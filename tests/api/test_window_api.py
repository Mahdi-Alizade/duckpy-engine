from duckpy.types.dtypes import DuckType
from duckpy.context import DuckPyContext
from duckpy.execution.window import WindowFunctionType


def test_dataframe_window_row_number_pipeline():
    ctx = DuckPyContext()

    data = [
        [1, "Product", 80000.0],
        [2, "Engineering", 120000.0],
        [3, "Product", 95000.0],
        [4, "Engineering", 150000.0],
    ]

    columns = [
        ("id", DuckType.INT64),
        ("dept", DuckType.STRING),
        ("salary", DuckType.FLOAT64),
    ]

    ctx.create_table_from_rows("team_salaries", columns, data, chunk_size=2)

    df = (
        ctx.table("team_salaries")
        .window(
            func_type=WindowFunctionType.ROW_NUMBER,
            partition_by=["dept"],
            order_by=["salary"],
            alias="salary_order"
        )
    )

    records = df.to_dict()
    assert len(records) == 4

    # Group results by dept
    eng_rows = [r for r in records if r["dept"] == "Engineering"]
    prod_rows = [r for r in records if r["dept"] == "Product"]

    # Engineering: 120000 -> 1, 150000 -> 2
    assert eng_rows[0]["salary"] == 120000.0
    assert eng_rows[0]["salary_order"] == 1
    assert eng_rows[1]["salary"] == 150000.0
    assert eng_rows[1]["salary_order"] == 2

    # Product: 80000 -> 1, 95000 -> 2
    assert prod_rows[0]["salary"] == 80000.0
    assert prod_rows[0]["salary_order"] == 1
    assert prod_rows[1]["salary"] == 95000.0
    assert prod_rows[1]["salary_order"] == 2