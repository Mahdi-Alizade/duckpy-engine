import pytest
from duckpy.types.dtypes import DuckType
from duckpy.context import DuckPyContext


def test_sql_filter_and_projection():
    ctx = DuckPyContext()
    data = [
        [1, "Alice", 120.0],
        [2, "Bob", 80.0],
        [3, "Charlie", 150.0],
    ]
    cols = [
        ("id", DuckType.INT64),
        ("name", DuckType.STRING),
        ("score", DuckType.FLOAT64),
    ]
    ctx.create_table_from_rows("students", cols, data, chunk_size=2)

    df = ctx.sql("SELECT name, score FROM students WHERE score > 100.0;")
    rows = df.to_dict()

    assert len(rows) == 2
    assert rows[0] == {"name": "Alice", "score": 120.0}
    assert rows[1] == {"name": "Charlie", "score": 150.0}


def test_sql_group_by_aggregation():
    ctx = DuckPyContext()
    data = [
        ["Tech", 5000.0],
        ["Tech", 7000.0],
        ["Sales", 4000.0],
    ]
    cols = [
        ("dept", DuckType.STRING),
        ("salary", DuckType.FLOAT64),
    ]
    ctx.create_table_from_rows("payroll", cols, data, chunk_size=2)

    df = ctx.sql("SELECT dept, AVG(salary) AS avg_sal, COUNT(salary) AS emp_count FROM payroll GROUP BY dept;")
    rows = df.to_dict()

    res = {r["dept"]: (r["avg_sal"], r["emp_count"]) for r in rows}
    assert res["Tech"] == (6000.0, 2)
    assert res["Sales"] == (4000.0, 1)


def test_sql_order_by_and_limit():
    ctx = DuckPyContext()
    data = [
        [1, "Player_A", 50.0],
        [2, "Player_B", 90.0],
        [3, "Player_C", 75.0],
        [4, "Player_D", 100.0],
    ]
    cols = [
        ("id", DuckType.INT64),
        ("name", DuckType.STRING),
        ("score", DuckType.FLOAT64),
    ]
    ctx.create_table_from_rows("leaderboard", cols, data, chunk_size=2)

    query = "SELECT name, score FROM leaderboard ORDER BY score DESC LIMIT 2;"
    df = ctx.sql(query)
    top_players = df.to_dict()

    assert len(top_players) == 2
    assert top_players[0] == {"name": "Player_D", "score": 100.0}
    assert top_players[1] == {"name": "Player_B", "score": 90.0}


def test_sql_compound_where_and_or():
    ctx = DuckPyContext()
    data = [
        [1, "Alice", "Tech", 120000.0],
        [2, "Bob", "Tech", 80000.0],
        [3, "Charlie", "HR", 95000.0],
        [4, "Diana", "Marketing", 110000.0],
    ]
    cols = [
        ("id", DuckType.INT64),
        ("name", DuckType.STRING),
        ("dept", DuckType.STRING),
        ("salary", DuckType.FLOAT64),
    ]
    ctx.create_table_from_rows("company", cols, data, chunk_size=2)

    # 1. Test AND condition
    sql_and = "SELECT name, salary FROM company WHERE dept = 'Tech' AND salary > 100000.0;"
    res_and = ctx.sql(sql_and).to_dict()
    assert len(res_and) == 1
    assert res_and[0] == {"name": "Alice", "salary": 120000.0}

    # 2. Test OR condition
    sql_or = "SELECT name, dept FROM company WHERE dept = 'HR' OR salary > 115000.0;"
    res_or = ctx.sql(sql_or).to_dict()
    assert len(res_or) == 2
    names = [r["name"] for r in res_or]
    assert "Alice" in names
    assert "Charlie" in names