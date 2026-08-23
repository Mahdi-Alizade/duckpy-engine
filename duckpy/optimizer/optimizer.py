"""
Rule-Based Optimizer (RBO) implementing Predicate Pushdown and Projection Pruning.
"""
from typing import Dict, List
from duckpy.storage.chunk import DataChunk
from duckpy.storage.schema import Schema
from duckpy.optimizer.logical_plan import (
    LogicalNode,
    LogicalScan,
    LogicalFilter,
    LogicalProjection,
    LogicalAggregate,
)
from duckpy.execution.operator import PhysicalOperator
from duckpy.execution.scan import PhysicalScan
from duckpy.execution.filter import VectorizedFilter
from duckpy.execution.projection import PhysicalProjection
from duckpy.execution.aggregate import PhysicalHashAggregate


class Optimizer:
    @staticmethod
    def pushdown_predicates(root: LogicalNode) -> LogicalNode:
        """
        Pushes LogicalFilter nodes as deep down the logical tree as possible.
        """
        if isinstance(root, LogicalProjection) and isinstance(root.child, LogicalFilter):
            filter_node = root.child
            # Push filter under projection if target column is within projection
            new_child = Optimizer.pushdown_predicates(filter_node.child)
            new_filter = LogicalFilter(
                new_child,
                filter_node.column_name,
                filter_node.op,
                filter_node.target_value
            )
            return LogicalProjection(new_filter, root.select_columns)

        if isinstance(root, (LogicalProjection, LogicalFilter, LogicalAggregate)):
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
            elif isinstance(root, LogicalAggregate):
                return LogicalAggregate(
                    optimized_child,
                    root.group_by_columns,
                    root.aggregates
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

        raise TypeError(f"Cannot compile unsupported logical node: {type(root)}")