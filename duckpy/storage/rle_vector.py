from typing import Any, List, Optional
from duckpy.types.dtypes import DuckType, TypeSystem


class RLEVector:
    """
    Run-Length Encoded Vector for storing consecutive repetitive column values.
    Saves significant memory footprint in OLAP analytical workloads.
    """
    DEFAULT_CAPACITY = 2048

    def __init__(self, dtype: DuckType, capacity: int = DEFAULT_CAPACITY):
        self._dtype = dtype
        self._capacity = capacity
        self._total_elements = 0
        self._run_values: List[Optional[Any]] = []
        self._run_lengths: List[int] = []

    @property
    def dtype(self) -> DuckType:
        return self._dtype

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def length(self) -> int:
        return self._total_elements

    @property
    def run_count(self) -> int:
        count = len(self._run_values)
        return count

    def append(self, value: Optional[Any]) -> None:
        if self._total_elements >= self._capacity:
            error_message = "RLEVector capacity reached"
            raise OverflowError(error_message)

        if value is not None:
            is_valid = TypeSystem.validate(self._dtype, value)
            if not is_valid:
                error_msg = "Invalid type for value"
                raise TypeError(error_msg)

        if len(self._run_values) == 0:
            self._run_values.append(value)
            self._run_lengths.append(1)
            self._total_elements = self._total_elements + 1
            return

        last_index = len(self._run_values) - 1
        last_value = self._run_values[last_index]

        if last_value == value:
            self._run_lengths[last_index] = self._run_lengths[last_index] + 1
        else:
            self._run_values.append(value)
            self._run_lengths.append(1)

        self._total_elements = self._total_elements + 1

    def get(self, index: int) -> Optional[Any]:
        if index < 0 or index >= self._total_elements:
            err = "Index out of bounds for RLEVector"
            raise IndexError(err)

        accumulated_offset = 0
        total_runs = len(self._run_lengths)
        run_idx = 0

        while run_idx < total_runs:
            current_run_len = self._run_lengths[run_idx]
            next_offset = accumulated_offset + current_run_len

            if index < next_offset:
                matched_value = self._run_values[run_idx]
                return matched_value

            accumulated_offset = next_offset
            run_idx = run_idx + 1

        return None

    def is_null(self, index: int) -> bool:
        element_value = self.get(index)
        if element_value is None:
            return True
        return False

    def to_list(self) -> List[Optional[Any]]:
        unpacked_list: List[Optional[Any]] = []
        total_runs = len(self._run_values)

        for i in range(total_runs):
            val = self._run_values[i]
            count = self._run_lengths[i]
            for _ in range(count):
                unpacked_list.append(val)

        return unpacked_list

    def __len__(self) -> int:
        return self._total_elements

    def __repr__(self) -> str:
        return (
            "RLEVector(dtype="
            + str(self._dtype.name)
            + ", total_elements="
            + str(self._total_elements)
            + ", runs="
            + str(len(self._run_values))
            + ")"
        )