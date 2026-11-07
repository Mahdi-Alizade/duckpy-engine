from enum import Enum, auto
from typing import Any, Callable, List, Optional
from duckpy.execution.operator import PhysicalOperator
from duckpy.execution.filter import ComparisonOp
from duckpy.storage.chunk import DataChunk
from duckpy.storage.schema import Schema


class BooleanLogicOp(Enum):
    AND = auto()
    OR = auto()


class FilterCondition:
    def __init__(self, column_name: str, op: ComparisonOp, target_value: Any):
        self.column_name = column_name
        self.op = op
        self.target_value = target_value


class VectorizedLogicalFilter(PhysicalOperator):
    """
    Physical operator that evaluates compound boolean predicates (AND / OR)
    over DataChunks in a vectorized manner.
    """
    def __init__(
        self,
        child: PhysicalOperator,
        left_condition: FilterCondition,
        logic_op: BooleanLogicOp,
        right_condition: FilterCondition
    ):
        self._child = child
        self._left_cond = left_condition
        self._logic_op = logic_op
        self._right_cond = right_condition
        self._left_comparator = self._get_comparator(left_condition.op)
        self._right_comparator = self._get_comparator(right_condition.op)

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

            left_vec = chunk.get_vector(self._left_cond.column_name)
            right_vec = chunk.get_vector(self._right_cond.column_name)

            matched_row_indices = []

            for row_idx in range(cardinality):
                # Evaluate left predicate
                left_match = False
                if not left_vec.is_null(row_idx):
                    left_val = left_vec.get(row_idx)
                    left_match = self._left_comparator(left_val, self._left_cond.target_value)

                # Evaluate right predicate
                right_match = False
                if not right_vec.is_null(row_idx):
                    right_val = right_vec.get(row_idx)
                    right_match = self._right_comparator(right_val, self._right_cond.target_value)

                # Combine with logical operator
                if self._logic_op == BooleanLogicOp.AND:
                    row_passed = left_match and right_match
                elif self._logic_op == BooleanLogicOp.OR:
                    row_passed = left_match or right_match
                else:
                    raise ValueError(f"Unsupported boolean operator: {self._logic_op}")

                if row_passed:
                    matched_row_indices.append(row_idx)

            if len(matched_row_indices) == 0:
                continue

            # Build result chunk
            filtered_chunk = DataChunk(self.schema, capacity=len(matched_row_indices))
            col_count = chunk.column_count
            for r_idx in matched_row_indices:
                row_data = [chunk.get_vector(c).get(r_idx) for c in range(col_count)]
                filtered_chunk.append_row(row_data)

            return filtered_chunk