"""
Logical Plan nodes representing the abstract relational algebra tree.
"""
from abc import ABC, abstractmethod
from typing import Any, List, Optional
from duckpy.storage.schema import Schema, ColumnDefinition
from duckpy.execution.filter import ComparisonOp
from duckpy.execution.aggregate import AggregateExpr, AggregateFunction
from duckpy.execution.expressions import Expression
from duckpy.execution.order_by import OrderByExpr
from duckpy.execution.logical_filter import BooleanLogicOp, FilterCondition
from duckpy.execution.window import WindowSpec
from duckpy.execution.hash_join import JoinType
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


class LogicalCompoundFilter(LogicalNode):
    def __init__(
        self,
        child: LogicalNode,
        left_condition: FilterCondition,
        logic_op: BooleanLogicOp,
        right_condition: FilterCondition
    ):
        self.child = child
        self.left_condition = left_condition
        self.logic_op = logic_op
        self.right_condition = right_condition

    @property
    def schema(self) -> Schema:
        return self.child.schema

    @property
    def children(self) -> List[LogicalNode]:
        return [self.child]

    def __repr__(self) -> str:
        return (
            f"LogicalCompoundFilter({self.left_condition.column_name} {self.left_condition.op.name} "
            f"{self.logic_op.name} {self.right_condition.column_name} {self.right_condition.op.name})"
        )


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


class LogicalHaving(LogicalNode):
    def __init__(
        self,
        child: LogicalNode,
        target_column: str,
        op: ComparisonOp,
        threshold_value: Any
    ):
        self.child = child
        self.target_column = target_column
        self.op = op
        self.threshold_value = threshold_value

    @property
    def schema(self) -> Schema:
        return self.child.schema

    @property
    def children(self) -> List[LogicalNode]:
        return [self.child]

    def __repr__(self) -> str:
        return f"LogicalHaving({self.target_column} {self.op.name} {self.threshold_value})"


class LogicalWithColumn(LogicalNode):
    def __init__(
        self,
        child: LogicalNode,
        column_name: str,
        expression: Expression,
        dtype: DuckType = DuckType.FLOAT64
    ):
        self.child = child
        self.column_name = column_name
        self.expression = expression
        self.dtype = dtype

        cols = list(self.child.schema.columns)
        cols.append(ColumnDefinition(column_name, dtype))
        self._schema = Schema(cols)

    @property
    def schema(self) -> Schema:
        return self._schema

    @property
    def children(self) -> List[LogicalNode]:
        return [self.child]

    def __repr__(self) -> str:
        return f"LogicalWithColumn(col='{self.column_name}', dtype={self.dtype.name})"


class LogicalOrderBy(LogicalNode):
    def __init__(self, child: LogicalNode, order_by_expressions: List[OrderByExpr]):
        self.child = child
        self.order_by_expressions = list(order_by_expressions)

    @property
    def schema(self) -> Schema:
        return self.child.schema

    @property
    def children(self) -> List[LogicalNode]:
        return [self.child]

    def __repr__(self) -> str:
        items = [f"{expr.column_name} {expr.direction.name}" for expr in self.order_by_expressions]
        return f"LogicalOrderBy({', '.join(items)})"


class LogicalLimit(LogicalNode):
    def __init__(self, child: LogicalNode, limit_count: int):
        self.child = child
        self.limit_count = limit_count

    @property
    def schema(self) -> Schema:
        return self.child.schema

    @property
    def children(self) -> List[LogicalNode]:
        return [self.child]

    def __repr__(self) -> str:
        return f"LogicalLimit({self.limit_count})"


class LogicalWindow(LogicalNode):
    def __init__(self, child: LogicalNode, window_spec: WindowSpec):
        self.child = child
        self.window_spec = window_spec

        existing_cols = list(child.schema.columns)
        window_col = ColumnDefinition(window_spec.alias, DuckType.INT64)
        existing_cols.append(window_col)
        self._schema = Schema(existing_cols)

    @property
    def schema(self) -> Schema:
        return self._schema

    @property
    def children(self) -> List[LogicalNode]:
        return [self.child]

    def __repr__(self) -> str:
        return f"LogicalWindow({self.window_spec.func_type.name} AS {self.window_spec.alias})"


class LogicalJoin(LogicalNode):
    def __init__(
        self,
        left: LogicalNode,
        right: LogicalNode,
        left_on: str,
        right_on: str,
        join_type: JoinType = JoinType.INNER
    ):
        self.left = left
        self.right = right
        self.left_on = left_on
        self.right_on = right_on
        self.join_type = join_type

        merged_cols: List[ColumnDefinition] = []
        left_col_names = set()

        for col in self.left.schema.columns:
            merged_cols.append(col)
            left_col_names.add(col.name)

        for col in self.right.schema.columns:
            final_name = col.name
            if final_name in left_col_names:
                final_name = f"right_{col.name}"
            merged_cols.append(ColumnDefinition(final_name, col.dtype))

        self._schema = Schema(merged_cols)

    @property
    def schema(self) -> Schema:
        return self._schema

    @property
    def children(self) -> List[LogicalNode]:
        return [self.left, self.right]

    def __repr__(self) -> str:
        return f"LogicalJoin({self.join_type.name} on left.{self.left_on} = right.{self.right_on})"


class LogicalUnion(LogicalNode):
    def __init__(
        self,
        left: LogicalNode,
        right: LogicalNode,
        distinct: bool = False
    ):
        if left.schema.column_count != right.schema.column_count:
            raise ValueError("LogicalUnion branches must have matching column counts.")
        self.left = left
        self.right = right
        self.distinct = distinct
        self._schema = left.schema

    @property
    def schema(self) -> Schema:
        return self._schema

    @property
    def children(self) -> List[LogicalNode]:
        return [self.left, self.right]

    def __repr__(self) -> str:
        union_kind = "UNION DISTINCT" if self.distinct else "UNION ALL"
        return f"LogicalUnion({union_kind})"