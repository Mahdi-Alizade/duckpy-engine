from duckpy.types.dtypes import DuckType
from duckpy.context import DuckPyContext


def test_dataframe_union_all_and_union_distinct():
    ctx = DuckPyContext()

    team_a = [
        [1, "Alice"],
        [2, "Bob"],
    ]
    team_b = [
        [2, "Bob"],     # Duplicate
        [3, "Charlie"],
    ]
    cols = [
        ("id", DuckType.INT64),
        ("name", DuckType.STRING),
    ]

    ctx.create_table_from_rows("team_a", cols, team_a, chunk_size=2)
    ctx.create_table_from_rows("team_b", cols, team_b, chunk_size=2)

    df_a = ctx.table("team_a")
    df_b = ctx.table("team_b")

    # 1. UNION ALL (Preserves duplicates: 4 total rows)
    res_union_all = df_a.union_all(df_b).to_dict()
    assert len(res_union_all) == 4
    names_all = [r["name"] for r in res_union_all]
    assert names_all == ["Alice", "Bob", "Bob", "Charlie"]

    # 2. UNION (Deduplicates: 3 unique rows)
    res_union_distinct = df_a.union(df_b).to_dict()
    assert len(res_union_distinct) == 3
    names_distinct = [r["name"] for r in res_union_distinct]
    assert names_distinct == ["Alice", "Bob", "Charlie"]