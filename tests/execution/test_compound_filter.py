from duckpy.types.dtypes import DuckType
from duckpy.storage.schema import Schema, ColumnDefinition
from duckpy.storage.chunk import DataChunk
from duckpy.execution.scan import PhysicalScan
from duckpy.execution.filter import ComparisonOp
from duckpy.execution.logical_filter import (
    VectorizedLogicalFilter,
    BooleanLogicOp,
    FilterCondition,
)


def test_vectorized_logical_filter_and():
    schema = Schema([
        ColumnDefinition("emp_id", DuckType.INT64),
        ColumnDefinition("department", DuckType.STRING),
        ColumnDefinition("salary", DuckType.FLOAT64),
    ])

    chunk = DataChunk(schema, capacity=4)
    chunk.append_row([1, "Tech", 95000.0])
    chunk.append_row([2, "Tech", 120000.0])
    chunk.append_row([3, "Finance", 130000.0])
    chunk.append_row([4, "Tech", 70000.0])

    scan_op = PhysicalScan(schema, [chunk])

    # Condition: department == 'Tech' AND salary >= 90000.0
    left_c = FilterCondition("department", ComparisonOp.EQUAL, "Tech")
    right_c = FilterCondition("salary", ComparisonOp.GREATER_THAN_OR_EQUAL, 90000.0)

    filter_op = VectorizedLogicalFilter(scan_op, left_c, BooleanLogicOp.AND, right_c)
    filter_op.init()

    res = filter_op.execute_chunk()
    assert res is not None
    assert res.card == 2
    assert res.to_rows() == [
        [1, "Tech", 95000.0],
        [2, "Tech", 120000.0]
    ]


def test_vectorized_logical_filter_or():
    schema = Schema([
        ColumnDefinition("status", DuckType.STRING),
        ColumnDefinition("score", DuckType.FLOAT64),
    ])

    chunk = DataChunk(schema, capacity=4)
    chunk.append_row(["ACTIVE", 40.0])
    chunk.append_row(["INACTIVE", 95.0])
    chunk.append_row(["INACTIVE", 50.0])
    chunk.append_row([None, 99.0])

    scan_op = PhysicalScan(schema, [chunk])

    # Condition: status == 'ACTIVE' OR score >= 90.0
    left_c = FilterCondition("status", ComparisonOp.EQUAL, "ACTIVE")
    right_c = FilterCondition("score", ComparisonOp.GREATER_THAN_OR_EQUAL, 90.0)

    filter_op = VectorizedLogicalFilter(scan_op, left_c, BooleanLogicOp.OR, right_c)
    filter_op.init()

    res = filter_op.execute_chunk()
    assert res is not None
    assert res.card == 3
    assert res.to_rows() == [
        ["ACTIVE", 40.0],
        ["INACTIVE", 95.0],
        [None, 99.0]
    ]