import re
from typing import Dict, List, Optional
from duckpy.storage.schema import Schema
from duckpy.execution.filter import ComparisonOp
from duckpy.execution.aggregate import AggregateExpr, AggregateFunction
from duckpy.optimizer.logical_plan import (
    LogicalNode,
    LogicalScan,
    LogicalFilter,
    LogicalProjection,
    LogicalAggregate,
)


class SimpleSQLParser:
    """
    Lightweight SQL Parser that parses standard analytical queries
    and compiles them into a DuckPy Logical Plan tree.
    """
    def __init__(self, catalog_schemas: Dict[str, Schema]):
        self._schemas = dict(catalog_schemas)

    def _parse_comparison_op(self, raw_op: str) -> ComparisonOp:
        cleaned_op = raw_op.strip()
        if cleaned_op == "=" or cleaned_op == "==":
            return ComparisonOp.EQUAL
        elif cleaned_op == "!=" or cleaned_op == "<>":
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
        # Handle string literals
        if (val.startswith("'") and val.endswith("'")) or (val.startswith('"') and val.endswith('"')):
            return val[1:-1]
        # Handle boolean
        if val.lower() == "true":
            return True
        elif val.lower() == "false":
            return False
        # Handle numbers
        try:
            if "." in val:
                return float(val)
            return int(val)
        except ValueError:
            return val

    def parse(self, sql_query: str) -> LogicalNode:
        cleaned_sql = sql_query.strip().rstrip(";")
        
        # Regex to capture SELECT, FROM, optional WHERE, optional GROUP BY
        pattern = re.compile(
            r"SELECT\s+(?P<select>.+?)\s+FROM\s+(?P<from>[a-zA-Z0-9_]+)"
            r"(?:\s+WHERE\s+(?P<where>.+?))?"
            r"(?:\s+GROUP\s+BY\s+(?P<group_by>.+?))?$",
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

        # 1. Process WHERE clause
        where_clause = match.group("where")
        if where_clause:
            where_pattern = re.compile(
                r"([a-zA-Z0-9_]+)\s*(=|!=|<>|>=|<=|>|<)\s*(.+)"
            )
            where_match = where_pattern.match(where_clause.strip())
            if not where_match:
                raise ValueError(f"Invalid WHERE predicate format: '{where_clause}'")

            filter_col = where_match.group(1).strip()
            raw_operator = where_match.group(2).strip()
            raw_val = where_match.group(3).strip()

            op = self._parse_comparison_op(raw_operator)
            target_value = self._cast_literal(raw_val)

            current_node = LogicalFilter(
                child=current_node,
                column_name=filter_col,
                op=op,
                target_value=target_value
            )

        # 2. Process SELECT & GROUP BY expressions
        select_clause = match.group("select").strip()
        group_by_clause = match.group("group_by")

        raw_select_items = [item.strip() for item in select_clause.split(",")]

        # Check if aggregates exist in select items
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
            group_by_cols: List[str] = []
            if group_by_clause:
                group_by_cols = [c.strip() for c in group_by_clause.split(",")]
            else:
                group_by_cols = project_columns

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

        return current_node