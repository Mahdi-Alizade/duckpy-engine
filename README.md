# DuckPy Engine 🦆⚡

A high-performance in-memory Columnar OLAP Query Engine built from first principles in Python, featuring Morsel-driven vectorized execution, zero-copy selection vectors, custom bitmap null management, and a Rule-Based Query Optimizer (RBO).

---

## 🏛 Architecture Overview

[ Fluent DataFrame API / SQL Interface ]
│
▼
[ Logical Query Tree ]
│
▼
[ Rule-Based Optimizer (RBO) ]
(Predicate Pushdown & Column Pruning)
│
▼
[ Physical Operator Pipeline ]
(VectorizedFilter ➔ PhysicalProjection ➔ HashAggregate)
│
▼
[ In-Memory Columnar Store ]
(DataChunks • Vectors • Compact BitMaps)


---

## 🚀 Key Features

* **Columnar Storage Model:** Data is organized in contiguous typed `Vector` arrays (`INT64`, `FLOAT64`, `STRING`, `BOOLEAN`) to ensure optimal CPU cache locality and reduce memory overhead compared to row-oriented storage.
* **Vectorized Execution Engine:** Processes records in horizontal batches (`DataChunk`) rather than single-tuple iterations (Volcano Model), drastically reducing Python interpreter overhead.
* **Null BitMaps:** Zero-overhead bytearray-backed bitmask tracking for `NULL` values without allocating empty object pointers.
* **Rule-Based Optimizer (RBO):** Automatically transforms logical query trees to push filters down closer to scans (`Predicate Pushdown`).
* **In-Memory Hash Aggregation:** High-speed vectorized grouping and aggregation supporting `SUM`, `AVG`, `COUNT`, `MIN`, and `MAX`.
* **Zero External Runtime Dependencies:** Built strictly using the Python Standard Library for maximum portability and core systems understanding.

---

## 💻 Quick Start

### Installation

```bash
# Clone repository
git clone [https://github.com/your-username/duckpy-engine.git](https://github.com/your-username/duckpy-engine.git)
cd duckpy-engine

# Setup virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install editable package with dev tools
pip install -e .
Usage Example
Python
from duckpy import DuckPyContext, DuckType, ComparisonOp, AggregateExpr, AggregateFunction

ctx = DuckPyContext()

# Define schema and data
columns = [
    ("emp_id", DuckType.INT64),
    ("department", DuckType.STRING),
    ("salary", DuckType.FLOAT64),
]

data = [
    [101, "Engineering", 140000.0],
    [102, "Engineering", 125000.0],
    [103, "Marketing", 92000.0],
    [104, "Marketing", 105000.0],
]

# Ingest and create table
ctx.create_table_from_rows("employees", columns, data, chunk_size=2048)

# Execute analytical query with lazy evaluation
results = (
    ctx.table("employees")
    .filter("salary", ComparisonOp.GREATER_THAN, 100000.0)
    .aggregate(
        group_by=["department"],
        aggregates=[
            AggregateExpr(AggregateFunction.AVG, "salary", alias="avg_salary"),
            AggregateExpr(AggregateFunction.COUNT, "salary", alias="emp_count"),
        ]
    )
    .to_dict()
)

print(results)
🧪 Running Tests & Benchmarks
Unit & Pipeline Tests
Bash
pytest -v --cov=duckpy
Performance Benchmark (100,000 Rows)
Bash
python benchmarks/benchmark_run.py
🛠 Tech Stack & Engineering Practices
Language: Python 3.10+ (Pure Standard Library Core)

Testing: PyTest, Hypothesis (Property-based testing)

Code Quality: Ruff, MyPy (Strict Static Typing)

Design Patterns: Relational Algebra, AST Query Compilation, Morsel Vectorization, Bitmask Indexing