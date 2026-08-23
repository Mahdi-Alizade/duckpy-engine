"""
Physical Table / In-Memory Scan Operator.
"""
from typing import List, Optional
from duckpy.execution.operator import PhysicalOperator
from duckpy.storage.chunk import DataChunk
from duckpy.storage.schema import Schema


class PhysicalScan(PhysicalOperator):
    def __init__(self, schema: Schema, chunks: List[DataChunk]):
        self._schema = schema
        self._chunks = list(chunks)
        self._current_index = 0

    @property
    def schema(self) -> Schema:
        return self._schema

    def init(self) -> None:
        self._current_index = 0

    def execute_chunk(self) -> Optional[DataChunk]:
        if self._current_index >= len(self._chunks):
            return None
        
        chunk = self._chunks[self._current_index]
        self._current_index += 1
        return chunk