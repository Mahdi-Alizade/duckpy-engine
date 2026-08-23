"""
Data types and Type definitions for DuckPy Columnar Engine.
"""
from enum import Enum, auto
from typing import Any, Union


class DuckType(Enum):
    INT64 = auto()
    FLOAT64 = auto()
    STRING = auto()
    BOOLEAN = auto()


class TypeSystem:
    @staticmethod
    def get_default_value(dtype: DuckType) -> Any:
        if dtype == DuckType.INT64:
            return 0
        elif dtype == DuckType.FLOAT64:
            return 0.0
        elif dtype == DuckType.STRING:
            return ""
        elif dtype == DuckType.BOOLEAN:
            return False
        raise ValueError(f"Unsupported data type: {dtype}")

    @staticmethod
    def validate(dtype: DuckType, value: Any) -> bool:
        if value is None:
            return True
        if dtype == DuckType.INT64:
            return isinstance(value, int) and not isinstance(value, bool)
        elif dtype == DuckType.FLOAT64:
            return isinstance(value, (float, int)) and not isinstance(value, bool)
        elif dtype == DuckType.STRING:
            return isinstance(value, str)
        elif dtype == DuckType.BOOLEAN:
            return isinstance(value, bool)
        return False