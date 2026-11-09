from duckpy.types.dtypes import DuckType
from duckpy.context import DuckPyContext


def test_dataframe_intersect_and_except():
    ctx = DuckPyContext()

    group_a = [
        [1, "Alice"],
        [2, "Bob"],
        [3, "Charlie"],
    ]
    group_b = [
        [2, "Bob"],
        [3, "Charlie"],
        [4, "David"],
    ]
    cols = [
        ("id", DuckType.INT64),
        ("name", DuckType.STRING),
    ]

    ctx.create_table_from_rows("group_a", cols, group_a, chunk_size=2)
    ctx.create_table_from_rows("group_b", cols, group_b, chunk_size=2)

    df_a = ctx.table("group_a")
    df_b = ctx.table("group_b")

    # 1. INTERSECT (Bob and Charlie)
    intersect_res = df_a.intersect(df_b).to_dict()
    assert len(intersect_res) == 2
    intersect_names = {r["name"] for r in intersect_res}
    assert intersect_names == {"Bob", "Charlie"}

    # 2. EXCEPT (Alice only)
    except_res = df_a.except_(df_b).to_dict()
    assert len(except_res) == 1
    assert except_res[0]["name"] == "Alice"


def test_sql_intersect_and_except():
    ctx = DuckPyContext()

    t1_data = [
        [10, "Service_X"],
        [20, "Service_Y"],
    ]
    t2_data = [
        [20, "Service_Y"],
        [30, "Service_Z"],
    ]
    cols = [
        ("code", DuckType.INT64),
        ("title", DuckType.STRING),
    ]
    ctx.create_table_from_rows("srv_1", cols, t1_data, chunk_size=2)
    ctx.create_table_from_rows("srv_2", cols, t2_data, chunk_size=2)

    # SQL INTERSECT
    sql_intersect = "SELECT code, title FROM srv_1 INTERSECT SELECT code, title FROM srv_2;"
    res_inter = ctx.sql(sql_intersect).to_dict()
    assert len(res_inter) == 1
    assert res_inter[0] == {"code": 20, "title": "Service_Y"}

    # SQL EXCEPT
    sql_except = "SELECT code, title FROM srv_1 EXCEPT SELECT code, title FROM srv_2;"
    res_exc = ctx.sql(sql_except).to_dict()
    assert len(res_exc) == 1
    assert res_exc[0] == {"code": 10, "title": "Service_X"}