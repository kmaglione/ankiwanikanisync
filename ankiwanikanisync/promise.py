from __future__ import annotations

import asyncio
import contextlib
import contextvars
from collections.abc import Awaitable, Coroutine, Iterable, Sequence
from enum import Enum
from functools import partial, wraps
from typing import (
    Any,
    Callable,
    ClassVar,
    Generator,
    Literal,
    NamedTuple,
    Protocol,
    Self,
    TypeGuard,
    TypeIs,
    cast,
    overload,
    runtime_checkable,
)

__all__ = ("Promise", "PromiseLike", "PromiseOutcome", "ispromise")


class Scheduler:
    type Callback = Callable[[], None]

    class Cancellable(Protocol):
        def cancel(self) -> None: ...
        def cancelled(self) -> bool: ...

    def call_soon(self, callable: Callback, /) -> Cancellable:
        raise NotImplementedError()  # pragma: no cover


def call_soon(callback: Scheduler.Callback) -> None:
    assert Promise.scheduler
    Promise.scheduler.call_soon(callback)


type HandlerFn[T, RT] = Callable[[T], RT]
type ResFn[T: Any] = Callable[[T], None]


class PromiseHandler(NamedTuple):
    callback: HandlerFn
    resolve: ResFn
    reject: ResFn


def run_handler(handler: PromiseHandler, result: Any) -> None:
    """
    Runs the given promise handler function, and calls its related Promise
    resolution handler with its return value on success, or its rejection
    handler with the exception it raises on failure.
    """
    try:
        handler.resolve(handler.callback(result))
    except Exception as e:
        handler.reject(e)


class FutureLike[T](Protocol):
    _asyncio_future_blocking: bool

    def add_done_callback(
        self,
        callback: Callable[[Self], None],
        /,
        *,
        context: contextvars.Context | None = None,
    ) -> None: ...

    def cancel(self, msg: Any | None = ...) -> bool: ...

    def get_loop(self) -> asyncio.AbstractEventLoop: ...

    def result(self) -> T: ...


@overload
def isfuture[T](arg: FutureLike[T]) -> TypeIs[FutureLike[T]]: ...


@overload
def isfuture(arg: object) -> TypeIs[FutureLike]: ...


def isfuture(arg: Any) -> TypeIs[FutureLike]:
    """
    >>> isfuture(Promise.resolve(True))
    True

    >>> isfuture(asyncio.Future())
    True

    >>> isfuture({})
    False
    """
    return getattr(arg, "_asyncio_future_blocking", None) is not None


@runtime_checkable
class PromiseLike[T](Protocol):
    """
    A Protocol representing Promise-like objects. When used with event loops,
    causes any coroutine which yields one to pause execution until the Promise
    resolves or rejects.
    """

    @overload
    def then[RT, RU](
        self,
        on_resolve: HandlerFn[T, PromiseLike[RT] | RT],
        on_reject: HandlerFn[Any, PromiseLike[RU] | RU] | None = None,
        /,
    ) -> Promise[RT | RU]: ...

    @overload
    def then[RU](
        self,
        on_resolve: None,
        on_reject: HandlerFn[Any, PromiseLike[RU] | RU],
        /,
    ) -> Promise[T | RU]: ...

    def then[RT, RU](
        self,
        on_resolve: HandlerFn[T, PromiseLike[RT] | RT] | None,
        on_reject: HandlerFn[Any, PromiseLike[RU] | RU] | None = None,
        /,
    ) -> Promise: ...


@overload
def ispromise[T](val: Promise[T]) -> TypeGuard[Promise[T]]: ...


@overload
def ispromise[T](val: PromiseLike[T]) -> TypeGuard[PromiseLike[T]]: ...


@overload
def ispromise[T](val: FutureLike[T]) -> TypeGuard[PromiseLike[T]]: ...


@overload
def ispromise(val: object) -> TypeGuard[PromiseLike]: ...


# Note: We check for the presence of a `then` method directly rather than
# using `isinstance(val, PromiseLike)`, since the latter is notoriously
# inefficient.
def ispromise(val: Any) -> TypeGuard[PromiseLike]:
    """
    >>> ispromise(Promise.resolve(True))
    True

    >>> class Thenable:
    ...     def then(*args):
    ...         return Thenable()

    >>> ispromise(Thenable())
    True

    >>> ispromise({})
    False
    """
    return callable(getattr(val, "then", None))


