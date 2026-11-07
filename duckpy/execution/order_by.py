from enum import Enum, auto
from functools import cmp_to_key
from typing import Any, List, Optional
from duckpy.execution.operator import PhysicalOperator
from duckpy.storage.chunk import DataChunk
from duckpy.storage.schema import Schema


class OrderDirection(Enum):
    ASCENDING = auto()
    DESCENDING = auto()


class OrderByExpr:
    def __init__(self, column_name: str, direction: OrderDirection = OrderDirection.ASCENDING):
        self.column_name = column_name
        self.direction = direction


class PhysicalOrderBy(PhysicalOperator):
    """
    Physical operator that buffers all incoming DataChunks and outputs
    sorted DataChunks according to specified column ordering rules with NULLS LAST.
    """
    def __init__(self, child: PhysicalOperator, order_by_expressions: List[OrderByExpr]):
        self._child = child
        self._order_by_expressions = list(order_by_expressions)
        self._schema = child.schema
        self._sorted_chunks: List[DataChunk] = []
        self._current_chunk_idx = 0
        self._has_sorted = False

    @property
    def schema(self) -> Schema:
        return self._schema

    def init(self) -> None:
        self._child.init()
        self._sorted_chunks.clear()
        self._current_chunk_idx = 0
        self._has_sorted = False

    def _compare_rows(self, row_a: List[Any], row_b: List[Any], order_specs: List[tuple[int, bool]]) -> int:
        for col_idx, is_descending in order_specs:
            val_a = row_a[col_idx]
            val_b = row_b[col_idx]

            # Nulls Last handling
            if val_a is None and val_b is None:
                continue
            if val_a is None:
                return 1
            if val_b is None:
                return -1

            if val_a == val_b:
                continue

            if val_a < val_b:
                return 1 if is_descending else -1
            else:
                return -1 if is_descending else 1

        return 0

    def _collect_and_sort(self) -> None:
        buffered_rows = []
        while True:
            chunk = self._child.execute_chunk()
            if chunk is None:
                break
            for row in chunk.to_rows():
                buffered_rows.append(row)

        if len(buffered_rows) == 0:
            self._has_sorted = True
            return

        order_specs: List[tuple[int, bool]] = []
        for expr in self._order_by_expressions:
            col_index = self._schema.get_column_index(expr.column_name)
            is_desc = (expr.direction == OrderDirection.DESCENDING)
            order_specs.append((col_index, is_desc))

        def comparator(a, b):
            return self._compare_rows(a, b, order_specs)

        buffered_rows.sort(key=cmp_to_key(comparator))

        capacity = 2048
        current_chunk = DataChunk(self._schema, capacity=capacity)
        for row in buffered_rows:
            if current_chunk.card >= capacity:
                self._sorted_chunks.append(current_chunk)
                current_chunk = DataChunk(self._schema, capacity=capacity)
            current_chunk.append_row(row)

        if current_chunk.card > 0:
            self._sorted_chunks.append(current_chunk)

        self._has_sorted = True

    def execute_chunk(self) -> Optional[DataChunk]:
        if not self._has_sorted:
            self._collect_and_sort()

        if self._current_chunk_idx >= len(self._sorted_chunks):
            return None

        result_chunk = self._sorted_chunks[self._current_chunk_idx]
        self._current_chunk_idx = self._current_chunk_idx + 1
        return result_chunk