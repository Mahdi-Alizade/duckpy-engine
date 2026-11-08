from enum import Enum, auto
from typing import Any, Dict, List, Optional
from duckpy.execution.operator import PhysicalOperator
from duckpy.storage.chunk import DataChunk
from duckpy.storage.schema import Schema, ColumnDefinition


class JoinType(Enum):
    INNER = auto()
    LEFT = auto()


class PhysicalHashJoin(PhysicalOperator):
    """
    Vectorized in-memory Hash Join operator supporting INNER and LEFT joins
    between two relational pipelines using Build and Probe phases.
    """
    def __init__(
        self,
        left_child: PhysicalOperator,
        right_child: PhysicalOperator,
        left_on: str,
        right_on: str,
        join_type: JoinType = JoinType.INNER
    ):
        self._left_child = left_child
        self._right_child = right_child
        self._left_on = left_on
        self._right_on = right_on
        self._join_type = join_type

        # Construct unified output schema with duplicate column name protection
        merged_cols: List[ColumnDefinition] = []
        left_col_names = set()

        for col in self._left_child.schema.columns:
            merged_cols.append(col)
            left_col_names.add(col.name)

        for col in self._right_child.schema.columns:
            final_name = col.name
            if final_name in left_col_names:
                final_name = f"right_{col.name}"
            merged_cols.append(ColumnDefinition(final_name, col.dtype))

        self._schema = Schema(merged_cols)

        # Hash table holding build-side rows
        self._hash_table: Dict[Any, List[List[Any]]] = {}
        self._has_built = False

    @property
    def schema(self) -> Schema:
        return self._schema

    def init(self) -> None:
        self._left_child.init()
        self._right_child.init()
        self._hash_table.clear()
        self._has_built = False

    def _build_hash_table(self) -> None:
        right_key_idx = self._right_child.schema.get_column_index(self._right_on)

        while True:
            chunk = self._right_child.execute_chunk()
            if chunk is None:
                break

            cardinality = chunk.card
            for row_idx in range(cardinality):
                key_val = chunk.get_vector(right_key_idx).get(row_idx)

                # Standard SQL: NULL values never match in equi-joins
                if key_val is None:
                    continue

                row_data = [chunk.get_vector(c).get(row_idx) for c in range(chunk.column_count)]

                if key_val not in self._hash_table:
                    self._hash_table[key_val] = []
                self._hash_table[key_val].append(row_data)

        self._has_built = True

    def execute_chunk(self) -> Optional[DataChunk]:
        if not self._has_built:
            self._build_hash_table()

        left_key_idx = self._left_child.schema.get_column_index(self._left_on)
        right_col_count = self._right_child.schema.column_count

        while True:
            probe_chunk = self._left_child.execute_chunk()
            if probe_chunk is None:
                return None

            probe_cardinality = probe_chunk.card
            if probe_cardinality == 0:
                continue

            joined_rows: List[List[Any]] = []

            for row_idx in range(probe_cardinality):
                left_key_val = probe_chunk.get_vector(left_key_idx).get(row_idx)
                left_row_data = [probe_chunk.get_vector(c).get(row_idx) for c in range(probe_chunk.column_count)]

                if left_key_val is not None and left_key_val in self._hash_table:
                    matching_right_rows = self._hash_table[left_key_val]
                    for right_row in matching_right_rows:
                        combined_row = list(left_row_data)
                        combined_row.extend(right_row)
                        joined_rows.append(combined_row)
                elif self._join_type == JoinType.LEFT:
                    combined_row = list(left_row_data)
                    null_padding = [None] * right_col_count
                    combined_row.extend(null_padding)
                    joined_rows.append(combined_row)

            if len(joined_rows) == 0:
                continue

            output_chunk = DataChunk(self._schema, capacity=len(joined_rows))
            for row in joined_rows:
                output_chunk.append_row(row)

            return output_chunk