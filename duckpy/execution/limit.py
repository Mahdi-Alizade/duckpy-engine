from typing import Optional
from duckpy.execution.operator import PhysicalOperator
from duckpy.storage.chunk import DataChunk
from duckpy.storage.schema import Schema


class PhysicalLimit(PhysicalOperator):
    """
    Physical operator that truncates incoming DataChunks
    once the target row limit count is reached.
    """
    def __init__(self, child: PhysicalOperator, limit_count: int):
        self._child = child
        self._limit_count = limit_count
        self._schema = child.schema
        self._emitted_rows = 0

    @property
    def schema(self) -> Schema:
        return self._schema

    def init(self) -> None:
        self._child.init()
        self._emitted_rows = 0

    def execute_chunk(self) -> Optional[DataChunk]:
        if self._emitted_rows >= self._limit_count:
            return None

        chunk = self._child.execute_chunk()
        if chunk is None:
            return None

        remaining_needed = self._limit_count - self._emitted_rows
        available_in_chunk = chunk.card

        if available_in_chunk <= remaining_needed:
            self._emitted_rows = self._emitted_rows + available_in_chunk
            return chunk

        # Need to slice chunk
        sliced_chunk = DataChunk(self._schema, capacity=remaining_needed)
        for r_idx in range(remaining_needed):
            row_vals = [chunk.get_vector(c).get(r_idx) for c in range(chunk.column_count)]
            sliced_chunk.append_row(row_vals)

        self._emitted_rows = self._emitted_rows + remaining_needed
        return sliced_chunk