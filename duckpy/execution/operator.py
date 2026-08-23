"""
Base Physical Operator interface for Vectorized Execution Engine.
"""
from abc import ABC, abstractmethod
from typing import Optional
from duckpy.storage.chunk import DataChunk
from duckpy.storage.schema import Schema


class PhysicalOperator(ABC):
    @property
    @abstractmethod
    def schema(self) -> Schema:
        """Returns output schema of this operator."""
        pass

    @abstractmethod
    def init(self) -> None:
        """Initialize or reset operator state before execution."""
        pass

    @abstractmethod
    def execute_chunk(self) -> Optional[DataChunk]:
        """
        Pull the next DataChunk from the operator pipeline.
        Returns None when pipeline exhausted.
        """
        pass