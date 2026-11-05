from concurrent.futures import ThreadPoolExecutor
from typing import Callable, List, Optional
from duckpy.execution.operator import PhysicalOperator
from duckpy.storage.chunk import DataChunk
from duckpy.storage.schema import Schema


class ParallelScan(PhysicalOperator):
    """
    Morsel-driven parallel scan operator processing DataChunks concurrently
    across a worker thread pool.
    """
    def __init__(
        self,
        schema: Schema,
        chunks: List[DataChunk],
        max_workers: int = 4,
        transform_fn: Optional[Callable[[DataChunk], Optional[DataChunk]]] = None
    ):
        self._schema = schema
        self._raw_chunks = list(chunks)
        self._max_workers = max_workers
        self._transform_fn = transform_fn
        
        self._result_queue: List[DataChunk] = []
        self._current_index = 0
        self._has_executed = False

    @property
    def schema(self) -> Schema:
        return self._schema

    def init(self) -> None:
        self._result_queue.clear()
        self._current_index = 0
        self._has_executed = False

    def _process_single_chunk(self, chunk: DataChunk) -> Optional[DataChunk]:
        if self._transform_fn is None:
            return chunk
        transformed = self._transform_fn(chunk)
        return transformed

    def _run_parallel_pipeline(self) -> None:
        total_chunks = len(self._raw_chunks)
        if total_chunks == 0:
            self._has_executed = True
            return

        effective_workers = min(self._max_workers, total_chunks)
        
        with ThreadPoolExecutor(max_workers=effective_workers) as executor:
            future_results = list(executor.map(self._process_single_chunk, self._raw_chunks))

        for chunk_res in future_results:
            if chunk_res is not None and chunk_res.card > 0:
                self._result_queue.append(chunk_res)

        self._has_executed = True

    def execute_chunk(self) -> Optional[DataChunk]:
        if not self._has_executed:
            self._run_parallel_pipeline()

        total_ready = len(self._result_queue)
        if self._current_index >= total_ready:
            return None

        next_chunk = self._result_queue[self._current_index]
        self._current_index = self._current_index + 1
        return next_chunk