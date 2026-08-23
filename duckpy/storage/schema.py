"""
Schema representation for defining table and vector layout structures.
"""
from typing import List, Dict, Optional
from duckpy.types.dtypes import DuckType


class ColumnDefinition:
    def __init__(self, name: str, dtype: DuckType):
        if not name or not isinstance(name, str):
            raise ValueError("Column name must be a non-empty string.")
        if not isinstance(dtype, DuckType):
            raise TypeError(f"dtype must be an instance of DuckType, got {type(dtype)}")
        
        self._name = name.strip()
        self._dtype = dtype

    @property
    def name(self) -> str:
        return self._name

    @property
    def dtype(self) -> DuckType:
        return self._dtype

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ColumnDefinition):
            return False
        return self._name == other._name and self._dtype == other._dtype

    def __repr__(self) -> str:
        return f"ColumnDefinition(name='{self._name}', dtype={self._dtype.name})"


class Schema:
    def __init__(self, columns: List[ColumnDefinition]):
        if not columns:
            raise ValueError("Schema must contain at least one column definition.")
        
        self._columns = list(columns)
        self._name_to_index: Dict[str, int] = {}
        
        for idx, col in enumerate(self._columns):
            if col.name in self._name_to_index:
                raise ValueError(f"Duplicate column name '{col.name}' found in schema.")
            self._name_to_index[col.name] = idx

    @property
    def columns(self) -> List[ColumnDefinition]:
        return list(self._columns)

    @property
    def column_count(self) -> int:
        return len(self._columns)

    def get_column_index(self, name: str) -> int:
        if name not in self._name_to_index:
            raise KeyError(f"Column '{name}' not found in schema.")
        return self._name_to_index[name]

    def get_column(self, name_or_idx: int | str) -> ColumnDefinition:
        if isinstance(name_or_idx, str):
            idx = self.get_column_index(name_or_idx)
            return self._columns[idx]
        elif isinstance(name_or_idx, int):
            if name_or_idx < 0 or name_or_idx >= len(self._columns):
                raise IndexError(f"Column index {name_or_idx} out of range.")
            return self._columns[name_or_idx]
        raise TypeError("Index must be an integer or a string.")

    def __len__(self) -> int:
        return len(self._columns)

    def __repr__(self) -> str:
        cols_repr = ", ".join(repr(c) for c in self._columns)
        return f"Schema([{cols_repr}])"