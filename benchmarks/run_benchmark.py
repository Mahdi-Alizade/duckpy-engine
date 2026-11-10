import time
import random
from duckpy.types.dtypes import DuckType
from duckpy.context import DuckPyContext
from duckpy.execution.filter import ComparisonOp
from duckpy.execution.aggregate import AggregateExpr, AggregateFunction


def generate_benchmark_dataset(num_rows: int = 100_000):
    departments = ["Engineering", "Sales", "Marketing", "Finance", "HumanResources"]
    dataset = []
    
    random.seed(42)
    for idx in range(num_rows):
        emp_id = idx + 1
        dept = random.choice(departments)
        salary = round(random.uniform(40_000.0, 180_000.0), 2)
        rating = round(random.uniform(1.0, 5.0), 1)
        dataset.append([emp_id, dept, salary, rating])
        
    return dataset


def run_benchmark():
    print("=" * 65)
    print("🚀 DuckPy Vectorized Columnar Engine Benchmark (100k Rows)")
    print("=" * 65)

    total_records = 100_000
    print(f"Generating synthetic dataset of {total_records:,} records...")
    t_start = time.perf_counter()
    raw_data = generate_benchmark_dataset(total_records)
    t_gen = time.perf_counter() - t_start
    print(f"Data generated in {t_gen:.4f}s")

    cols = [
        ("emp_id", DuckType.INT64),
        ("dept", DuckType.STRING),
        ("salary", DuckType.FLOAT64),
        ("rating", DuckType.FLOAT64),
    ]

    ctx = DuckPyContext()
    t_ingest_start = time.perf_counter()
    ctx.create_table_from_rows("employees", cols, raw_data, chunk_size=4096)
    t_ingest = time.perf_counter() - t_ingest_start
    print(f"Columnar chunks ingestion ({total_records:,} rows) took: {t_ingest:.4f}s\n")

    # Benchmark 1: Vectorized Filter & Projection
    print("--- Benchmark 1: Vectorized Filter & Projection ---")
    print("Query: SELECT dept, salary FROM employees WHERE salary > 120000.0")
    b1_start = time.perf_counter()
    df1 = (
        ctx.table("employees")
        .filter("salary", ComparisonOp.GREATER_THAN, 120_000.0)
        .select("dept", "salary")
    )
    res1 = df1.to_dict()
    b1_time = time.perf_counter() - b1_start
    print(f"Matched {len(res1):,} rows in {b1_time:.4f}s ({len(res1) / b1_time:,.0f} rows/s)\n")

    # Benchmark 2: Group By & Hash Aggregation
    print("--- Benchmark 2: Group By & Hash Aggregation ---")
    print("Query: SELECT dept, AVG(salary), COUNT(salary) FROM employees GROUP BY dept")
    b2_start = time.perf_counter()
    df2 = (
        ctx.table("employees")
        .aggregate(
            group_by=["dept"],
            aggregates=[
                AggregateExpr(AggregateFunction.AVG, "salary", alias="avg_salary"),
                AggregateExpr(AggregateFunction.COUNT, "salary", alias="emp_count"),
            ]
        )
    )
    res2 = df2.to_dict()
    b2_time = time.perf_counter() - b2_start
    print(f"Aggregated into {len(res2)} groups in {b2_time:.4f}s ({total_records / b2_time:,.0f} input rows/s)")
    for row in res2:
        print(f"  - {row['dept']}: Count={row['emp_count']:,}, Avg Salary={row['avg_salary']:,.2f}")
    print()

    # Benchmark 3: Pure SQL Pipeline Execution
    print("--- Benchmark 3: Full SQL Execution (WHERE + ORDER BY + LIMIT) ---")
    sql_query = "SELECT dept, salary FROM employees WHERE salary > 150000.0 ORDER BY salary DESC LIMIT 5;"
    print(f"SQL: {sql_query}")
    b3_start = time.perf_counter()
    df3 = ctx.sql(sql_query)
    res3 = df3.to_dict()
    b3_time = time.perf_counter() - b3_start
    print(f"Executed full SQL in {b3_time:.4f}s")
    for r in res3:
        print(f"  * Dept: {r['dept']} | Salary: {r['salary']:,.2f}")

    print("\n" + "=" * 65)
    print("✅ Benchmark Completed Successfully")
    print("=" * 65)


if __name__ == "__main__":
    run_benchmark()