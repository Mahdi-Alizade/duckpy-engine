"""
SelectionVector implementation for Zero-Copy filtering and indexing in vectorized operations.
"""
from typing import List, Iterator


class SelectionVector:
    def __init__(self, indices: List[int]):
        self._indices = list(indices)

    @property
    def count(self) -> int:
        return len(self._indices)

    def get(self, index: int) -> int:
        if index < 0 or index >= len(self._indices):
            raise IndexError(f"Selection index {index} out of range ({len(self._indices)})")
        return self._indices[index]

    def to_list(self) -> List[int]:
        return list(self._indices)

    def __len__(self) -> int:
        return len(self._indices)

    def __iter__(self) -> Iterator[int]:
        return iter(self._indices)

    def __repr__(self) -> str:
        return f"SelectionVector(count={len(self._indices)}, indices={self._indices[:10]}...)"