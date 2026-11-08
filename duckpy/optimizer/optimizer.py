"""
Rule-Based Optimizer (RBO) implementing Predicate Pushdown and Physical Pipeline compilation.
"""
from typing import Dict, List
from duckpy.storage.chunk import DataChunk
from duckpy.storage.schema import Schema
from duckpy.optimizer.logical_plan import (
    LogicalNode,
    LogicalScan,
    LogicalFilter,
    LogicalCompoundFilter,
    LogicalProjection,
    LogicalAggregate,
    LogicalHaving,
    LogicalWithColumn,
    LogicalOrderBy,
    LogicalLimit,
    LogicalWindow,
)
from duckpy.execution.operator import PhysicalOperator
from duckpy.execution.scan import PhysicalScan
from duckpy.execution.filter import VectorizedFilter
from duckpy.execution.logical_filter import VectorizedLogicalFilter
from duckpy.execution.projection import PhysicalProjection
from duckpy.execution.aggregate import PhysicalHashAggregate
from duckpy.execution.having import PhysicalHaving
from duckpy.execution.window import PhysicalWindow
from duckpy.execution.expression_eval import PhysicalExpressionEval
from duckpy.execution.order_by import PhysicalOrderBy
from duckpy.execution.limit import PhysicalLimit


class Optimizer:
    @staticmethod
    def pushdown_predicates(root: LogicalNode) -> LogicalNode:
        """
        Pushes single and compound filter nodes down the logical tree.
        """
        if isinstance(root, LogicalProjection) and isinstance(root.child, LogicalFilter):
            filter_node = root.child
            new_child = Optimizer.pushdown_predicates(filter_node.child)
            new_filter = LogicalFilter(
                new_child,
                filter_node.column_name,
                filter_node.op,
                filter_node.target_value
            )
            return LogicalProjection(new_filter, root.select_columns)

        if isinstance(root, (LogicalProjection, LogicalFilter, LogicalCompoundFilter, LogicalAggregate, LogicalHaving, LogicalWithColumn, LogicalOrderBy, LogicalLimit, LogicalWindow)):
            optimized_child = Optimizer.pushdown_predicates(root.children[0])
            if isinstance(root, LogicalProjection):
                return LogicalProjection(optimized_child, root.select_columns)
            elif isinstance(root, LogicalFilter):
                return LogicalFilter(
                    optimized_child,
                    root.column_name,
                    root.op,
                    root.target_value
                )
            elif isinstance(root, LogicalCompoundFilter):
                return LogicalCompoundFilter(
                    optimized_child,
                    root.left_condition,
                    root.logic_op,
                    root.right_condition
                )
            elif isinstance(root, LogicalAggregate):
                return LogicalAggregate(
                    optimized_child,
                    root.group_by_columns,
                    root.aggregates
                )
            elif isinstance(root, LogicalHaving):
                return LogicalHaving(
                    optimized_child,
                    root.target_column,
                    root.op,
                    root.threshold_value
                )
            elif isinstance(root, LogicalWithColumn):
                return LogicalWithColumn(
                    optimized_child,
                    root.column_name,
                    root.expression,
                    root.dtype
                )
            elif isinstance(root, LogicalOrderBy):
                return LogicalOrderBy(
                    optimized_child,
                    root.order_by_expressions
                )
            elif isinstance(root, LogicalLimit):
                return LogicalLimit(
                    optimized_child,
                    root.limit_count
                )
            elif isinstance(root, LogicalWindow):
                return LogicalWindow(
                    optimized_child,
                    root.window_spec
                )

        return root

    @staticmethod
    def to_physical(
        root: LogicalNode,
        tables_catalog: Dict[str, List[DataChunk]]
    ) -> PhysicalOperator:
        """
        Compiles the Logical Plan into an executable Physical Pipeline.
        """
        if isinstance(root, LogicalScan):
            chunks = tables_catalog.get(root.table_name, [])
            return PhysicalScan(root.schema, chunks)

        elif isinstance(root, LogicalFilter):
            child_phys = Optimizer.to_physical(root.child, tables_catalog)
            return VectorizedFilter(
                child_phys,
                root.column_name,
                root.op,
                root.target_value
            )

        elif isinstance(root, LogicalCompoundFilter):
            child_phys = Optimizer.to_physical(root.child, tables_catalog)
            return VectorizedLogicalFilter(
                child_phys,
                root.left_condition,
                root.logic_op,
                root.right_condition
            )

        elif isinstance(root, LogicalProjection):
            child_phys = Optimizer.to_physical(root.child, tables_catalog)
            return PhysicalProjection(child_phys, root.select_columns)

        elif isinstance(root, LogicalAggregate):
            child_phys = Optimizer.to_physical(root.child, tables_catalog)
            return PhysicalHashAggregate(
                child_phys,
                root.group_by_columns,
                root.aggregates
            )

        elif isinstance(root, LogicalHaving):
            child_phys = Optimizer.to_physical(root.child, tables_catalog)
            return PhysicalHaving(
                child_phys,
                root.target_column,
                root.op,
                root.threshold_value
            )

        elif isinstance(root, LogicalWindow):
            child_phys = Optimizer.to_physical(root.child, tables_catalog)
            return PhysicalWindow(child_phys, root.window_spec)

        elif isinstance(root, LogicalWithColumn):
            child_phys = Optimizer.to_physical(root.child, tables_catalog)
            return PhysicalExpressionEval(
                child_phys,
                root.expression,
                root.column_name,
                root.dtype
            )

        elif isinstance(root, LogicalOrderBy):
            child_phys = Optimizer.to_physical(root.child, tables_catalog)
            return PhysicalOrderBy(child_phys, root.order_by_expressions)

        elif isinstance(root, LogicalLimit):
            child_phys = Optimizer.to_physical(root.child, tables_catalog)
            return PhysicalLimit(child_phys, root.limit_count)

        raise TypeError(f"Cannot compile unsupported logical node: {type(root)}")