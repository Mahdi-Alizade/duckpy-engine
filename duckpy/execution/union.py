from typing import Any, List, Optional, Set, Tuple
from duckpy.execution.operator import PhysicalOperator
from duckpy.storage.chunk import DataChunk
from duckpy.storage.schema import Schema


class PhysicalUnion(PhysicalOperator):
    """
    Physical operator executing UNION ALL (streaming concatenation)
    or UNION DISTINCT (filtering duplicate rows using hash sets).
    """
    def __init__(
        self,
        left_child: PhysicalOperator,
        right_child: PhysicalOperator,
        distinct: bool = False
    ):
        self._left_child = left_child
        self._right_child = right_child
        self._distinct = distinct

        # Validate schema column counts match
        if left_child.schema.column_count != right_child.schema.column_count:
            raise ValueError("UNION pipelines must have the exact same number of columns.")

        self._schema = left_child.schema
        self._seen_hashes: Set[Tuple[Any, ...]] = set()
        self._reading_left = True

    @property
    def schema(self) -> Schema:
        return self._schema

    def init(self) -> None:
        self._left_child.init()
        self._right_child.init()
        self._seen_hashes.clear()
        self._reading_left = True

    def execute_chunk(self) -> Optional[DataChunk]:
        while True:
            if self._reading_left:
                chunk = self._left_child.execute_chunk()
                if chunk is None:
                    self._reading_left = False
                    continue
            else:
                chunk = self._right_child.execute_chunk()
                if chunk is None:
                    return None

            if chunk.card == 0:
                continue

            # If plain UNION ALL, stream chunk directly
            if not self._distinct:
                return chunk

            # For UNION DISTINCT, deduplicate row by row
            unique_rows: List[List[Any]] = []
            col_count = chunk.column_count

            for r_idx in range(chunk.card):
                row_data = [chunk.get_vector(c).get(r_idx) for c in range(col_count)]
                row_key = tuple(row_data)

                if row_key not in self._seen_hashes:
                    self._seen_hashes.add(row_key)
                    unique_rows.append(row_data)

            if len(unique_rows) == 0:
                continue

            dedup_chunk = DataChunk(self._schema, capacity=len(unique_rows))
            for row in unique_rows:
                dedup_chunk.append_row(row)

            return dedup_chunk