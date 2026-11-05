import os
import json
import struct
from typing import List, Dict, Any
from duckpy.types.dtypes import DuckType
from duckpy.storage.schema import Schema, ColumnDefinition
from duckpy.storage.chunk import DataChunk


class DiskStorageEngine:
    """
    Handles serializing and deserializing DataChunks and Schemas
    to/from custom portable columnar binary files on disk.
    """
    MAGIC_HEADER = b"DUCKPY1"

    @staticmethod
    def save_table(file_path: str, schema: Schema, chunks: List[DataChunk]) -> None:
        schema_meta = []
        for col in schema.columns:
            meta_item = {
                "name": col.name,
                "dtype": col.dtype.name
            }
            schema_meta.append(meta_item)

        metadata_dict = {
            "columns": schema_meta,
            "chunk_count": len(chunks)
        }

        meta_bytes = json.dumps(metadata_dict).encode("utf-8")
        meta_size = len(meta_bytes)

        with open(file_path, "wb") as f:
            # 1. Write Magic Header
            f.write(DiskStorageEngine.MAGIC_HEADER)
            # 2. Write Metadata Length (4 bytes unsigned int)
            f.write(struct.pack("<I", meta_size))
            # 3. Write JSON Metadata
            f.write(meta_bytes)

            # 4. Write Chunks row by row in binary/JSON records
            for chunk in chunks:
                chunk_rows = chunk.to_rows()
                chunk_payload = json.dumps(chunk_rows).encode("utf-8")
                payload_len = len(chunk_payload)

                f.write(struct.pack("<I", payload_len))
                f.write(chunk_payload)

    @staticmethod
    def load_table(file_path: str) -> tuple[Schema, List[DataChunk]]:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Storage file not found: {file_path}")

        with open(file_path, "rb") as f:
            magic = f.read(len(DiskStorageEngine.MAGIC_HEADER))
            if magic != DiskStorageEngine.MAGIC_HEADER:
                raise ValueError("Corrupted or invalid DuckPy binary storage file.")

            meta_size_bytes = f.read(4)
            meta_size = struct.unpack("<I", meta_size_bytes)[0]

            meta_bytes = f.read(meta_size)
            metadata_dict = json.loads(meta_bytes.decode("utf-8"))

            # Reconstruct Schema
            col_defs: List[ColumnDefinition] = []
            for item in metadata_dict["columns"]:
                dtype_enum = DuckType[item["dtype"]]
                col_defs.append(ColumnDefinition(item["name"], dtype_enum))

            schema = Schema(col_defs)
            chunk_count = metadata_dict["chunk_count"]
            reconstructed_chunks: List[DataChunk] = []

            for _ in range(chunk_count):
                payload_len_bytes = f.read(4)
                if not payload_len_bytes:
                    break
                payload_len = struct.unpack("<I", payload_len_bytes)[0]
                chunk_data_bytes = f.read(payload_len)

                rows_data = json.loads(chunk_data_bytes.decode("utf-8"))
                chunk = DataChunk(schema, capacity=max(len(rows_data), 1))
                for row in rows_data:
                    chunk.append_row(row)

                reconstructed_chunks.append(chunk)

        return schema, reconstructed_chunks