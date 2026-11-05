import os
import tempfile
from duckpy.types.dtypes import DuckType
from duckpy.context import DuckPyContext


def test_save_and_load_table_persistence():
    ctx = DuckPyContext()

    data = [
        [1, "Alice", 120000.0],
        [2, "Bob", 95000.0],
        [3, "Charlie", 110000.0],
    ]
    cols = [
        ("id", DuckType.INT64),
        ("name", DuckType.STRING),
        ("salary", DuckType.FLOAT64),
    ]

    ctx.create_table_from_rows("staff", cols, data, chunk_size=2)

    with tempfile.NamedTemporaryFile(suffix=".duck", delete=False) as tmp_file:
        tmp_path = tmp_file.name

    try:
        # Save to disk
        ctx.save_table_to_disk("staff", tmp_path)
        assert os.path.exists(tmp_path)
        assert os.path.getsize(tmp_path) > 0

        # Load into a fresh context
        new_ctx = DuckPyContext()
        df = new_ctx.load_table_from_disk("loaded_staff", tmp_path)
        loaded_rows = df.to_dict()

        assert len(loaded_rows) == 3
        assert loaded_rows[0] == {"id": 1, "name": "Alice", "salary": 120000.0}
        assert loaded_rows[1] == {"id": 2, "name": "Bob", "salary": 95000.0}
        assert loaded_rows[2] == {"id": 3, "name": "Charlie", "salary": 110000.0}

        # Check executing SQL over loaded table
        sql_res = new_ctx.sql("SELECT name FROM loaded_staff WHERE salary > 100000.0;").to_dict()
        assert len(sql_res) == 2
        assert sql_res[0]["name"] == "Alice"
        assert sql_res[1]["name"] == "Charlie"

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)