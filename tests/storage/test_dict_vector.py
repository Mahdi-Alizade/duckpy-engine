import pytest
from duckpy.storage.dict_vector import DictionaryVector


def test_dictionary_vector_append_and_deduplication():
    vec = DictionaryVector(capacity=10)
    vec.append("Engineering")
    vec.append("Sales")
    vec.append("Engineering")
    vec.append(None)
    vec.append("Sales")

    assert len(vec) == 5
    assert vec.dictionary_size == 2
    assert vec.get(0) == "Engineering"
    assert vec.get(1) == "Sales"
    assert vec.get(2) == "Engineering"
    assert vec.get(3) is None
    assert vec.is_null(3) is True
    assert vec.get(4) == "Sales"


def test_dictionary_vector_type_error():
    vec = DictionaryVector(capacity=5)
    with pytest.raises(TypeError):
        vec.append(12345)