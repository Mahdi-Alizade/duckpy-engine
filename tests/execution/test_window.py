from duckpy.types.dtypes import DuckType
from duckpy.storage.schema import Schema, ColumnDefinition
from duckpy.storage.chunk import DataChunk
from duckpy.execution.scan import PhysicalScan
from duckpy.execution.window import PhysicalWindow, WindowSpec, WindowFunctionType


def test_window_row_number_partition_by():
    schema = Schema([
        ColumnDefinition("dept", DuckType.STRING),
        ColumnDefinition("score", DuckType.FLOAT64),
    ])

    chunk = DataChunk(schema, capacity=4)
    chunk.append_row(["Sales", 100.0])
    chunk.append_row(["Tech", 200.0])
    chunk.append_row(["Sales", 150.0])
    chunk.append_row(["Tech", 180.0])

    scan_op = PhysicalScan(schema, [chunk])

    # ROW_NUMBER() OVER (PARTITION BY dept ORDER BY score)
    spec = WindowSpec(
        func_type=WindowFunctionType.ROW_NUMBER,
        partition_by=["dept"],
        order_by=["score"],
        alias="row_num"
    )

    win_op = PhysicalWindow(scan_op, spec)
    win_op.init()

    res_chunk = win_op.execute_chunk()
    assert res_chunk is not None
    rows = res_chunk.to_rows()

    # Sales rows: 100 -> 1, 150 -> 2
    sales_rows = [r for r in rows if r[0] == "Sales"]
    assert sales_rows[0] == ["Sales", 100.0, 1]
    assert sales_rows[1] == ["Sales", 150.0, 2]

    # Tech rows: 180 -> 1, 200 -> 2
    tech_rows = [r for r in rows if r[0] == "Tech"]
    assert tech_rows[0] == ["Tech", 180.0, 1]
    assert tech_rows[1] == ["Tech", 200.0, 2]


def test_window_rank_with_ties():
    schema = Schema([
        ColumnDefinition("dept", DuckType.STRING),
        ColumnDefinition("score", DuckType.FLOAT64),
    ])

    chunk = DataChunk(schema, capacity=4)
    chunk.append_row(["Tech", 100.0])
    chunk.append_row(["Tech", 100.0])
    chunk.append_row(["Tech", 150.0])

    scan_op = PhysicalScan(schema, [chunk])

    # RANK() OVER (PARTITION BY dept ORDER BY score)
    spec = WindowSpec(
        func_type=WindowFunctionType.RANK,
        partition_by=["dept"],
        order_by=["score"],
        alias="rank_val"
    )

    win_op = PhysicalWindow(scan_op, spec)
    win_op.init()

    res_chunk = win_op.execute_chunk()
    assert res_chunk is not None
    rows = res_chunk.to_rows()

    assert rows[0] == ["Tech", 100.0, 1]
    assert rows[1] == ["Tech", 100.0, 1]
    assert rows[2] == ["Tech", 150.0, 3]