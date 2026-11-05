from enum import Enum, auto
from typing import List, Optional
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
    sorted DataChunks according to specified column ordering rules.
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

    def _collect_and_sort(self) -> None:
        all_rows = []
        while True:
            chunk = self._child.execute_chunk()
            if chunk is None:
                break
            for row in chunk.to_rows():
                all_rows.append(row)

        if len(all_rows) == 0:
            self._has_sorted = True
            return

        # Prepare sort keys based on column indices
        col_indices = []
        for expr in self._order_by_expressions:
            idx = self._schema.get_column_index(expr.column_name)
            is_reverse = (expr.direction == OrderDirection.DESCENDING)
            col_indices.append((idx, is_reverse))

        # Sort rows with support for None values (Nulls Last)
        def sort_key_helper(row):
            key_elements = []
            for idx, is_reverse in col_indices:
                val = row[idx]
                is_null = (val is None)
                key_elements.append((is_null, val))
            return key_elements

        # Multi-key sorting
        for idx, is_reverse in reversed(col_indices):
            all_rows.sort(
                key=lambda r: (r[idx] is None, r[idx] if r[idx] is not None else 0),
                reverse=is_reverse
            )

        # Repackage into chunks
        capacity = 2048
        current_chunk = DataChunk(self._schema, capacity=capacity)
        for row in all_rows:
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