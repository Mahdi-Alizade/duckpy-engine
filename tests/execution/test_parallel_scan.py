import pytest
from duckpy.types.dtypes import DuckType
from duckpy.storage.schema import Schema, ColumnDefinition
from duckpy.storage.chunk import DataChunk
from duckpy.execution.parallel_scan import ParallelScan


def test_parallel_scan_basic_execution():
    schema = Schema([
        ColumnDefinition("id", DuckType.INT64),
        ColumnDefinition("score", DuckType.FLOAT64),
    ])

    chunk1 = DataChunk(schema, capacity=2)
    chunk1.append_row([1, 10.0])
    chunk1.append_row([2, 20.0])

    chunk2 = DataChunk(schema, capacity=2)
    chunk2.append_row([3, 30.0])
    chunk2.append_row([4, 40.0])

    chunk3 = DataChunk(schema, capacity=2)
    chunk3.append_row([5, 50.0])

    op = ParallelScan(schema, [chunk1, chunk2, chunk3], max_workers=3)
    op.init()

    collected_rows = []
    while True:
        chunk = op.execute_chunk()
        if chunk is None:
            break
        for row in chunk.to_rows():
            collected_rows.append(row)

    assert len(collected_rows) == 5
    assert collected_rows[0] == [1, 10.0]
    assert collected_rows[4] == [5, 50.0]


def test_parallel_scan_with_filter_transformation():
    schema = Schema([
        ColumnDefinition("id", DuckType.INT64),
        ColumnDefinition("is_valid", DuckType.BOOLEAN),
    ])

    chunk1 = DataChunk(schema, capacity=2)
    chunk1.append_row([1, True])
    chunk1.append_row([2, False])

    chunk2 = DataChunk(schema, capacity=2)
    chunk2.append_row([3, True])
    chunk2.append_row([4, True])

    # Filter out False rows inside worker
    def filter_only_true(c: DataChunk) -> DataChunk:
        out_chunk = DataChunk(c.schema, capacity=c.card)
        for r_idx in range(c.card):
            val = c.get_vector("is_valid").get(r_idx)
            if val is True:
                out_chunk.append_row([c.get_vector(0).get(r_idx), val])
        return out_chunk

    op = ParallelScan(schema, [chunk1, chunk2], max_workers=2, transform_fn=filter_only_true)
    op.init()

    all_ids = []
    while True:
        chunk = op.execute_chunk()
        if chunk is None:
            break
        for row in chunk.to_rows():
            all_ids.append(row[0])

    assert all_ids == [1, 3, 4]