"""
DataFrame API providing lazy evaluation and fluent query construction.
"""
from typing import Any, Dict, List, Optional, Sequence
from duckpy.types.dtypes import DuckType
from duckpy.storage.chunk import DataChunk
from duckpy.storage.schema import Schema
from duckpy.execution.filter import ComparisonOp
from duckpy.execution.aggregate import AggregateExpr, AggregateFunction
from duckpy.optimizer.logical_plan import (
    LogicalNode,
    LogicalFilter,
    LogicalProjection,
    LogicalAggregate,
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

    def aggregate(
        self,
        group_by: Sequence[str],
        aggregates: Sequence[AggregateExpr]
    ) -> "DataFrame":
        new_plan = LogicalAggregate(self._logical_plan, list(group_by), list(aggregates))
        return DataFrame(new_plan, self._catalog)

    def execute(self) -> List[DataChunk]:
        """
        Runs RBO optimization, compiles to Physical Pipeline, and executes.
        """
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
        """
        Executes and returns results as list of dictionary records.
        """
        chunks = self.execute()
        records: List[Dict[str, Any]] = []
        for chunk in chunks:
            cols = [chunk.schema.get_column(i).name for i in range(chunk.column_count)]
            for row in chunk.to_rows():
                records.append(dict(zip(cols, row)))
        return records

    def show(self) -> None:
        """
        Pretty prints the query results to terminal.
        """
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