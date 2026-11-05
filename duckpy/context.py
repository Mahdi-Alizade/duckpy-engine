from typing import Any, Dict, List, Optional
from duckpy.types.dtypes import DuckType
from duckpy.storage.schema import Schema, ColumnDefinition
from duckpy.storage.chunk import DataChunk
from duckpy.dataframe import DataFrame
from duckpy.optimizer.logical_plan import LogicalScan
from duckpy.sql.parser import SimpleSQLParser
from duckpy.persistence.storage_engine import DiskStorageEngine


class DuckPyContext:
    """
    DuckPy Database Engine Session Context managing registered tables,
    schemas, direct SQL execution, and binary disk persistence.
    """
    def __init__(self):
        self._catalog: Dict[str, List[DataChunk]] = {}
        self._schemas: Dict[str, Schema] = {}

    def register_table(self, name: str, schema: Schema, chunks: List[DataChunk]) -> None:
        if name in self._catalog:
            raise ValueError(f"Table '{name}' is already registered.")
        self._catalog[name] = list(chunks)
        self._schemas[name] = schema

    def create_table_from_rows(
        self,
        name: str,
        columns: List[tuple[str, DuckType]],
        rows: List[List[Any]],
        chunk_size: int = 2048
    ) -> DataFrame:
        col_defs = [ColumnDefinition(c_name, c_type) for c_name, c_type in columns]
        schema = Schema(col_defs)

        chunks: List[DataChunk] = []
        current_chunk = DataChunk(schema, capacity=chunk_size)

        for row in rows:
            if current_chunk.card >= chunk_size:
                chunks.append(current_chunk)
                current_chunk = DataChunk(schema, capacity=chunk_size)
            current_chunk.append_row(row)

        if current_chunk.card > 0:
            chunks.append(current_chunk)

        self.register_table(name, schema, chunks)
        return self.table(name)

    def table(self, name: str) -> DataFrame:
        if name not in self._catalog:
            raise KeyError(f"Table '{name}' not found in catalog.")
        
        schema = self._schemas[name]
        scan_plan = LogicalScan(name, schema)
        return DataFrame(scan_plan, self._catalog)

    def sql(self, query: str) -> DataFrame:
        """
        Parses and executes an SQL query, returning a lazy DataFrame.
        """
        parser = SimpleSQLParser(self._schemas)
        logical_plan = parser.parse(query)
        return DataFrame(logical_plan, self._catalog)

    def save_table_to_disk(self, table_name: str, file_path: str) -> None:
        """
        Persists a table from in-memory catalog to disk in DuckPy binary format.
        """
        if table_name not in self._catalog:
            raise KeyError(f"Table '{table_name}' does not exist.")
        
        schema = self._schemas[table_name]
        chunks = self._catalog[table_name]
        DiskStorageEngine.save_table(file_path, schema, chunks)

    def load_table_from_disk(self, table_name: str, file_path: str) -> DataFrame:
        """
        Loads a persisted binary table file into memory and registers it.
        """
        schema, chunks = DiskStorageEngine.load_table(file_path)
        self.register_table(table_name, schema, chunks)
        return self.table(table_name)