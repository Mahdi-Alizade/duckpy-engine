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