class CancelledError(BaseException):
    pass


class CancellationError(Exception):
    pass


class InvalidStateError(Exception):
    pass


class Loop[T]:
    """
    Acts as an event loop for a single async function. Handles the async
    execution of Promise-like values yielded by the coroutine, and feeds the
    result or rejection values back into the coroutine.
    """

    _cancelled: bool = False
    _pending: Promise | None = None

    def __init__(self, awaitable: Awaitable[PromiseLike[T] | T], /) -> None:
        self.iter = awaitable.__await__()
        self.last_result = None

        def fn(resolve: ResFn[T], reject: ResFn):
            self.resolve = resolve
            self.reject = reject

        self.promise = Promise(fn, self.cancel)

        call_soon(self.loop)

    def cancel(self, msg: Any | None = None):
        self._cancelled = True
        if self._pending:
            with contextlib.suppress(Exception):
                self._pending.cancel(msg)

    def loop(self, result: Any = None, *, is_rejection: bool = False) -> None:
        """
        Runs the event loop until the generator either finishes or yields a
        PromiseLike or FutureLike object.

        When the generator finishes, self.promise is resolved or rejected with
        the return or exception value (respectively) of the generator.

        When the generator yields a PromiseLike or FutureLike, the loop pauses
        until it is settled, and then re-enters the loop() method and continues
        with its result (or exception) value as the next value fed to the
        generator.
        """
        while True:
            try:
                if self._cancelled:
                    result = None
                    self.iter.throw(CancelledError())
                elif is_rejection:
                    result = self.iter.throw(result)
                else:
                    result = self.iter.send(result)
                is_rejection = False
                if not ispromise(result) and isfuture(result):
                    result = Promise.wrap(result)
                if ispromise(result):
                    self._pending = result
                    result.then(self.loop, partial(self.loop, is_rejection=True))
                else:
                    self._pending = None
                    continue
            except StopIteration as e:
                self.resolve(e.value)
            except (Exception, CancelledError) as e:
                self.reject(e)
            break


# Per the JavaScript APIs, promise outcomes only have `value` attributes if
# their status is "fulfilled", and only have "reason" attributes if their
# status is "rejected". To make that API type-checker friendly, these classes
# act as tagged-unions based on their `status` attribute. Thus, the following
# will produce valid code:
#
#   def result(outcome: PromiseOutcome[T]):
#       if outcome.status == "fulfilled":
#           assert_type(outcome.value, T)
#       else:
#           assert_type(outcome.reason, Any)
class PromiseFulfilledOutcome[U]:
    status: Literal["fulfilled"] = "fulfilled"

    def __init__(self, value: U):
        self.value = value

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, PromiseFulfilledOutcome):
            return other.value == self.value
        return False


class PromiseRejectedOutcome:
    status: Literal["rejected"] = "rejected"

    def __init__(self, reason: Any):
        self.reason = reason

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, PromiseRejectedOutcome):
            return other.reason == self.reason
        return False


type PromiseOutcome[U] = PromiseFulfilledOutcome[U] | PromiseRejectedOutcome


def cast_list_some[T](vals: Sequence[None | T]) -> list[T]:
    """
    Casts a list of a `None | T` type to a list of type `T`. This is
    essentially equivalent to `cast(list[T], vals)`, except that it ensures
    that T matches the originally declared item type of the list, while a
    direct cast would allow specifying arbitrary, unrelated types.

    Does assert the values of contents, since we can't know whether NoneType
    is a valid subtype of T.
    """
    return cast(list[T], vals)


class PromiseWithResolvers[T]:
    promise: Promise[T]
    resolve: ResFn[T]
    reject: ResFn

    def __init__(self, on_cancel: Callable[[], None] | None = None):
        self.promise = Promise[T](None, on_cancel)
        self.resolve = self.promise._resolvers.resolve
        self.reject = self.promise._resolvers.reject


