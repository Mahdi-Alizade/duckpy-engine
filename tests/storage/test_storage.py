import pytest
from duckpy.types.dtypes import DuckType
from duckpy.storage.bitmap import BitMap
from duckpy.storage.vector import Vector


def test_bitmap_operations():
    bm = BitMap(size=10, initial_value=False)
    assert bm.size == 10
    assert bm.count_trues() == 0

    bm.set(0, True)
    bm.set(9, True)
    assert bm.get(0) is True
    assert bm.get(9) is True
    assert bm.get(1) is False
    assert bm.count_trues() == 2

    bm.set(0, False)
    assert bm.get(0) is False
    assert bm.count_trues() == 1


def test_vector_append_and_nulls():
    vec = Vector(dtype=DuckType.INT64, capacity=5)
    vec.append(100)
    vec.append(None)
    vec.append(300)

    assert len(vec) == 3
    assert vec.get(0) == 100
    assert vec.get(1) is None
    assert vec.is_null(1) is True
    assert vec.get(2) == 300

    with pytest.raises(TypeError):
        vec.append("invalid_string_in_int_vector")


def test_vector_overflow():
    vec = Vector(dtype=DuckType.STRING, capacity=2)
    vec.append("A")
    vec.append("B")
    
    with pytest.raises(OverflowError):
        vec.append("C")


def test_vector_from_list():
    raw_data = [1.5, None, 3.14, 0.0]
    vec = Vector.from_list(raw_data, dtype=DuckType.FLOAT64)
    assert len(vec) == 4
    assert vec.to_list() == raw_data