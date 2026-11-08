from typing import Any, Callable, Optional
from duckpy.execution.operator import PhysicalOperator
from duckpy.execution.filter import ComparisonOp
from duckpy.storage.chunk import DataChunk
from duckpy.storage.schema import Schema


class PhysicalHaving(PhysicalOperator):
    """
    Physical operator that applies filtering predicates on post-aggregation DataChunks (HAVING clause).
    """
    def __init__(
        self,
        child: PhysicalOperator,
        target_column: str,
        op: ComparisonOp,
        threshold_value: Any
    ):
        self._child = child
        self._target_column = target_column
        self._op = op
        self._threshold_value = threshold_value
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
        raise ValueError(f"Unsupported comparison operator: {op}")

    def execute_chunk(self) -> Optional[DataChunk]:
        while True:
            chunk = self._child.execute_chunk()
            if chunk is None:
                return None

            cardinality = chunk.card
            if cardinality == 0:
                continue

            target_vec = chunk.get_vector(self._target_column)
            accepted_indices = []

            for row_idx in range(cardinality):
                if target_vec.is_null(row_idx):
                    continue
                val = target_vec.get(row_idx)
                if self._comparator(val, self._threshold_value):
                    accepted_indices.append(row_idx)

            if len(accepted_indices) == 0:
                continue

            filtered_chunk = DataChunk(self.schema, capacity=len(accepted_indices))
            col_count = chunk.column_count
            for r_idx in accepted_indices:
                row_vals = [chunk.get_vector(c).get(r_idx) for c in range(col_count)]
                filtered_chunk.append_row(row_vals)

            return filtered_chunk