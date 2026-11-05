from enum import Enum, auto
from typing import Any, List, Optional, Union
from duckpy.types.dtypes import DuckType
from duckpy.storage.vector import Vector
from duckpy.storage.chunk import DataChunk


class ArithmeticOp(Enum):
    ADD = auto()
    SUBTRACT = auto()
    MULTIPLY = auto()
    DIVIDE = auto()


class Expression:
    """
    Base class for vectorized expression trees.
    """
    def evaluate(self, chunk: DataChunk) -> Vector:
        raise NotImplementedError("Subclasses must implement evaluate.")


class ColumnRefExpr(Expression):
    """
    Evaluates to an existing column vector in the DataChunk.
    """
    def __init__(self, column_name: str):
        self.column_name = column_name

    def evaluate(self, chunk: DataChunk) -> Vector:
        target_vec = chunk.get_vector(self.column_name)
        return target_vec


class LiteralExpr(Expression):
    """
    Represents a constant scalar literal.
    """
    def __init__(self, value: Any, dtype: DuckType):
        self.value = value
        self.dtype = dtype

    def evaluate(self, chunk: DataChunk) -> Vector:
        cardinality = chunk.card
        vec = Vector(dtype=self.dtype, capacity=max(cardinality, 1))
        for _ in range(cardinality):
            vec.append(self.value)
        return vec


class BinaryArithmeticExpr(Expression):
    """
    Vectorized binary arithmetic operator evaluating Left [Op] Right.
    Supports Null-propagation.
    """
    def __init__(
        self,
        left: Expression,
        op: ArithmeticOp,
        right: Expression,
        alias: Optional[str] = None
    ):
        self.left = left
        self.op = op
        self.right = right
        self.alias = alias or f"expr_{op.name.lower()}"

    def evaluate(self, chunk: DataChunk) -> Vector:
        left_vec = self.left.evaluate(chunk)
        right_vec = self.right.evaluate(chunk)

        cardinality = chunk.card
        # Result type default to FLOAT64 for arithmetic safety
        result_dtype = DuckType.FLOAT64
        result_vec = Vector(dtype=result_dtype, capacity=max(cardinality, 1))

        for idx in range(cardinality):
            if left_vec.is_null(idx) or right_vec.is_null(idx):
                result_vec.append(None)
                continue

            left_val = float(left_vec.get(idx))
            right_val = float(right_vec.get(idx))

            if self.op == ArithmeticOp.ADD:
                computed_val = left_val + right_val
            elif self.op == ArithmeticOp.SUBTRACT:
                computed_val = left_val - right_val
            elif self.op == ArithmeticOp.MULTIPLY:
                computed_val = left_val * right_val
            elif self.op == ArithmeticOp.DIVIDE:
                if right_val == 0.0:
                    computed_val = None
                else:
                    computed_val = left_val / right_val
            else:
                raise ValueError(f"Unsupported arithmetic op: {self.op}")

            result_vec.append(computed_val)

        return result_vec