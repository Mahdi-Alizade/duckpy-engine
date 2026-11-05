import pytest
from duckpy.types.dtypes import DuckType
from duckpy.storage.rle_vector import RLEVector


def test_rle_vector_compression_and_retrieval():
    vec = RLEVector(dtype=DuckType.STRING, capacity=20)

    # Append repetitive items
    for _ in range(5):
        vec.append("ACTIVE")

    for _ in range(3):
        vec.append("PENDING")

    vec.append(None)
    vec.append(None)

    assert len(vec) == 10
    assert vec.run_count == 3

    assert vec.get(0) == "ACTIVE"
    assert vec.get(4) == "ACTIVE"
    assert vec.get(5) == "PENDING"
    assert vec.get(7) == "PENDING"
    assert vec.get(8) is None
    assert vec.is_null(8) is True
    assert vec.is_null(9) is True


def test_rle_vector_to_list():
    vec = RLEVector(dtype=DuckType.INT64, capacity=6)
    vec.append(42)
    vec.append(42)
    vec.append(100)

    unpacked = vec.to_list()
    assert unpacked == [42, 42, 100]


def test_rle_vector_type_validation():
    vec = RLEVector(dtype=DuckType.INT64, capacity=5)
    with pytest.raises(TypeError):
        vec.append("invalid_string_type")


def test_rle_vector_overflow():
    vec = RLEVector(dtype=DuckType.BOOLEAN, capacity=2)
    vec.append(True)
    vec.append(False)
    with pytest.raises(OverflowError):
        vec.append(True)