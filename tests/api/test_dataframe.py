from duckpy.types.dtypes import DuckType
from duckpy.context import DuckPyContext
from duckpy.execution.filter import ComparisonOp
from duckpy.execution.aggregate import AggregateExpr, AggregateFunction


def test_end_to_end_dataframe_query():
    ctx = DuckPyContext()

    data = [
        [1, "Alice", "Tech", 120000.0],
        [2, "Bob", "Tech", 95000.0],
        [3, "Charlie", "Finance", 110000.0],
        [4, "Diana", "Finance", 80000.0],
        [5, "Evan", "Tech", 70000.0],
    ]

    columns = [
        ("id", DuckType.INT64),
        ("name", DuckType.STRING),
        ("department", DuckType.STRING),
        ("salary", DuckType.FLOAT64),
    ]

    ctx.create_table_from_rows("employees", columns, data, chunk_size=2)

    # Query: SELECT department, AVG(salary), COUNT(salary) WHERE salary >= 90000 GROUP BY department
    res = (
        ctx.table("employees")
        .filter("salary", ComparisonOp.GREATER_THAN_OR_EQUAL, 90000.0)
        .aggregate(
            group_by=["department"],
            aggregates=[
                AggregateExpr(AggregateFunction.AVG, "salary", alias="avg_salary"),
                AggregateExpr(AggregateFunction.COUNT, "salary", alias="headcount"),
            ]
        )
        .to_dict()
    )

    res_map = {r["department"]: (r["avg_salary"], r["headcount"]) for r in res}
    
    # Tech above 90k: Alice(120k), Bob(95k) -> avg: 107500.0, count: 2
    assert res_map["Tech"] == (107500.0, 2)
    # Finance above 90k: Charlie(110k) -> avg: 110000.0, count: 1
    assert res_map["Finance"] == (110000.0, 1)