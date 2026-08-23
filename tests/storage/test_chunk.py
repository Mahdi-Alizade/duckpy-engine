import pytest
from duckpy.types.dtypes import DuckType
from duckpy.storage.schema import Schema, ColumnDefinition
from duckpy.storage.chunk import DataChunk


def test_schema_creation_and_lookup():
    col1 = ColumnDefinition("id", DuckType.INT64)
    col2 = ColumnDefinition("price", DuckType.FLOAT64)
    col3 = ColumnDefinition("name", DuckType.STRING)
    
    schema = Schema([col1, col2, col3])
    
    assert schema.column_count == 3
    assert schema.get_column_index("price") == 1
    assert schema.get_column(0).name == "id"
    assert schema.get_column("name").dtype == DuckType.STRING

    with pytest.raises(ValueError):
        Schema([ColumnDefinition("id", DuckType.INT64), ColumnDefinition("id", DuckType.FLOAT64)])


def test_datachunk_row_append_and_access():
    schema = Schema([
        ColumnDefinition("user_id", DuckType.INT64),
        ColumnDefinition("balance", DuckType.FLOAT64),
        ColumnDefinition("is_active", DuckType.BOOLEAN),
    ])

    chunk = DataChunk(schema, capacity=3)
    chunk.append_row([101, 250.75, True])
    chunk.append_row([102, None, False])

    assert chunk.card == 2
    assert chunk.get_vector("user_id").get(0) == 101
    assert chunk.get_vector("balance").get(1) is None
    assert chunk.get_vector(2).get(0) is True

    rows = chunk.to_rows()
    assert rows == [
        [101, 250.75, True],
        [102, None, False]
    ]


def test_datachunk_capacity_overflow():
    schema = Schema([ColumnDefinition("val", DuckType.INT64)])
    chunk = DataChunk(schema, capacity=1)
    chunk.append_row([1])

    with pytest.raises(OverflowError):
        chunk.append_row([2])