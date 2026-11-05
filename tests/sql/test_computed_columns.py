from duckpy.types.dtypes import DuckType
from duckpy.context import DuckPyContext
from duckpy.execution.expressions import (
    ColumnRefExpr,
    LiteralExpr,
    BinaryArithmeticExpr,
    ArithmeticOp,
)


def test_dataframe_with_column_and_filter():
    ctx = DuckPyContext()

    data = [
        [1, "Product_A", 100.0, 20.0],
        [2, "Product_B", 250.0, 50.0],
        [3, "Product_C", 80.0, 10.0],
    ]

    columns = [
        ("id", DuckType.INT64),
        ("name", DuckType.STRING),
        ("base_price", DuckType.FLOAT64),
        ("tax", DuckType.FLOAT64),
    ]

    ctx.create_table_from_rows("inventory", columns, data, chunk_size=2)

    # total_price = base_price + tax
    total_price_expr = BinaryArithmeticExpr(
        left=ColumnRefExpr("base_price"),
        op=ArithmeticOp.ADD,
        right=ColumnRefExpr("tax"),
        alias="total_price"
    )

    df = (
        ctx.table("inventory")
        .with_column("total_price", total_price_expr)
        .select("name", "total_price")
    )

    records = df.to_dict()
    assert len(records) == 3
    assert records[0] == {"name": "Product_A", "total_price": 120.0}
    assert records[1] == {"name": "Product_B", "total_price": 300.0}
    assert records[2] == {"name": "Product_C", "total_price": 90.0}