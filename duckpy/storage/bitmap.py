"""
Compact Null BitMap representation for Vector storage.
"""
import bytearray
from typing import List


class BitMap:
    def __init__(self, size: int, initial_value: bool = False):
        self._size = size
        num_bytes = (size + 7) // 8
        fill = 0xFF if initial_value else 0x00
        self._bytes = bytearray([fill] * num_bytes)

    @property
    def size(self) -> int:
        return self._size

    def set(self, index: int, value: bool) -> None:
        if index < 0 or index >= self._size:
            raise IndexError(f"Index {index} out of bounds for bitmap size {self._size}")
        
        byte_index = index // 8
        bit_offset = index % 8

        if value:
            self._bytes[byte_index] |= (1 << bit_offset)
        else:
            self._bytes[byte_index] &= ~(1 << bit_offset)

    def get(self, index: int) -> bool:
        if index < 0 or index >= self._size:
            raise IndexError(f"Index {index} out of bounds for bitmap size {self._size}")
        
        byte_index = index // 8
        bit_offset = index % 8
        return bool((self._bytes[byte_index] >> bit_offset) & 1)

    def to_list(self) -> List[bool]:
        return [self.get(i) for i in range(self._size)]

    def count_trues(self) -> int:
        total = 0
        for b in self._bytes:
            total += bin(b).count("1")
        # Exclude out-of-bound bits from the last byte if any
        excess_bits = (len(self._bytes) * 8) - self._size
        if excess_bits > 0:
            last_byte = self._bytes[-1]
            for bit in range(8 - excess_bits, 8):
                if (last_byte >> bit) & 1:
                    total -= 1
        return total

    def __repr__(self) -> str:
        bits = "".join("1" if self.get(i) else "0" for i in range(self._size))
        return f"BitMap(size={self._size}, bits='{bits}')"