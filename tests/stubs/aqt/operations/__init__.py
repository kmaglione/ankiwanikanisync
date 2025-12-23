from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, ClassVar, Self
from unittest.mock import MagicMock

from anki.collection import Collection

from ankiwanikanisync.promise import Promise

from .. import mw

executor = ThreadPoolExecutor(max_workers=10)


class Op[T]:
    pending_ops: ClassVar[set[Promise]] = set()

    _on_success: Callable[[T], None] | None = None
    _on_failure: Callable[[Any], None] | None = None

    def __init__(self, callback: Callable[[Collection], T]):
        self.callback = callback

    @Promise.wrap
    async def _do_run_in_background(self):
        try:
            assert mw.col
            future = executor.submit(self.callback, mw.col)
            result = await asyncio.wrap_future(future)
        except Exception as e:
            if self._on_failure:
                self._on_failure(e)
                return
            raise
        if self._on_success:
            self._on_success(result)

    def run_in_background(self) -> None:
        mw.taskman.add_pending_op(
            self._do_run_in_background().catch(Promise.report_error)
        )

    def success(self, callback: Callable[[T], None]) -> Self:
        self._on_success = callback
        return self

    def failure(self, callback: Callable[[Any], None]) -> Self:
        self._on_failure = callback
        return self


class CollectionOp[T](Op[T]):
    def __init__(self, parent: Any, op: Callable[[Collection], T]):
        super().__init__(op)


class QueryOp[T](Op[T]):
    def __init__(
        self,
        *,
        parent: Any,
        op: Callable[[Collection], T],
        success: Callable[[T], None],
    ):
        super().__init__(op)
        self.success(success)

    def without_collection(self) -> Self:
        return self

    def with_progress(self) -> Self:
        return self


ResultWithChanges = MagicMock()