class PromiseResolvers[T]:
    def __init__(self, promise: Promise[T]):
        self.promise: Promise[T] | None = promise

    def resolve(self, arg: Any) -> None:
        if not self.promise:
            return
        if self.promise._status in (Status.Pending, Status.Cancelled):
            if ispromise(arg):
                arg.then(self.resolve, self.reject)
            else:
                self.promise._settle(arg, Status.Fulfilled)

    def reject(self, arg: Any) -> None:
        if not self.promise:
            return
        if self.promise._status in (Status.Pending, Status.Cancelled):
            if isinstance(arg, (CancelledError, asyncio.CancelledError)):
                # CancelledError is an instance of BaseException, but not
                # Exception. To prevent task cancellations from
                # propagating up to the top level and exiting the
                # application, which is presumably not the usual
                # intention, we convert them to CancellationErrors.
                try:
                    raise CancellationError() from arg
                except CancellationError as e:
                    arg = e
            self.promise._settle(arg, Status.Rejected)


class Promise[T](PromiseLike[T], FutureLike[T]):
    """
    A helper class which is approximately equivalent to the JavaScript Promise
    object. Runs all handlers asynchronously, at the top of the Qt application
    event loop. Also handles running async functions at the top of the event
    loop, and mapping their result to a Promise which resolves to their return
    value on completion, or rejects with their exception value on failure.

    Note that rejection values are always dynamically typed, since any
    exception raised by a handler function can be converted into a rejection
    value.
    """

    class Status(Enum):
        Pending = 0
        Fulfilled = 1
        Rejected = 2
        Cancelled = 3

    _status: Promise.Status = Status.Pending
    _result: Any = None
    _handled_rejection = False

    scheduler: ClassVar[Scheduler | None] = None

    @classmethod
    def set_scheduler(cls, scheduler: Scheduler):
        cls.scheduler = scheduler

    def __init__(
        self,
        fn: Callable[[ResFn[T], ResFn], None] | None,
        /,
        on_cancel: Callable[[], None] | None = None,
    ) -> None:
        """
        Comparable in function to the JavaScript Promise constructor.
        Immediately calls the given callable, passing callback functions which
        resolve or reject the returned promise when called.
        """

        resolvers = PromiseResolvers(self)

        self._resolve_handlers = list[PromiseHandler]()
        self._reject_handlers = list[PromiseHandler]()
        self._on_cancel = on_cancel
        self._resolvers = resolvers

        if fn:
            try:
                fn(resolvers.resolve, resolvers.reject)
            except (Exception, CancelledError) as e:
                resolvers.reject(e)

    # Awaitable interface
    def __await__(self) -> Generator[Self, T, T]:
        """
        Returns a generator which yields the promise itself, and then returns
        the next value sent to the generator. When used in an event loop, this
        will cause the loop to pause until the Promise is settled, and then
        feed the resolution or rejection value back into the coroutine that
        awaited on the Promise.
        """
        self._asyncio_future_blocking = True
        yield self
        return self.result()

    # Future interface
    _asyncio_future_blocking = False

    def get_loop(self) -> asyncio.AbstractEventLoop:
        return asyncio.get_running_loop()

    def add_done_callback(
        self,
        callback: Callable[[Self], None],
        *,
        context: contextvars.Context | None = None,
    ):
        @self.finally_
        def finally_():
            if context:
                context.run(callback, self)
            else:
                callback(self)  # pragma: no cover

        finally_.catch(Promise.report_error)

    def result(self) -> T:
        match self._status:
            case Status.Fulfilled:
                return self._result
            case Status.Rejected:
                raise self._result
            case Status.Cancelled:
                raise asyncio.CancelledError()
            case _:
                raise asyncio.InvalidStateError()

    def exception(self) -> Any:
        match self._status:
            case Status.Rejected:
                raise self._result
            case Status.Cancelled:
                raise asyncio.CancelledError()
        return None

    def done(self) -> bool:
        return self._status in (Status.Fulfilled, Status.Rejected, Status.Cancelled)

    def cancelled(self) -> bool:
        return self._status is Status.Cancelled

    # Promise interface

    def cancel(self, msg: Any | None = None):
        """
        If the promise has an on_cancel callback, calls that callback and sets
        the Promise's state to Cancelled. Otherwise, rejects the promise with
        a CancellationError. In the former case, the on_cancel callback is
        responsible for resolving or rejecting the promise, or raising an
        exception to automatically reject with that exception value.
        """
        if self._status is not Status.Pending:
            return False

        self._status = Status.Cancelled
        try:
            if self._on_cancel:
                self._on_cancel()
            else:
                raise CancellationError()
        except (Exception, CancelledError) as e:
            self._resolvers.reject(e)
        return True

    @staticmethod
    def from_awaitable[U](awaitable: Awaitable[PromiseLike[U] | U], /) -> Promise[U]:
        """
        Converts any awaitable object into a promise which resolves with the
        awaitable's return value, or rejects with any exceptions that it
        raises.

        Any Promise-like object yielded by the awaitable will be awaited. If
        it resolves, its resolution value will be sent back to the awaitable.
        If it rejects, its rejection value will be thrown.
        """
        return Loop(awaitable).promise

    @overload
    @staticmethod
    def wrap[**P, RT](
        func: Callable[P, Coroutine[Any, Any, RT]], /
    ) -> Callable[P, Promise[RT]]: ...

    @overload
    @staticmethod
    def wrap[U](func: FutureLike[U], /) -> Promise[U]: ...

    @staticmethod
    def wrap[**P, RT, U](
        func: Callable[P, Coroutine[Any, Any, PromiseLike[RT] | RT]] | FutureLike[U],
        /,
    ) -> Callable[P, Promise[RT]] | PromiseLike[U]:
        """
        Decorator which wraps an async function so that, when called, it is
        scheduled for execution on the next tick of the event loop, and
        returns a promise which resolves with its return value or rejects with
        any errors that it throws.

        The wrapped callable is may be called from any thread, but the async
        function will always execute on the main thread.
        """

        if isfuture(func):
            if ispromise(func):
                return func

            def fn(resolve: ResFn[U], reject: HandlerFn):
                @func.add_done_callback
                def callback(future: FutureLike[U]):
                    try:
                        resolve(future.result())
                    except (Exception, asyncio.CancelledError) as e:
                        reject(e)

            def cancel():
                func.cancel()

            return Promise(fn, cancel)

        @wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> Promise:
            return Promise.from_awaitable(func(*args, **kwargs))

        return wrapper

    def _run_handlers(self) -> None:
        """
        If the promise has been settled, runs any pending resolution or
        rejection handlers at the top of the application event loop, and
        removes them from the queue.

        If the promise has not yet been settled, does nothing.
        """
        match self._status:
            case Status.Fulfilled:
                for handler in self._resolve_handlers:
                    call_soon(partial(run_handler, handler, self._result))
            case Status.Rejected:
                for handler in self._reject_handlers:
                    call_soon(partial(run_handler, handler, self._result))
                    self._handled_rejection = True
            case _:
                return

        self._resolve_handlers.clear()
        self._reject_handlers.clear()

    def _settle(self, result: Any, status: Status):
        assert self._status in (Status.Pending, Status.Cancelled)
        self._result = result
        self._status = status
        self._run_handlers()
        self._resolvers.promise = None

    def report_error(error: Any):
        import traceback

        traceback.print_exception(error)

    def __del__(self) -> None:
        """
        Checks whether rejected promises have called a rejection handler and,
        if not, propagates the rejection value to the Qt runtime as an
        unhandled exception.
        """
        if self._status is Status.Rejected and not self._handled_rejection:
            Promise.report_error(self._result)

    @overload
    def then[RT, RU](
        self,
        on_resolve: HandlerFn[T, PromiseLike[RT] | RT],
        on_reject: HandlerFn[Any, PromiseLike[RU] | RU] | None = None,
        /,
    ) -> Promise[RT | RU]: ...

    @overload
    def then[RU](
        self,
        on_resolve: None,
        on_reject: HandlerFn[Any, PromiseLike[RU] | RU],
        /,
    ) -> Promise[T | RU]: ...

    def then[RT, RU](
        self,
        on_resolve: HandlerFn[T, PromiseLike[RT] | RT] | None,
        on_reject: HandlerFn[Any, PromiseLike[RU] | RU] | None = None,
        /,
    ) -> Promise:
        """
        Equivalent to the JavaScript Promise#then method.

        The appropriate callback will be called from the top of the main
        thread event loop after the promise resolves or rejects.

        Returns a new Promise which resolves or rejects with the return value
        of whichever callback is called when the promise is settled. If the
        callback returns a Promise, the returned promise is settled with the
        eventual result of that Promise.
        """

        @Promise
        def result(resolve: ResFn, reject: ResFn) -> None:
            self._resolve_handlers.append(
                PromiseHandler(on_resolve or resolve, resolve, reject)
            )
            self._reject_handlers.append(
                PromiseHandler(on_reject or reject, resolve, reject)
            )

        self._run_handlers()
        return result

    def catch[U](
        self, on_reject: HandlerFn[Any, PromiseLike[U] | U], /
    ) -> Promise[T | U]:
        """
        Equivalent to the JavaScript Promise#catch method, which is equivalent
        to passing the given rejection callback as the second argument of the
        Promise.then method.
        """
        return self.then(None, on_reject)

    def finally_(self, callback: Callable[[], PromiseLike | None], /) -> Promise[T]:
        """
        Equivalent to the JavaScript Promise#finally method, which is
        approximately equivalent to passing the given callback as both the
        resolve and reject argument of the Promise.then method, except that:

            a) The callback is called with no arguments,
            b) The return value of the callback is ignored unless it returns a
               promise which rejects or throws an exception, and,
            c) The returned promise settles with the final state of the
               original promise unless, per b), the handler returns a rejected
               promise or raises an exception, in which case the returned
               promise rejects with that rejection value or exception.
        """

        def on_finally(arg: Any) -> Promise[T]:
            if ispromise(res := callback()):

                @res.then
                def promise(result):
                    return self

                return promise
            return self

        return self.then(on_finally, on_finally)

    with_resolvers: ClassVar = PromiseWithResolvers

    # We should be able to dispense with these overloads and just declare:
    #
    #   def resolve[U](val: U = None, /) -> Promise[U]
    #
    # but zuban refuses to accept it as a valid definition.
    @staticmethod
    @overload
    def resolve() -> Promise[None]: ...

    @staticmethod
    @overload
    def resolve[U](val: PromiseLike[U] | U, /) -> Promise[U]: ...

    @staticmethod
    def resolve(val: Any = None, /) -> Promise:
        @Promise
        def promise(resolve: ResFn, reject: ResFn) -> None:
            resolve(val)

        return promise

    @staticmethod
    def reject(val: Any = None, /) -> Promise[T]:
        @Promise[T]
        def promise(resolve: ResFn[T], reject: ResFn) -> None:
            reject(val)

        return promise

    @staticmethod
    def all[U](promises_iter: Iterable[Promise[U]], /) -> Promise[list[U]]:
        promises = list(promises_iter)

        @Promise[list[U]]
        def promise(resolve: ResFn[list[U]], reject: ResFn) -> None:
            settled: list[bool] = [False] * len(promises)
            results = list[None | U]([None]) * len(promises)

            def catch(exc: Any) -> None:
                reject(exc)

            def then_handler(i: int, val: U) -> None:
                settled[i] = True
                results[i] = val

                if all(settled):
                    resolve(cast_list_some(results))

            for i in range(len(promises)):
                promises[i].then(partial(then_handler, i), catch)

            if len(promises) == 0:
                resolve([])

        return promise

    @staticmethod
    def all_settled[U](
        promises_iter: Iterable[Promise[U]],
        /,
    ) -> Promise[list[PromiseOutcome[U]]]:
        promises = list(promises_iter)

        @Promise[list[PromiseOutcome[U]]]
        def promise(resolve: ResFn[list[PromiseOutcome[U]]], reject: ResFn):
            results: list[None | PromiseOutcome[U]] = [None] * len(promises)

            def maybe_resolve():
                if all(results):
                    resolve(cast_list_some(results))

            def add_handler(i: int):
                @promises[i].catch
                def catch(exc: Any) -> None:
                    results[i] = PromiseRejectedOutcome(exc)
                    maybe_resolve()

                @promises[i].then
                def then_handler(val: U) -> None:
                    results[i] = PromiseFulfilledOutcome(val)
                    maybe_resolve()

            for i in range(len(promises)):
                add_handler(i)

            maybe_resolve()

        return promise

    @staticmethod
    def race[U](promises: Iterable[Promise[U]], /) -> Promise[U]:
        @Promise[U]
        def promise(resolve: ResFn[U], reject: ResFn):
            def resolved(val: U) -> None:
                resolve(val)

            def rejected(exc: Any) -> None:
                reject(exc)

            for promise in promises:
                promise.then(resolved, rejected)

        return promise


Status = Promise.Status
