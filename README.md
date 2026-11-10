# 🦆 DuckPy Engine

[![DuckPy Engine CI](https://github.com/MahdiAlizadeh/duckpy-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/MahdiAlizadeh/duckpy-engine/actions/workflows/ci.yml)
[![Python Version](https://img.shields.io/badge/python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests Coverage](https://img.shields.io/badge/tests-46%20passed-brightgreen.svg)]()

**DuckPy Engine** is an in-memory, vectorized columnar analytical database (OLAP) engine built from scratch in pure Python using only standard library primitives. Inspired by modern database systems like **DuckDB** and **Apache Arrow**, it demonstrates high-throughput analytical query processing via contiguous chunk-based vectors, bitmap null management, dictionary and run-length encoding (RLE), rule-based optimization (RBO), and multi-engine query interfaces (fluent DataFrame API + SQL parser).

---

## 🏛️ System Architecture

```text
               +-------------------------------------------+
               | User Interfaces: SQL Query / DataFrame API|
               +-------------------------------------------+
                                     |
                                     v
               +-------------------------------------------+
               |        Logical Relational Tree Plan       |
               |  (Scan, Filter, Project, Join, Agg, Win)  |
               +-------------------------------------------+
                                     |
                                     v
               +-------------------------------------------+
               |     Rule-Based Optimizer (RBO Engine)     |
               |   - Predicate Pushdown                    |
               |   - Projection Pruning & Plan Rewriting   |
               +-------------------------------------------+
                                     |
                                     v
               +-------------------------------------------+
               |       Vectorized Physical Pipeline        |
               | (Morsel / Chunk Pull-based Volcano Engine)|
               +-------------------------------------------+
                                     |
                                     v
    +-----------------------------------------------------------------+
    |                     Columnar Storage Layer                      |
    |  - DataChunk (Horizontal row slices in contiguous columns)      |
    |  - Vector / RLEVector / DictionaryVector                        |
    |  - BitMap (Compact bitwise null representation)                 |
    |  - SelectionVector (Zero-copy filtered index views)             |
    +-----------------------------------------------------------------+
✨ Key Architectural FeaturesColumnar Storage Model: Data is laid out vertically by attribute, drastically reducing memory bandwidth during column scans and aggregate projections.Vectorized Chunk Execution: Processing proceeds in morsels (DataChunk, default 2048 rows), maximizing CPU cache locality and amortizing Python function call overhead.Pluggable Vector Compression:Vector: Contiguous flat typed array with byte-level BitMap null mask.RLEVector: Run-Length Encoded vector for repetitive low-cardinality sequences.DictionaryVector: Dictionary encoding for high repetition strings/integers.SelectionVector: Indirect row indices allowing zero-copy predicate evaluations.Rule-Based Optimizer (RBO): Pushes down single and compound predicates through projections, joins, and relational transformations before physical instantiation.Physical Relational Algebra Operators:PhysicalScan & ParallelScan (Thread-pool multi-chunk scans)VectorizedFilter & VectorizedLogicalFilter (Compound AND / OR expressions)PhysicalProjectionPhysicalHashAggregate (COUNT, SUM, AVG, MIN, MAX)PhysicalHaving (Post-aggregation filtering)PhysicalOrderBy (Multi-key comparator with database-standard NULLS LAST)PhysicalLimit (Early pipeline short-circuiting)PhysicalHashJoin (INNER and LEFT join build-probe pipeline)PhysicalWindow (ROW_NUMBER, RANK over partition specs)PhysicalUnion (UNION ALL and deduplicated UNION DISTINCT)PhysicalSetOperation (INTERSECT and EXCEPT / MINUS)Binary Disk Persistence: Native custom binary file format (.duck) packing schema metadata and chunk vectors with sub-millisecond roundtrips.Dual Query API: Complete fluent lazy DataFrame API coupled with a SimpleSQLParser compiling SQL queries into optimized logical execution trees.⚡ Performance Benchmarks (100,000 Rows)Tested on Python 3.13 (Standard CPython without native extensions):WorkloadRecords EvaluatedExecution TimeThroughputData Ingestion into Chunks100,000 rows0.4388s~228,000 rows/sVectorized Filter & Projection100,000 rows (42,947 matches)0.6244s~68,777 rows/sGroup-By & Hash Aggregation100,000 rows (5 groups, 2 aggs)0.3568s~280,255 rows/sFull SQL (WHERE + ORDER BY + LIMIT)100,000 rows0.4864s~205,500 rows/sRun the benchmarks locally:PowerShellpython benchmarks/run_benchmark.py
🚀 Quickstart Guide1. Installation & Environment SetupPowerShell# Clone the repository
git clone [https://github.com/MahdiAlizadeh/duckpy-engine.git](https://github.com/MahdiAlizadeh/duckpy-engine.git)
cd duckpy-engine

# Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install testing dependencies
pip install pytest pytest-cov hypothesis
2. Using the SQL EnginePythonfrom duckpy.types.dtypes import DuckType
from duckpy.context import DuckPyContext

ctx = DuckPyContext()

# Register a table
schema = [
    ("emp_id", DuckType.INT64),
    ("dept", DuckType.STRING),
    ("salary", DuckType.FLOAT64),
]
data = [
    [1, "Tech", 120000.0],
    [2, "Tech", 95000.0],
    [3, "Sales", 85000.0],
    [4, "Tech", 140000.0],
    [5, "Sales", 60000.0],
]
ctx.create_table_from_rows("employees", schema, data)

# Run analytical SQL queries
query = """
SELECT dept, AVG(salary) AS avg_sal, COUNT(salary) AS emp_count
FROM employees
WHERE salary >= 80000.0
GROUP BY dept
HAVING avg_sal > 90000.0
ORDER BY avg_sal DESC;
"""
df = ctx.sql(query)
df.show()
3. Using the Fluent DataFrame APIPythonfrom duckpy.execution.filter import ComparisonOp
from duckpy.execution.expressions import (
    ColumnRefExpr,
    BinaryArithmeticExpr,
    ArithmeticOp,
    LiteralExpr,
)

# Apply vector transformations and computed columns
tax_expr = BinaryArithmeticExpr(
    left=ColumnRefExpr("salary"),
    op=ArithmeticOp.MULTIPLY,
    right=LiteralExpr(0.20, DuckType.FLOAT64)
)

result = (
    ctx.table("employees")
    .filter("salary", ComparisonOp.GREATER_THAN, 90000.0)
    .with_column("tax_amount", tax_expr)
    .select("emp_id", "dept", "salary", "tax_amount")
    .order_by("salary", ascending=False)
    .limit(2)
)

print(result.to_dict())
🧪 Testing SuiteDuckPy maintains an automated unit and integration testing suite covering storage structures, rule optimization, bitmask manipulation, and operators:PowerShell# Run full test suite
pytest -v

# Run tests with duration tracking
pytest -v --durations=5
📜 LicenseThis project is licensed under the MIT License. See the LICENSE file for details.