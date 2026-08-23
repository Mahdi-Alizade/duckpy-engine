from duckpy.types.dtypes import DuckType
from duckpy.storage.schema import Schema, ColumnDefinition
from duckpy.storage.chunk import DataChunk
from duckpy.execution.filter import ComparisonOp
from duckpy.optimizer.logical_plan import (
    LogicalScan,
    LogicalFilter,
    LogicalProjection,
)
from duckpy.optimizer.optimizer import Optimizer


def test_predicate_pushdown_and_execution():
    schema = Schema([
        ColumnDefinition("id", DuckType.INT64),
        ColumnDefinition("score", DuckType.FLOAT64),
        ColumnDefinition("department", DuckType.STRING),
    ])

    chunk = DataChunk(schema, capacity=3)
    chunk.append_row([1, 95.0, "Engineering"])
    chunk.append_row([2, 50.0, "Sales"])
    chunk.append_row([3, 80.0, "Engineering"])

    catalog = {"employees": [chunk]}

    # Build unoptimized tree: Projection(Filter(Scan))
    scan = LogicalScan("employees", schema)
    filtered = LogicalFilter(scan, "score", ComparisonOp.GREATER_THAN, 75.0)
    projected = LogicalProjection(filtered, ["id", "department"])

    # Optimize & compile
    optimized_plan = Optimizer.pushdown_predicates(projected)
    physical_pipeline = Optimizer.to_physical(optimized_plan, catalog)
    physical_pipeline.init()

    # Execute
    result_chunk = physical_pipeline.execute_chunk()
    assert result_chunk is not None
    assert result_chunk.schema.column_count == 2
    assert result_chunk.to_rows() == [
        [1, "Engineering"],
        [3, "Engineering"]
    ]