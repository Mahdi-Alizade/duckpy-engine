"""
Physical Hash Aggregate Operator supporting GROUP BY and Vectorized Aggregations (SUM, COUNT, MIN, MAX, AVG).
"""
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple
from duckpy.execution.operator import PhysicalOperator
from duckpy.storage.chunk import DataChunk
from duckpy.storage.schema import Schema, ColumnDefinition
from duckpy.types.dtypes import DuckType


class AggregateFunction(Enum):
    COUNT = auto()
    SUM = auto()
    MIN = auto()
    MAX = auto()
    AVG = auto()


class AggregateExpr:
    def __init__(self, func: AggregateFunction, column_name: str, alias: Optional[str] = None):
        self.func = func
        self.column_name = column_name
        self.alias = alias or f"{func.name.lower()}({column_name})"


class PhysicalHashAggregate(PhysicalOperator):
    def __init__(
        self,
        child: PhysicalOperator,
        group_by_columns: List[str],
        aggregates: List[AggregateExpr]
    ):
        self._child = child
        self._group_by_columns = list(group_by_columns)
        self._aggregates = list(aggregates)
        self._executed = False

        # Build output schema
        child_schema = self._child.schema
        output_cols: List[ColumnDefinition] = []

        for grp_col in self._group_by_columns:
            output_cols.append(child_schema.get_column(grp_col))

        for agg in self._aggregates:
            if agg.func == AggregateFunction.COUNT:
                dtype = DuckType.INT64
            elif agg.func in (AggregateFunction.SUM, AggregateFunction.AVG):
                dtype = DuckType.FLOAT64
            else:
                dtype = child_schema.get_column(agg.column_name).dtype
            output_cols.append(ColumnDefinition(agg.alias, dtype))

        self._schema = Schema(output_cols)

    @property
    def schema(self) -> Schema:
        return self._schema

    def init(self) -> None:
        self._child.init()
        self._executed = False

    def execute_chunk(self) -> Optional[DataChunk]:
        if self._executed:
            return None
        self._executed = True

        # Hash map: group_key -> list of aggregate accumulators
        # Accumulator formats:
        # COUNT: int
        # SUM: float
        # MIN: val
        # MAX: val
        # AVG: [sum, count]
        hash_table: Dict[Tuple[Any, ...], List[Any]] = {}

        while True:
            chunk = self._child.execute_chunk()
            if chunk is None:
                break
            if chunk.card == 0:
                continue

            for row_idx in range(chunk.card):
                group_key = tuple(
                    chunk.get_vector(col).get(row_idx) for col in self._group_by_columns
                )

                if group_key not in hash_table:
                    # Init accumulators
                    accs = []
                    for agg in self._aggregates:
                        if agg.func == AggregateFunction.COUNT:
                            accs.append(0)
                        elif agg.func == AggregateFunction.SUM:
                            accs.append(0.0)
                        elif agg.func == AggregateFunction.MIN:
                            accs.append(float("inf"))
                        elif agg.func == AggregateFunction.MAX:
                            accs.append(float("-inf"))
                        elif agg.func == AggregateFunction.AVG:
                            accs.append([0.0, 0])
                    hash_table[group_key] = accs

                accs = hash_table[group_key]
                for i, agg in enumerate(self._aggregates):
                    val = chunk.get_vector(agg.column_name).get(row_idx)
                    if val is None:
                        continue

                    if agg.func == AggregateFunction.COUNT:
                        accs[i] += 1
                    elif agg.func == AggregateFunction.SUM:
                        accs[i] += float(val)
                    elif agg.func == AggregateFunction.MIN:
                        if val < accs[i]:
                            accs[i] = val
                    elif agg.func == AggregateFunction.MAX:
                        if val > accs[i]:
                            accs[i] = val
                    elif agg.func == AggregateFunction.AVG:
                        accs[i][0] += float(val)
                        accs[i][1] += 1

        if not hash_table:
            return None

        # Build output chunk
        result_chunk = DataChunk(self._schema, capacity=max(len(hash_table), 1))
        for group_key, accs in hash_table.items():
            final_row = list(group_key)
            for i, agg in enumerate(self._aggregates):
                if agg.func == AggregateFunction.AVG:
                    total_sum, count = accs[i]
                    final_row.append(total_sum / count if count > 0 else None)
                else:
                    final_row.append(accs[i])
            result_chunk.append_row(final_row)

        return result_chunk