from typing import List, Any, Optional, Union
from duckpy.storage.schema import Schema
from duckpy.storage.vector import Vector
from duckpy.storage.dict_vector import DictionaryVector
from duckpy.storage.rle_vector import RLEVector

AnyVector = Union[Vector, DictionaryVector, RLEVector]


class DataChunk:
    """
    DataChunk representing a horizontal batch of columnar Vectors.
    Supports standard contiguous Vectors, DictionaryVector, and RLEVector.
    """
    def __init__(self, schema: Schema, capacity: int = Vector.DEFAULT_VECTOR_SIZE):
        self._schema = schema
        self._capacity = capacity
        
        initialized_vectors: List[AnyVector] = []
        for column_def in schema.columns:
            new_vec = Vector(dtype=column_def.dtype, capacity=capacity)
            initialized_vectors.append(new_vec)
            
        self._vectors = initialized_vectors

    @property
    def schema(self) -> Schema:
        return self._schema

    @property
    def column_count(self) -> int:
        return len(self._vectors)

    @property
    def card(self) -> int:
        if len(self._vectors) == 0:
            return 0
        first_vector = self._vectors[0]
        return len(first_vector)

    @property
    def capacity(self) -> int:
        return self._capacity

    def get_vector(self, index_or_name: Union[int, str]) -> AnyVector:
        if isinstance(index_or_name, str):
            col_idx = self._schema.get_column_index(index_or_name)
            return self._vectors[col_idx]
        elif isinstance(index_or_name, int):
            total_cols = len(self._vectors)
            if index_or_name < 0 or index_or_name >= total_cols:
                err_msg = "Vector index out of bounds"
                raise IndexError(err_msg)
            return self._vectors[index_or_name]

        type_err = "Identifier must be an integer index or string column name."
        raise TypeError(type_err)

    def set_vector(self, index_or_name: Union[int, str], vector: AnyVector) -> None:
        """
        Replaces an internal column vector with a compressed or custom vector.
        """
        if isinstance(index_or_name, str):
            target_index = self._schema.get_column_index(index_or_name)
        elif isinstance(index_or_name, int):
            if index_or_name < 0 or index_or_name >= len(self._vectors):
                raise IndexError("Target vector index out of bounds")
            target_index = index_or_name
        else:
            raise TypeError("Identifier must be integer index or string name.")

        col_def = self._schema.get_column(target_index)
        if col_def.dtype != vector.dtype:
            raise TypeError("Vector data type does not match schema column definition.")

        self._vectors[target_index] = vector

    def append_row(self, row_values: List[Optional[Any]]) -> None:
        expected_len = self.column_count
        actual_len = len(row_values)

        if actual_len != expected_len:
            msg = "Row length mismatch: expected " + str(expected_len) + ", got " + str(actual_len)
            raise ValueError(msg)

        current_cardinality = self.card
        if current_cardinality >= self._capacity:
            overflow_msg = "DataChunk capacity reached."
            raise OverflowError(overflow_msg)

        for col_idx in range(expected_len):
            val = row_values[col_idx]
            target_vec = self._vectors[col_idx]
            target_vec.append(val)

    def to_rows(self) -> List[List[Optional[Any]]]:
        row_count = self.card
        cols_count = self.column_count
        rows_matrix: List[List[Optional[Any]]] = []

        for r in range(row_count):
            single_row: List[Optional[Any]] = []
            for c in range(cols_count):
                curr_vec = self._vectors[c]
                val = curr_vec.get(r)
                single_row.append(val)
            rows_matrix.append(single_row)

        return rows_matrix

    def __repr__(self) -> str:
        return (
            "DataChunk(cardinality="
            + str(self.card)
            + "/"
            + str(self._capacity)
            + ", columns="
            + str(self.column_count)
            + ")"
        )