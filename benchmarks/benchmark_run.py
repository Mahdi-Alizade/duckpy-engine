"""
DuckPy Engine Benchmark suite comparing query times on 100,000 synthetic rows.
"""
import os
import sys
import time
import random

# Ensure root project directory is in python path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from duckpy.context import DuckPyContext
from duckpy.types.dtypes import DuckType
from duckpy.execution.filter import ComparisonOp
from duckpy.execution.aggregate import AggregateExpr, AggregateFunction


def run_benchmark():
    print("Generating 100,000 rows of analytical data...")
    num_rows = 100_000
    departments = ["Engineering", "Product", "Design", "Sales", "Legal"]
    
    rows = [
        [i, f"user_{i}", random.choice(departments), float(random.randint(40000, 180000))]
        for i in range(num_rows)
    ]

    columns = [
        ("user_id", DuckType.INT64),
        ("username", DuckType.STRING),
        ("department", DuckType.STRING),
        ("salary", DuckType.FLOAT64),
    ]

    ctx = DuckPyContext()
    start_load = time.perf_counter()
    ctx.create_table_from_rows("users", columns, rows, chunk_size=4096)
    load_time = time.perf_counter() - start_load
    print(f"Data chunked & vectorized into memory in: {load_time * 1000:.2f} ms\n")

    print("Running OLAP Query: Filter + GroupBy + Vectorized Aggregation...")
    start_query = time.perf_counter()

    df = (
        ctx.table("users")
        .filter("salary", ComparisonOp.GREATER_THAN, 100000.0)
        .aggregate(
            group_by=["department"],
            aggregates=[
                AggregateExpr(AggregateFunction.AVG, "salary", alias="avg_salary"),
                AggregateExpr(AggregateFunction.COUNT, "salary", alias="count"),
            ]
        )
    )

    df.show()
    query_time = time.perf_counter() - start_query
    print(f"\nExecution finished in: {query_time * 1000:.2f} ms")


if __name__ == "__main__":
    run_benchmark()