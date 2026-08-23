import pytest
from duckpy.types.dtypes import DuckType
from duckpy.storage.schema import Schema, ColumnDefinition
from duckpy.storage.chunk import DataChunk
from duckpy.execution.scan import PhysicalScan
from duckpy.execution.filter import VectorizedFilter, ComparisonOp


def test_vectorized_filter_pipeline():
    schema = Schema([
        ColumnDefinition("id", DuckType.INT64),
        ColumnDefinition("score", DuckType.FLOAT64),
    ])

    chunk1 = DataChunk(schema, capacity=3)
    chunk1.append_row([1, 85.5])
    chunk1.append_row([2, 42.0])
    chunk1.append_row([3, 91.0])

    chunk2 = DataChunk(schema, capacity=3)
    chunk2.append_row([4, 60.0])
    chunk2.append_row([5, None])
    chunk2.append_row([6, 75.0])

    scan_op = PhysicalScan(schema, [chunk1, chunk2])
    
    # Filter: score > 70.0
    filter_op = VectorizedFilter(
        child=scan_op,
        column_name="score",
        op=ComparisonOp.GREATER_THAN,
        target_value=70.0
    )
    filter_op.init()

    # First chunk result: id 1 (85.5) and id 3 (91.0)
    out1 = filter_op.execute_chunk()
    assert out1 is not None
    assert out1.card == 2
    assert out1.to_rows() == [
        [1, 85.5],
        [3, 91.0]
    ]

    # Second chunk result: id 6 (75.0)
    out2 = filter_op.execute_chunk()
    assert out2 is not None
    assert out2.card == 1
    assert out2.to_rows() == [
        [6, 75.0]
    ]

    # Exhausted
    out3 = filter_op.execute_chunk()
    assert out3 is None