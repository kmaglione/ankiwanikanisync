from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Final, Generator, Sequence, TypeVar, cast, overload

from anki.collection import OpChangesWithCount
from aqt import mw
from aqt.operations import CollectionOp, QueryOp
from aqt.utils import tooltip

Q = TypeVar("Q", bound=Callable[..., Any])


# When fetching objects from WaniKani by lists of IDs, break requests into
# chunks of this size.
CHUNK_SIZE: Final = 1024


def chunked[T](
    seq: Sequence[T], /, chunk_size: int = CHUNK_SIZE
) -> Generator[tuple[int, Sequence[T]], None, None]:
    for i in range(0, len(seq), chunk_size):
        yield i, seq[i : i + chunk_size]


def maybe_chunked[T](
    desc: str, seq: Sequence[T] | None, /, chunk_size: int = CHUNK_SIZE
) -> Generator[Sequence[T] | None, None, None]:
    if seq is None:
        report_progress(f"Fetching all {desc}...", 0, 0)
        yield None
    else:
        for i in range(0, len(seq), chunk_size):
            chunk = seq[i : i + chunk_size]
            report_progress(
                f"Fetching {desc} {i}-{i + len(chunk) - 1}/{len(seq)}...", i, len(seq)
            )
            yield chunk


@overload
def query_op(
    *, with_progress: bool = False, without_collection=False
) -> Callable[[Q], Q]: ...


@overload
def query_op(func: Q, /) -> Q: ...


def query_op(
    func: Q | None = None, /, *, with_progress: bool = False, without_collection=False
):
    def decorator(func: Q) -> Q:
        @wraps(func)
        def wrapper(*args, **kwargs):
            query_op = QueryOp(
                parent=mw,
                op=lambda _: func(*args, **kwargs),
                success=lambda _: None,
            )
            if without_collection:
                query_op.without_collection()
            if with_progress:
                query_op.with_progress()
            query_op.run_in_background()

        return cast(Q, wrapper)

    if func:
        return decorator(func)
    return decorator


def collection_op[**P, T: OpChangesWithCount](
    func: Callable[P, T],
) -> Callable[P, None]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs):
        CollectionOp(
            mw,
            lambda _: func(*args, **kwargs),
        ).run_in_background()

    return wrapper


def compose[FRT, **GP, GRT](
    f: Callable[[GRT], FRT], g: Callable[GP, GRT]
) -> Callable[GP, FRT]:
    def composed(*args: GP.args, **kwargs: GP.kwargs) -> FRT:
        return f(g(*args, **kwargs))

    composed.__name__ = f"{f.__name__}∘{g.__name__}"
    composed.__qualname__ = f"{f.__qualname__}∘{g.__qualname__}"
    if False:
        # This might be nice in some limited use cases, but probably isn't
        # worth the computational cost of copying the __annotations__ dict
        # most of the time.
        composed.__type_params__ = g.__type_params__ # type: ignore
        composed.__annotations__ = dict(g.__annotations__)
        composed.__annotations__["return"] = f.__annotations__["return"]
    return composed


def wknow():
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def wkparsetime(txt):
    return datetime.fromisoformat(txt.replace("Z", "+00:00"))


def report_progress(txt, val, max):
    mw.taskman.run_on_main(lambda: mw.progress.update(label=txt, value=val, max=max))


def show_tooltip(txt, period=3000):
    mw.taskman.run_on_main(lambda: tooltip(txt, period=period))
