"""
DataChunk implementation containing a horizontal batch of columnar Vectors.
"""
from typing import List, Any, Optional
from duckpy.storage.schema import Schema
from duckpy.storage.vector import Vector


class DataChunk:
    def __init__(self, schema: Schema, capacity: int = Vector.DEFAULT_VECTOR_SIZE):
        self._schema = schema
        self._capacity = capacity
        self._vectors: List[Vector] = [
            Vector(dtype=col.dtype, capacity=capacity)
            for col in schema.columns
        ]

    @property
    def schema(self) -> Schema:
        return self._schema

    @property
    def column_count(self) -> int:
        return len(self._vectors)

    @property
    def card(self) -> int:
        if not self._vectors:
            return 0
        return self._vectors[0].length

    @property
    def capacity(self) -> int:
        return self._capacity

    def get_vector(self, index_or_name: int | str) -> Vector:
        if isinstance(index_or_name, str):
            idx = self._schema.get_column_index(index_or_name)
            return self._vectors[idx]
        elif isinstance(index_or_name, int):
            if index_or_name < 0 or index_or_name >= len(self._vectors):
                raise IndexError(f"Vector index {index_or_name} out of bounds.")
            return self._vectors[index_or_name]
        raise TypeError("Identifier must be an integer index or string column name.")

    def append_row(self, row_values: List[Optional[Any]]) -> None:
        if len(row_values) != self.column_count:
            raise ValueError(
                f"Row length mismatch: expected {self.column_count} values, got {len(row_values)}"
            )
        
        current_len = self.card
        if current_len >= self._capacity:
            raise OverflowError(f"DataChunk capacity of {self._capacity} reached.")

        for i, val in enumerate(row_values):
            self._vectors[i].append(val)

    def to_rows(self) -> List[List[Optional[Any]]]:
        num_rows = self.card
        rows: List[List[Optional[Any]]] = []
        for r in range(num_rows):
            row = [self._vectors[c].get(r) for c in range(self.column_count)]
            rows.append(row)
        return rows

    def __repr__(self) -> str:
        return f"DataChunk(cardinality={self.card}/{self._capacity}, columns={self.column_count})"