from enum import Enum, auto
from typing import Any, List, Optional, Set, Tuple
from duckpy.execution.operator import PhysicalOperator
from duckpy.storage.chunk import DataChunk
from duckpy.storage.schema import Schema


class SetOpType(Enum):
    INTERSECT = auto()
    EXCEPT = auto()


class PhysicalSetOperation(PhysicalOperator):
    """
    Physical operator executing relational set operations:
    - INTERSECT: rows present in both left and right relations.
    - EXCEPT: rows present in left relation but not in right relation.
    """
    def __init__(
        self,
        left_child: PhysicalOperator,
        right_child: PhysicalOperator,
        op_type: SetOpType
    ):
        self._left_child = left_child
        self._right_child = right_child
        self._op_type = op_type

        if left_child.schema.column_count != right_child.schema.column_count:
            raise ValueError("Set operations require identical column counts in both inputs.")

        self._schema = left_child.schema
        self._right_set: Set[Tuple[Any, ...]] = set()
        self._emitted_set: Set[Tuple[Any, ...]] = set()
        self._has_built_right = False

    @property
    def schema(self) -> Schema:
        return self._schema

    def init(self) -> None:
        self._left_child.init()
        self._right_child.init()
        self._right_set.clear()
        self._emitted_set.clear()
        self._has_built_right = False

    def _build_right_set(self) -> None:
        col_count = self._right_child.schema.column_count
        while True:
            chunk = self._right_child.execute_chunk()
            if chunk is None:
                break
            for r_idx in range(chunk.card):
                row_tuple = tuple(chunk.get_vector(c).get(r_idx) for c in range(col_count))
                self._right_set.add(row_tuple)
        self._has_built_right = True

    def execute_chunk(self) -> Optional[DataChunk]:
        if not self._has_built_right:
            self._build_right_set()

        col_count = self._schema.column_count

        while True:
            left_chunk = self._left_child.execute_chunk()
            if left_chunk is None:
                return None

            if left_chunk.card == 0:
                continue

            filtered_rows: List[List[Any]] = []

            for r_idx in range(left_chunk.card):
                row_vals = [left_chunk.get_vector(c).get(r_idx) for c in range(col_count)]
                row_tuple = tuple(row_vals)

                if row_tuple in self._emitted_set:
                    continue

                if self._op_type == SetOpType.INTERSECT:
                    if row_tuple in self._right_set:
                        self._emitted_set.add(row_tuple)
                        filtered_rows.append(row_vals)
                elif self._op_type == SetOpType.EXCEPT:
                    if row_tuple not in self._right_set:
                        self._emitted_set.add(row_tuple)
                        filtered_rows.append(row_vals)

            if len(filtered_rows) == 0:
                continue

            output_chunk = DataChunk(self._schema, capacity=len(filtered_rows))
            for row in filtered_rows:
                output_chunk.append_row(row)

            return output_chunk