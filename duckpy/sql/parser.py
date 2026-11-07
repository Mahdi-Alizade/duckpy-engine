import re
from typing import Dict, List, Optional
from duckpy.storage.schema import Schema
from duckpy.execution.filter import ComparisonOp
from duckpy.execution.aggregate import AggregateExpr, AggregateFunction
from duckpy.execution.order_by import OrderByExpr, OrderDirection
from duckpy.execution.logical_filter import BooleanLogicOp, FilterCondition
from duckpy.optimizer.logical_plan import (
    LogicalNode,
    LogicalScan,
    LogicalFilter,
    LogicalCompoundFilter,
    LogicalProjection,
    LogicalAggregate,
    LogicalOrderBy,
    LogicalLimit,
)


class SimpleSQLParser:
    """
    Lightweight SQL Parser that parses standard analytical queries
    supporting compound WHERE predicates (AND/OR), SELECT, GROUP BY, ORDER BY, and LIMIT.
    """
    def __init__(self, catalog_schemas: Dict[str, Schema]):
        self._schemas = dict(catalog_schemas)

    def _parse_comparison_op(self, raw_op: str) -> ComparisonOp:
        cleaned_op = raw_op.strip()
        if cleaned_op in ("=", "=="):
            return ComparisonOp.EQUAL
        elif cleaned_op in ("!=", "<>"):
            return ComparisonOp.NOT_EQUAL
        elif cleaned_op == ">":
            return ComparisonOp.GREATER_THAN
        elif cleaned_op == ">=":
            return ComparisonOp.GREATER_THAN_OR_EQUAL
        elif cleaned_op == "<":
            return ComparisonOp.LESS_THAN
        elif cleaned_op == "<=":
            return ComparisonOp.LESS_THAN_OR_EQUAL
        
        error_msg = f"Unsupported SQL comparison operator: {raw_op}"
        raise ValueError(error_msg)

    def _cast_literal(self, literal_str: str):
        val = literal_str.strip()
        if (val.startswith("'") and val.endswith("'")) or (val.startswith('"') and val.endswith('"')):
            return val[1:-1]
        if val.lower() == "true":
            return True
        elif val.lower() == "false":
            return False
        try:
            if "." in val:
                return float(val)
            return int(val)
        except ValueError:
            return val

    def _parse_single_condition(self, condition_str: str) -> FilterCondition:
        pattern = re.compile(r"([a-zA-Z0-9_]+)\s*(=|!=|<>|>=|<=|>|<)\s*(.+)")
        match = pattern.match(condition_str.strip())
        if not match:
            raise ValueError(f"Invalid predicate format: '{condition_str}'")

        col_name = match.group(1).strip()
        raw_op = match.group(2).strip()
        raw_val = match.group(3).strip()

        op = self._parse_comparison_op(raw_op)
        val = self._cast_literal(raw_val)
        return FilterCondition(col_name, op, val)

    def parse(self, sql_query: str) -> LogicalNode:
        cleaned_sql = sql_query.strip().rstrip(";")
        
        # Regex to capture SELECT, FROM, WHERE, GROUP BY, ORDER BY, LIMIT
        pattern = re.compile(
            r"SELECT\s+(?P<select>.+?)\s+FROM\s+(?P<from>[a-zA-Z0-9_]+)"
            r"(?:\s+WHERE\s+(?P<where>.+?))?"
            r"(?:\s+GROUP\s+BY\s+(?P<group_by>.+?))?"
            r"(?:\s+ORDER\s+BY\s+(?P<order_by>.+?))?"
            r"(?:\s+LIMIT\s+(?P<limit>\d+))?$",
            re.IGNORECASE
        )

        match = pattern.match(cleaned_sql)
        if not match:
            err = f"Malformed or unsupported SQL syntax: '{sql_query}'"
            raise ValueError(err)

        table_name = match.group("from").strip()
        if table_name not in self._schemas:
            raise KeyError(f"Table '{table_name}' does not exist in context catalog.")

        schema = self._schemas[table_name]
        current_node: LogicalNode = LogicalScan(table_name, schema)

        # 1. Process WHERE clause (support AND / OR compound logic)
        where_clause = match.group("where")
        if where_clause:
            where_raw = where_clause.strip()
            # Check for AND / OR delimiters
            and_parts = re.split(r"\s+AND\s+", where_raw, flags=re.IGNORECASE)
            or_parts = re.split(r"\s+OR\s+", where_raw, flags=re.IGNORECASE)

            if len(and_parts) == 2:
                left_cond = self._parse_single_condition(and_parts[0])
                right_cond = self._parse_single_condition(and_parts[1])
                current_node = LogicalCompoundFilter(
                    child=current_node,
                    left_condition=left_cond,
                    logic_op=BooleanLogicOp.AND,
                    right_condition=right_cond
                )
            elif len(or_parts) == 2:
                left_cond = self._parse_single_condition(or_parts[0])
                right_cond = self._parse_single_condition(or_parts[1])
                current_node = LogicalCompoundFilter(
                    child=current_node,
                    left_condition=left_cond,
                    logic_op=BooleanLogicOp.OR,
                    right_condition=right_cond
                )
            else:
                single_cond = self._parse_single_condition(where_raw)
                current_node = LogicalFilter(
                    child=current_node,
                    column_name=single_cond.column_name,
                    op=single_cond.op,
                    target_value=single_cond.target_value
                )

        # 2. Process SELECT & GROUP BY
        select_clause = match.group("select").strip()
        group_by_clause = match.group("group_by")
        raw_select_items = [item.strip() for item in select_clause.split(",")]

        aggregates: List[AggregateExpr] = []
        project_columns: List[str] = []
        has_aggregation = False

        agg_pattern = re.compile(r"^(COUNT|SUM|AVG|MIN|MAX)\((.+?)\)(?:\s+AS\s+([a-zA-Z0-9_]+))?$", re.IGNORECASE)

        for item in raw_select_items:
            agg_match = agg_pattern.match(item)
            if agg_match:
                has_aggregation = True
                fn_name = agg_match.group(1).upper()
                target_col = agg_match.group(2).strip()
                custom_alias = agg_match.group(3)

                func_enum = AggregateFunction[fn_name]
                alias = custom_alias if custom_alias else f"{fn_name.lower()}({target_col})"
                aggregates.append(AggregateExpr(func_enum, target_col, alias=alias))
            else:
                project_columns.append(item)

        if has_aggregation:
            group_by_cols = [c.strip() for c in group_by_clause.split(",")] if group_by_clause else project_columns
            current_node = LogicalAggregate(
                child=current_node,
                group_by_columns=group_by_cols,
                aggregates=aggregates
            )
        else:
            if select_clause != "*":
                current_node = LogicalProjection(
                    child=current_node,
                    select_columns=project_columns
                )

        # 3. Process ORDER BY clause
        order_by_clause = match.group("order_by")
        if order_by_clause:
            order_specs = []
            for spec in order_by_clause.split(","):
                parts = spec.strip().split()
                col = parts[0]
                direction = OrderDirection.DESCENDING if (len(parts) > 1 and parts[1].upper() == "DESC") else OrderDirection.ASCENDING
                order_specs.append(OrderByExpr(col, direction))
            current_node = LogicalOrderBy(current_node, order_specs)

        # 4. Process LIMIT clause
        limit_clause = match.group("limit")
        if limit_clause:
            limit_val = int(limit_clause.strip())
            current_node = LogicalLimit(current_node, limit_val)

        return current_node