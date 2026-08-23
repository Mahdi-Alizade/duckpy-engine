"""
Logical Plan nodes representing the abstract relational algebra tree.
"""
from abc import ABC, abstractmethod
from typing import Any, List, Optional
from duckpy.storage.schema import Schema, ColumnDefinition
from duckpy.execution.filter import ComparisonOp
from duckpy.execution.aggregate import AggregateExpr, AggregateFunction
from duckpy.types.dtypes import DuckType


class LogicalNode(ABC):
    @property
    @abstractmethod
    def schema(self) -> Schema:
        pass

    @property
    @abstractmethod
    def children(self) -> List["LogicalNode"]:
        pass


class LogicalScan(LogicalNode):
    def __init__(self, table_name: str, schema: Schema):
        self.table_name = table_name
        self._schema = schema

    @property
    def schema(self) -> Schema:
        return self._schema

    @property
    def children(self) -> List[LogicalNode]:
        return []

    def __repr__(self) -> str:
        return f"LogicalScan(table='{self.table_name}', cols={self._schema.column_count})"


class LogicalFilter(LogicalNode):
    def __init__(
        self,
        child: LogicalNode,
        column_name: str,
        op: ComparisonOp,
        target_value: Any
    ):
        self.child = child
        self.column_name = column_name
        self.op = op
        self.target_value = target_value

    @property
    def schema(self) -> Schema:
        return self.child.schema

    @property
    def children(self) -> List[LogicalNode]:
        return [self.child]

    def __repr__(self) -> str:
        return f"LogicalFilter({self.column_name} {self.op.name} {self.target_value})"


class LogicalProjection(LogicalNode):
    def __init__(self, child: LogicalNode, select_columns: List[str]):
        self.child = child
        self.select_columns = list(select_columns)
        
        output_cols = [self.child.schema.get_column(col) for col in self.select_columns]
        self._schema = Schema(output_cols)

    @property
    def schema(self) -> Schema:
        return self._schema

    @property
    def children(self) -> List[LogicalNode]:
        return [self.child]

    def __repr__(self) -> str:
        return f"LogicalProjection(cols={self.select_columns})"


class LogicalAggregate(LogicalNode):
    def __init__(
        self,
        child: LogicalNode,
        group_by_columns: List[str],
        aggregates: List[AggregateExpr]
    ):
        self.child = child
        self.group_by_columns = list(group_by_columns)
        self.aggregates = list(aggregates)

        output_cols = [self.child.schema.get_column(col) for col in self.group_by_columns]
        for agg in self.aggregates:
            if agg.func == AggregateFunction.COUNT:
                dtype = DuckType.INT64
            elif agg.func in (AggregateFunction.SUM, AggregateFunction.AVG):
                dtype = DuckType.FLOAT64
            else:
                dtype = self.child.schema.get_column(agg.column_name).dtype
            output_cols.append(ColumnDefinition(agg.alias, dtype))

        self._schema = Schema(output_cols)

    @property
    def schema(self) -> Schema:
        return self._schema

    @property
    def children(self) -> List[LogicalNode]:
        return [self.child]

    def __repr__(self) -> str:
        return f"LogicalAggregate(groups={self.group_by_columns}, aggs={[a.alias for a in self.aggregates]})"