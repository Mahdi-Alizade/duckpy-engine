"""
Columnar Vector representation storing contiguous arrays of typed values.
"""
from typing import Any, List, Optional
from duckpy.types.dtypes import DuckType, TypeSystem
from duckpy.storage.bitmap import BitMap


class Vector:
    DEFAULT_VECTOR_SIZE = 2048

    def __init__(self, dtype: DuckType, capacity: int = DEFAULT_VECTOR_SIZE):
        self._dtype = dtype
        self._capacity = capacity
        self._length = 0
        self._data: List[Any] = []
        self._null_bitmap = BitMap(capacity, initial_value=False)

    @property
    def dtype(self) -> DuckType:
        return self._dtype

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def length(self) -> int:
        return self._length

    def append(self, value: Optional[Any]) -> None:
        if self._length >= self._capacity:
            raise OverflowError(f"Vector capacity of {self._capacity} reached.")

        if value is None:
            self._null_bitmap.set(self._length, True)
            self._data.append(TypeSystem.get_default_value(self._dtype))
        else:
            if not TypeSystem.validate(self._dtype, value):
                raise TypeError(f"Invalid type for value '{value}' with expected dtype {self._dtype}")
            self._null_bitmap.set(self._length, False)
            self._data.append(value)

        self._length += 1

    def get(self, index: int) -> Optional[Any]:
        if index < 0 or index >= self._length:
            raise IndexError(f"Index {index} out of bounds for vector length {self._length}")
        
        if self._null_bitmap.get(index):
            return None
        return self._data[index]

    def is_null(self, index: int) -> bool:
        if index < 0 or index >= self._length:
            raise IndexError(f"Index {index} out of bounds for vector length {self._length}")
        return self._null_bitmap.get(index)

    def to_list(self) -> List[Optional[Any]]:
        return [self.get(i) for i in range(self._length)]

    @classmethod
    def from_list(cls, values: List[Optional[Any]], dtype: DuckType, capacity: Optional[int] = None) -> "Vector":
        target_capacity = capacity if capacity is not None else max(len(values), cls.DEFAULT_VECTOR_SIZE)
        vec = cls(dtype=dtype, capacity=target_capacity)
        for val in values:
            vec.append(val)
        return vec

    def __len__(self) -> int:
        return self._length

    def __repr__(self) -> str:
        return f"Vector(dtype={self._dtype.name}, length={self._length}/{self._capacity}, data={self.to_list()[:10]}...)"