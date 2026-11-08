from enum import Enum, auto
from functools import cmp_to_key
from typing import Any, List, Optional
from duckpy.execution.operator import PhysicalOperator
from duckpy.storage.chunk import DataChunk
from duckpy.storage.schema import Schema, ColumnDefinition
from duckpy.types.dtypes import DuckType


class WindowFunctionType(Enum):
    ROW_NUMBER = auto()
    RANK = auto()


class WindowSpec:
    """
    Defines partition columns, order columns, and the target window function.
    """
    def __init__(
        self,
        func_type: WindowFunctionType,
        partition_by: List[str],
        order_by: List[str],
        alias: str
    ):
        self.func_type = func_type
        self.partition_by = list(partition_by)
        self.order_by = list(order_by)
        self.alias = alias


class PhysicalWindow(PhysicalOperator):
    """
    Physical operator that buffers all incoming DataChunks, partitions and sorts rows,
    and appends computed window function columns (e.g. ROW_NUMBER, RANK).
    """
    def __init__(self, child: PhysicalOperator, window_spec: WindowSpec):
        self._child = child
        self._spec = window_spec

        existing_cols = list(child.schema.columns)
        window_col = ColumnDefinition(window_spec.alias, DuckType.INT64)
        existing_cols.append(window_col)
        self._schema = Schema(existing_cols)

        self._result_chunks: List[DataChunk] = []
        self._current_chunk_idx = 0
        self._has_executed = False

    @property
    def schema(self) -> Schema:
        return self._schema

    def init(self) -> None:
        self._child.init()
        self._result_chunks.clear()
        self._current_chunk_idx = 0
        self._has_executed = False

    def _execute_window(self) -> None:
        all_rows: List[List[Any]] = []
        while True:
            chunk = self._child.execute_chunk()
            if chunk is None:
                break
            for row in chunk.to_rows():
                all_rows.append(row)

        if len(all_rows) == 0:
            self._has_executed = True
            return

        child_schema = self._child.schema
        partition_indices = [child_schema.get_column_index(col) for col in self._spec.partition_by]
        order_indices = [child_schema.get_column_index(col) for col in self._spec.order_by]

        # 1. Group rows by partition key
        partitions = {}
        for row in all_rows:
            pkey_elements = []
            for idx in partition_indices:
                pkey_elements.append(row[idx])
            pkey = tuple(pkey_elements)

            if pkey not in partitions:
                partitions[pkey] = []
            partitions[pkey].append(row)

        # 2. Sort each partition and compute window values
        final_computed_rows = []

        def sort_comparator(row_a, row_b):
            for col_idx in order_indices:
                val_a = row_a[col_idx]
                val_b = row_b[col_idx]

                if val_a is None and val_b is None:
                    continue
                if val_a is None:
                    return 1
                if val_b is None:
                    return -1

                if val_a < val_b:
                    return -1
                elif val_a > val_b:
                    return 1
            return 0

        for pkey in partitions:
            partition_rows = partitions[pkey]
            if len(order_indices) > 0:
                partition_rows.sort(key=cmp_to_key(sort_comparator))

            prev_order_vals = None
            current_rank = 1

            for row_idx, row in enumerate(partition_rows):
                if self._spec.func_type == WindowFunctionType.ROW_NUMBER:
                    calculated_metric = row_idx + 1
                elif self._spec.func_type == WindowFunctionType.RANK:
                    current_order_vals = [row[idx] for idx in order_indices]
                    if prev_order_vals is None:
                        current_rank = 1
                    elif current_order_vals != prev_order_vals:
                        current_rank = row_idx + 1
                    prev_order_vals = current_order_vals
                    calculated_metric = current_rank
                else:
                    calculated_metric = row_idx + 1

                extended_row = list(row)
                extended_row.append(calculated_metric)
                final_computed_rows.append(extended_row)

        # 3. Pack into chunks
        capacity = 2048
        current_chunk = DataChunk(self._schema, capacity=capacity)
        for row in final_computed_rows:
            if current_chunk.card >= capacity:
                self._result_chunks.append(current_chunk)
                current_chunk = DataChunk(self._schema, capacity=capacity)
            current_chunk.append_row(row)

        if current_chunk.card > 0:
            self._result_chunks.append(current_chunk)

        self._has_executed = True

    def execute_chunk(self) -> Optional[DataChunk]:
        if not self._has_executed:
            self._execute_window()

        if self._current_chunk_idx >= len(self._result_chunks):
            return None

        chunk = self._result_chunks[self._current_chunk_idx]
        self._current_chunk_idx = self._current_chunk_idx + 1
        return chunk