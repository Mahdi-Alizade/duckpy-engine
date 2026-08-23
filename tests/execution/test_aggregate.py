from duckpy.types.dtypes import DuckType
from duckpy.storage.schema import Schema, ColumnDefinition
from duckpy.storage.chunk import DataChunk
from duckpy.execution.scan import PhysicalScan
from duckpy.execution.projection import PhysicalProjection
from duckpy.execution.aggregate import (
    PhysicalHashAggregate,
    AggregateExpr,
    AggregateFunction,
)


def test_projection_operator():
    schema = Schema([
        ColumnDefinition("id", DuckType.INT64),
        ColumnDefinition("name", DuckType.STRING),
        ColumnDefinition("balance", DuckType.FLOAT64),
    ])

    chunk = DataChunk(schema, capacity=2)
    chunk.append_row([1, "Alice", 150.0])
    chunk.append_row([2, "Bob", 200.0])

    scan_op = PhysicalScan(schema, [chunk])
    proj_op = PhysicalProjection(scan_op, ["name", "balance"])
    proj_op.init()

    out = proj_op.execute_chunk()
    assert out is not None
    assert out.schema.column_count == 2
    assert out.to_rows() == [
        ["Alice", 150.0],
        ["Bob", 200.0]
    ]


def test_hash_aggregate_group_by():
    schema = Schema([
        ColumnDefinition("department", DuckType.STRING),
        ColumnDefinition("salary", DuckType.FLOAT64),
    ])

    chunk = DataChunk(schema, capacity=5)
    chunk.append_row(["Engineering", 3000.0])
    chunk.append_row(["Engineering", 5000.0])
    chunk.append_row(["HR", 2000.0])
    chunk.append_row(["HR", 2500.0])

    scan_op = PhysicalScan(schema, [chunk])
    
    # GROUP BY department, AVG(salary), COUNT(salary)
    agg_op = PhysicalHashAggregate(
        child=scan_op,
        group_by_columns=["department"],
        aggregates=[
            AggregateExpr(AggregateFunction.AVG, "salary", alias="avg_salary"),
            AggregateExpr(AggregateFunction.COUNT, "salary", alias="emp_count"),
        ]
    )
    agg_op.init()

    out = agg_op.execute_chunk()
    assert out is not None
    assert out.card == 2

    rows_dict = {row[0]: (row[1], row[2]) for row in out.to_rows()}
    assert rows_dict["Engineering"] == (4000.0, 2)
    assert rows_dict["HR"] == (2250.0, 2)