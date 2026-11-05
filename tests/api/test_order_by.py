from duckpy.types.dtypes import DuckType
from duckpy.context import DuckPyContext


def test_order_by_ascending_and_descending():
    ctx = DuckPyContext()

    data = [
        [1, "Zara", 75000.0],
        [2, "Ali", 120000.0],
        [3, "Behnam", 95000.0],
        [4, "Sara", None],
    ]

    columns = [
        ("id", DuckType.INT64),
        ("name", DuckType.STRING),
        ("salary", DuckType.FLOAT64),
    ]

    ctx.create_table_from_rows("team", columns, data, chunk_size=2)

    # 1. Order by salary descending
    df_desc = ctx.table("team").order_by("salary", ascending=False)
    res_desc = df_desc.to_dict()

    assert len(res_desc) == 4
    assert res_desc[0]["salary"] == 120000.0
    assert res_desc[1]["salary"] == 95000.0
    assert res_desc[2]["salary"] == 75000.0
    assert res_desc[3]["salary"] is None

    # 2. Order by name ascending
    df_asc = ctx.table("team").order_by("name", ascending=True)
    res_asc = df_asc.to_dict()

    names_sorted = [r["name"] for r in res_asc]
    assert names_sorted == ["Ali", "Behnam", "Sara", "Zara"]