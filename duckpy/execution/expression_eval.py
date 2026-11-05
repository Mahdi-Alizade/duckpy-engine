from typing import Optional
from duckpy.execution.operator import PhysicalOperator
from duckpy.execution.expressions import Expression
from duckpy.storage.chunk import DataChunk
from duckpy.storage.schema import Schema, ColumnDefinition
from duckpy.types.dtypes import DuckType


class PhysicalExpressionEval(PhysicalOperator):
    """
    Physical operator that evaluates an Expression tree on incoming DataChunks
    and appends the resulting Vector as a new computed column.
    """
    def __init__(
        self,
        child: PhysicalOperator,
        expression: Expression,
        result_column_name: str,
        result_dtype: DuckType = DuckType.FLOAT64
    ):
        self._child = child
        self._expression = expression
        self._result_column_name = result_column_name
        self._result_dtype = result_dtype

        # Construct expanded output schema
        existing_columns = list(self._child.schema.columns)
        new_column = ColumnDefinition(self._result_column_name, self._result_dtype)
        existing_columns.append(new_column)
        self._schema = Schema(existing_columns)

    @property
    def schema(self) -> Schema:
        return self._schema

    def init(self) -> None:
        self._child.init()

    def execute_chunk(self) -> Optional[DataChunk]:
        input_chunk = self._child.execute_chunk()
        if input_chunk is None:
            return None

        # Evaluate expression vector over input chunk
        evaluated_vector = self._expression.evaluate(input_chunk)

        # Build output chunk containing all previous columns + new vector
        cardinality = input_chunk.card
        output_chunk = DataChunk(self._schema, capacity=input_chunk.capacity)

        total_cols = input_chunk.column_count
        for row_idx in range(cardinality):
            row_data = []
            for col_idx in range(total_cols):
                val = input_chunk.get_vector(col_idx).get(row_idx)
                row_data.append(val)

            # Append the newly evaluated expression value
            new_val = evaluated_vector.get(row_idx)
            row_data.append(new_val)

            output_chunk.append_row(row_data)

        return output_chunk