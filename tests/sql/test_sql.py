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

    sql_and = "SELECT name, salary FROM company WHERE dept = 'Tech' AND salary > 100000.0;"
    res_and = ctx.sql(sql_and).to_dict()
    assert len(res_and) == 1
    assert res_and[0] == {"name": "Alice", "salary": 120000.0}

    sql_or = "SELECT name, dept FROM company WHERE dept = 'HR' OR salary > 115000.0;"
    res_or = ctx.sql(sql_or).to_dict()
    assert len(res_or) == 2
    names = [r["name"] for r in res_or]
    assert "Alice" in names
    assert "Charlie" in names


def test_sql_having_filter():
    ctx = DuckPyContext()
    data = [
        ["Tech", 100000.0],
        ["Tech", 120000.0],
        ["Tech", 140000.0],
        ["HR", 50000.0],
        ["Sales", 60000.0],
        ["Sales", 80000.0],
    ]
    cols = [
        ("dept", DuckType.STRING),
        ("salary", DuckType.FLOAT64),
    ]
    ctx.create_table_from_rows("org", cols, data, chunk_size=2)

    query = "SELECT dept, AVG(salary) AS avg_sal FROM org GROUP BY dept HAVING avg_sal > 80000.0;"
    df = ctx.sql(query)
    records = df.to_dict()

    assert len(records) == 1
    assert records[0]["dept"] == "Tech"
    assert records[0]["avg_sal"] == 120000.0


def test_sql_inner_join_execution():
    ctx = DuckPyContext()

    users_data = [
        [1, "Alice", 10],
        [2, "Bob", 20],
        [3, "Charlie", 30],
    ]
    users_cols = [
        ("id", DuckType.INT64),
        ("username", DuckType.STRING),
        ("dept_id", DuckType.INT64),
    ]
    ctx.create_table_from_rows("accounts", users_cols, users_data, chunk_size=2)

    depts_data = [
        [10, "Engineering"],
        [20, "Product"],
    ]
    depts_cols = [
        ("dept_id", DuckType.INT64),
        ("dept_title", DuckType.STRING),
    ]
    ctx.create_table_from_rows("departments", depts_cols, depts_data, chunk_size=2)

    query = (
        "SELECT username, dept_title "
        "FROM accounts "
        "INNER JOIN departments ON accounts.dept_id = departments.dept_id "
        "WHERE dept_id = 10;"
    )
    df = ctx.sql(query)
    records = df.to_dict()

    assert len(records) == 1
    assert records[0] == {"username": "Alice", "dept_title": "Engineering"}


def test_sql_union_and_union_all():
    ctx = DuckPyContext()

    branch_a_data = [
        [101, "Server_A"],
        [102, "Server_B"],
    ]
    branch_b_data = [
        [102, "Server_B"],  # Duplicate row
        [103, "Server_C"],
    ]
    node_cols = [
        ("node_id", DuckType.INT64),
        ("node_name", DuckType.STRING),
    ]

    ctx.create_table_from_rows("cluster_a", node_cols, branch_a_data, chunk_size=2)
    ctx.create_table_from_rows("cluster_b", node_cols, branch_b_data, chunk_size=2)

    # 1. UNION ALL
    query_all = "SELECT node_id, node_name FROM cluster_a UNION ALL SELECT node_id, node_name FROM cluster_b;"
    res_all = ctx.sql(query_all).to_dict()
    assert len(res_all) == 4

    # 2. UNION DISTINCT
    query_distinct = "SELECT node_id, node_name FROM cluster_a UNION SELECT node_id, node_name FROM cluster_b;"
    res_distinct = ctx.sql(query_distinct).to_dict()
    assert len(res_distinct) == 3
    node_names = [r["node_name"] for r in res_distinct]
    assert "Server_A" in node_names
    assert "Server_B" in node_names
    assert "Server_C" in node_names