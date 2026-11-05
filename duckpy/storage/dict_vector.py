"""
Dictionary-encoded Vector for low-memory storage of high-cardinality string columns.
"""
from typing import Any, Dict, List, Optional
from duckpy.types.dtypes import DuckType
from duckpy.storage.bitmap import BitMap


class DictionaryVector:
    DEFAULT_CAPACITY = 2048

    def __init__(self, capacity: int = DEFAULT_CAPACITY):
        self._capacity = capacity
        self._length = 0
        self._dictionary: List[str] = []
        self._lookup: Dict[str, int] = {}
        self._indices: List[int] = []
        self._null_bitmap = BitMap(capacity, initial_value=False)

    @property
    def dtype(self) -> DuckType:
        return DuckType.STRING

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def length(self) -> int:
        return self._length

    @property
    def dictionary_size(self) -> int:
        return len(self._dictionary)

    def append(self, value: Optional[str]) -> None:
        if self._length >= self._capacity:
            raise OverflowError(f"DictionaryVector capacity of {self._capacity} reached.")

        if value is None:
            self._null_bitmap.set(self._length, True)
            self._indices.append(-1)
        else:
            if not isinstance(value, str):
                raise TypeError(f"Expected str, got {type(value)}")
            self._null_bitmap.set(self._length, False)
            if value not in self._lookup:
                new_idx = len(self._dictionary)
                self._dictionary.append(value)
                self._lookup[value] = new_idx
            self._indices.append(self._lookup[value])

        self._length += 1

    def get(self, index: int) -> Optional[str]:
        if index < 0 or index >= self._length:
            raise IndexError(f"Index {index} out of bounds for vector length {self._length}")

        if self._null_bitmap.get(index):
            return None
        dict_id = self._indices[index]
        return self._dictionary[dict_id]

    def is_null(self, index: int) -> bool:
        if index < 0 or index >= self._length:
            raise IndexError(f"Index {index} out of bounds for vector length {self._length}")
        return self._null_bitmap.get(index)

    def to_list(self) -> List[Optional[str]]:
        return [self.get(i) for i in range(self._length)]

    def __len__(self) -> int:
        return self._length

    def __repr__(self) -> str:
        return (
            f"DictionaryVector(length={self._length}/{self._capacity}, "
            f"unique_keys={len(self._dictionary)})"
        )