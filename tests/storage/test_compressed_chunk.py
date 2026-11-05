from duckpy.types.dtypes import DuckType
from duckpy.storage.schema import Schema, ColumnDefinition
from duckpy.storage.chunk import DataChunk
from duckpy.storage.dict_vector import DictionaryVector
from duckpy.storage.rle_vector import RLEVector


def test_chunk_with_dictionary_and_rle_vectors():
    schema = Schema([
        ColumnDefinition("user_id", DuckType.INT64),
        ColumnDefinition("department", DuckType.STRING),
        ColumnDefinition("status", DuckType.STRING),
    ])

    chunk = DataChunk(schema, capacity=5)

    # Make compressed column for department
    dict_vec = DictionaryVector(capacity=5)
    dict_vec.append("Engineering")
    dict_vec.append("Engineering")
    dict_vec.append("HR")

    # Make compressed RLE column for status
    rle_vec = RLEVector(dtype=DuckType.STRING, capacity=5)
    rle_vec.append("ACTIVE")
    rle_vec.append("ACTIVE")
    rle_vec.append("INACTIVE")

    # Regular vector for user_id
    id_vec = chunk.get_vector("user_id")
    id_vec.append(101)
    id_vec.append(102)
    id_vec.append(103)

    # Plug in compressed vectors
    chunk.set_vector("department", dict_vec)
    chunk.set_vector("status", rle_vec)

    assert chunk.card == 3
    assert chunk.to_rows() == [
        [101, "Engineering", "ACTIVE"],
        [102, "Engineering", "ACTIVE"],
        [103, "HR", "INACTIVE"]
    ]