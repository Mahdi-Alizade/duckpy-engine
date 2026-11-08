from duckpy.types.dtypes import DuckType
from duckpy.storage.schema import Schema, ColumnDefinition
from duckpy.storage.chunk import DataChunk
from duckpy.execution.scan import PhysicalScan
from duckpy.execution.hash_join import PhysicalHashJoin, JoinType


def test_physical_inner_hash_join():
    # Left table: Employees (emp_id, name, dept_id)
    left_schema = Schema([
        ColumnDefinition("emp_id", DuckType.INT64),
        ColumnDefinition("name", DuckType.STRING),
        ColumnDefinition("dept_id", DuckType.INT64),
    ])
    chunk_l = DataChunk(left_schema, capacity=3)
    chunk_l.append_row([1, "Alice", 10])
    chunk_l.append_row([2, "Bob", 20])
    chunk_l.append_row([3, "Charlie", 30])  # No matching dept in right table
    left_scan = PhysicalScan(left_schema, [chunk_l])

    # Right table: Departments (dept_id, dept_name)
    right_schema = Schema([
        ColumnDefinition("dept_id", DuckType.INT64),
        ColumnDefinition("dept_name", DuckType.STRING),
    ])
    chunk_r = DataChunk(right_schema, capacity=2)
    chunk_r.append_row([10, "Engineering"])
    chunk_r.append_row([20, "Sales"])
    right_scan = PhysicalScan(right_schema, [chunk_r])

    join_op = PhysicalHashJoin(
        left_child=left_scan,
        right_child=right_scan,
        left_on="dept_id",
        right_on="dept_id",
        join_type=JoinType.INNER
    )
    join_op.init()

    res_chunk = join_op.execute_chunk()
    assert res_chunk is not None
    assert res_chunk.card == 2

    rows = res_chunk.to_rows()
    assert rows[0] == [1, "Alice", 10, 10, "Engineering"]
    assert rows[1] == [2, "Bob", 20, 20, "Sales"]


def test_physical_left_hash_join_with_null_padding():
    left_schema = Schema([
        ColumnDefinition("id", DuckType.INT64),
        ColumnDefinition("city_id", DuckType.INT64),
    ])
    chunk_l = DataChunk(left_schema, capacity=2)
    chunk_l.append_row([1, 100])
    chunk_l.append_row([2, 999])  # Missing in right
    left_scan = PhysicalScan(left_schema, [chunk_l])

    right_schema = Schema([
        ColumnDefinition("city_id", DuckType.INT64),
        ColumnDefinition("city_name", DuckType.STRING),
    ])
    chunk_r = DataChunk(right_schema, capacity=1)
    chunk_r.append_row([100, "Tehran"])
    right_scan = PhysicalScan(right_schema, [chunk_r])

    join_op = PhysicalHashJoin(
        left_child=left_scan,
        right_child=right_scan,
        left_on="city_id",
        right_on="city_id",
        join_type=JoinType.LEFT
    )
    join_op.init()

    res_chunk = join_op.execute_chunk()
    assert res_chunk is not None
    assert res_chunk.card == 2

    rows = res_chunk.to_rows()
    assert rows[0] == [1, 100, 100, "Tehran"]
    assert rows[1] == [2, 999, None, None]