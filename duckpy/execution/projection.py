"""
Physical Projection Operator for Column Pruning and Selection.
"""
from typing import List, Optional
from duckpy.execution.operator import PhysicalOperator
from duckpy.storage.chunk import DataChunk
from duckpy.storage.schema import Schema, ColumnDefinition


class PhysicalProjection(PhysicalOperator):
    def __init__(self, child: PhysicalOperator, select_columns: List[str]):
        self._child = child
        self._select_columns = list(select_columns)
        
        # Validate projection columns exist in child schema
        child_schema = self._child.schema
        output_cols: List[ColumnDefinition] = []
        for col_name in self._select_columns:
            output_cols.append(child_schema.get_column(col_name))
        
        self._schema = Schema(output_cols)

    @property
    def schema(self) -> Schema:
        return self._schema

    def init(self) -> None:
        self._child.init()

    def execute_chunk(self) -> Optional[DataChunk]:
        chunk = self._child.execute_chunk()
        if chunk is None:
            return None

        projected_chunk = DataChunk(self._schema, capacity=chunk.card)
        for r_idx in range(chunk.card):
            row_vals = [chunk.get_vector(col_name).get(r_idx) for col_name in self._select_columns]
            projected_chunk.append_row(row_vals)

        return projected_chunk