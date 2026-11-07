"""
DataFrame API providing lazy evaluation and fluent query construction.
"""
from typing import Any, Dict, List, Optional, Sequence, Union
from duckpy.types.dtypes import DuckType
from duckpy.storage.chunk import DataChunk
from duckpy.storage.schema import Schema
from duckpy.execution.filter import ComparisonOp
from duckpy.execution.aggregate import AggregateExpr, AggregateFunction
from duckpy.execution.expressions import Expression
from duckpy.execution.order_by import OrderByExpr, OrderDirection
from duckpy.optimizer.logical_plan import (
    LogicalNode,
    LogicalFilter,
    LogicalProjection,
    LogicalAggregate,
    LogicalWithColumn,
    LogicalOrderBy,
    LogicalLimit,
)
from duckpy.optimizer.optimizer import Optimizer


class DataFrame:
    def __init__(
        self,
        logical_plan: LogicalNode,
        catalog: Dict[str, List[DataChunk]]
    ):
        self._logical_plan = logical_plan
        self._catalog = catalog

    @property
    def schema(self) -> Schema:
        return self._logical_plan.schema

    def filter(self, column: str, op: ComparisonOp, value: Any) -> "DataFrame":
        new_plan = LogicalFilter(self._logical_plan, column, op, value)
        return DataFrame(new_plan, self._catalog)

    def select(self, *columns: str) -> "DataFrame":
        new_plan = LogicalProjection(self._logical_plan, list(columns))
        return DataFrame(new_plan, self._catalog)

    def with_column(
        self,
        column_name: str,
        expression: Expression,
        dtype: DuckType = DuckType.FLOAT64
    ) -> "DataFrame":
        new_plan = LogicalWithColumn(self._logical_plan, column_name, expression, dtype)
        return DataFrame(new_plan, self._catalog)

    def order_by(
        self,
        column_name: str,
        ascending: bool = True
    ) -> "DataFrame":
        direction = OrderDirection.ASCENDING if ascending else OrderDirection.DESCENDING
        expr = OrderByExpr(column_name, direction)
        new_plan = LogicalOrderBy(self._logical_plan, [expr])
        return DataFrame(new_plan, self._catalog)

    def limit(self, count: int) -> "DataFrame":
        new_plan = LogicalLimit(self._logical_plan, count)
        return DataFrame(new_plan, self._catalog)

    def aggregate(
        self,
        group_by: Sequence[str],
        aggregates: Sequence[AggregateExpr]
    ) -> "DataFrame":
        new_plan = LogicalAggregate(self._logical_plan, list(group_by), list(aggregates))
        return DataFrame(new_plan, self._catalog)

    def execute(self) -> List[DataChunk]:
        optimized_plan = Optimizer.pushdown_predicates(self._logical_plan)
        physical_pipeline = Optimizer.to_physical(optimized_plan, self._catalog)
        physical_pipeline.init()

        chunks: List[DataChunk] = []
        while True:
            chunk = physical_pipeline.execute_chunk()
            if chunk is None:
                break
            chunks.append(chunk)
        return chunks

    def to_dict(self) -> List[Dict[str, Any]]:
        chunks = self.execute()
        records: List[Dict[str, Any]] = []
        for chunk in chunks:
            cols = [chunk.schema.get_column(i).name for i in range(chunk.column_count)]
            for row in chunk.to_rows():
                records.append(dict(zip(cols, row)))
        return records

    def show(self) -> None:
        records = self.to_dict()
        if not records:
            print("Empty result.")
            return

        headers = list(records[0].keys())
        col_widths = {h: len(h) for h in headers}

        for r in records:
            for h in headers:
                col_widths[h] = max(col_widths[h], len(str(r[h])))

        header_str = " | ".join(h.ljust(col_widths[h]) for h in headers)
        divider = "-+-".join("-" * col_widths[h] for h in headers)
        print(header_str)
        print(divider)
        for r in records:
            print(" | ".join(str(r[h]).ljust(col_widths[h]) for h in headers))