"""
Physical Filter Operator applying vectorized predicates on DataChunks.
"""
from enum import Enum, auto
from typing import Any, Callable, Optional
from duckpy.execution.operator import PhysicalOperator
from duckpy.storage.chunk import DataChunk
from duckpy.storage.schema import Schema
from duckpy.storage.selection import SelectionVector


class ComparisonOp(Enum):
    EQUAL = auto()
    NOT_EQUAL = auto()
    GREATER_THAN = auto()
    GREATER_THAN_OR_EQUAL = auto()
    LESS_THAN = auto()
    LESS_THAN_OR_EQUAL = auto()


class VectorizedFilter(PhysicalOperator):
    def __init__(
        self,
        child: PhysicalOperator,
        column_name: str,
        op: ComparisonOp,
        target_value: Any
    ):
        self._child = child
        self._column_name = column_name
        self._op = op
        self._target_value = target_value
        self._comparator = self._get_comparator(op)

    @property
    def schema(self) -> Schema:
        return self._child.schema

    def init(self) -> None:
        self._child.init()

    @staticmethod
    def _get_comparator(op: ComparisonOp) -> Callable[[Any, Any], bool]:
        if op == ComparisonOp.EQUAL:
            return lambda a, b: a == b
        elif op == ComparisonOp.NOT_EQUAL:
            return lambda a, b: a != b
        elif op == ComparisonOp.GREATER_THAN:
            return lambda a, b: a > b
        elif op == ComparisonOp.GREATER_THAN_OR_EQUAL:
            return lambda a, b: a >= b
        elif op == ComparisonOp.LESS_THAN:
            return lambda a, b: a < b
        elif op == ComparisonOp.LESS_THAN_OR_EQUAL:
            return lambda a, b: a <= b
        raise ValueError(f"Unsupported comparison operator {op}")

    def execute_chunk(self) -> Optional[DataChunk]:
        while True:
            chunk = self._child.execute_chunk()
            if chunk is None:
                return None
            
            if chunk.card == 0:
                continue

            target_vec = chunk.get_vector(self._column_name)
            matched_indices = []

            # Vectorized evaluation loop
            for idx in range(chunk.card):
                if target_vec.is_null(idx):
                    continue
                val = target_vec.get(idx)
                if self._comparator(val, self._target_value):
                    matched_indices.append(idx)

            if not matched_indices:
                continue

            # Build filtered output chunk
            filtered_chunk = DataChunk(self.schema, capacity=len(matched_indices))
            for row_idx in matched_indices:
                row_vals = [chunk.get_vector(c).get(row_idx) for c in range(chunk.column_count)]
                filtered_chunk.append_row(row_vals)

            return filtered_chunk