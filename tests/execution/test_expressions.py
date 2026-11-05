from duckpy.types.dtypes import DuckType
from duckpy.storage.schema import Schema, ColumnDefinition
from duckpy.storage.chunk import DataChunk
from duckpy.execution.expressions import (
    ColumnRefExpr,
    LiteralExpr,
    BinaryArithmeticExpr,
    ArithmeticOp,
)


def test_vectorized_arithmetic_column_and_literal():
    schema = Schema([
        ColumnDefinition("base_salary", DuckType.FLOAT64),
        ColumnDefinition("bonus", DuckType.FLOAT64),
    ])

    chunk = DataChunk(schema, capacity=4)
    chunk.append_row([1000.0, 200.0])
    chunk.append_row([2000.0, None])
    chunk.append_row([3000.0, 500.0])

    # Expr: base_salary + bonus
    add_expr = BinaryArithmeticExpr(
        left=ColumnRefExpr("base_salary"),
        op=ArithmeticOp.ADD,
        right=ColumnRefExpr("bonus"),
        alias="total_comp"
    )

    res_vec = add_expr.evaluate(chunk)
    assert len(res_vec) == 3
    assert res_vec.get(0) == 1200.0
    assert res_vec.get(1) is None
    assert res_vec.is_null(1) is True
    assert res_vec.get(2) == 3500.0


def test_vectorized_multiplication_with_literal():
    schema = Schema([
        ColumnDefinition("price", DuckType.FLOAT64),
    ])

    chunk = DataChunk(schema, capacity=3)
    chunk.append_row([50.0])
    chunk.append_row([100.0])

    # Expr: price * 1.20 (20% tax)
    tax_expr = BinaryArithmeticExpr(
        left=ColumnRefExpr("price"),
        op=ArithmeticOp.MULTIPLY,
        right=LiteralExpr(1.2, DuckType.FLOAT64),
        alias="taxed_price"
    )

    res_vec = tax_expr.evaluate(chunk)
    assert len(res_vec) == 2
    assert round(res_vec.get(0), 2) == 60.0
    assert round(res_vec.get(1), 2) == 120.0


def test_vectorized_division_by_zero():
    schema = Schema([
        ColumnDefinition("val", DuckType.FLOAT64),
    ])

    chunk = DataChunk(schema, capacity=2)
    chunk.append_row([100.0])

    div_expr = BinaryArithmeticExpr(
        left=ColumnRefExpr("val"),
        op=ArithmeticOp.DIVIDE,
        right=LiteralExpr(0.0, DuckType.FLOAT64),
        alias="div_zero"
    )

    res_vec = div_expr.evaluate(chunk)
    assert res_vec.get(0) is None
    assert res_vec.is_null(0) is True