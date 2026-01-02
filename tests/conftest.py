from __future__ import annotations

import asyncio
import functools
import importlib
import json
import traceback
from typing import TYPE_CHECKING, Any, AsyncGenerator, Callable, Generator

import anki.lang
import pytest
import pytest_asyncio
from anki.collection import Collection

from .fixtures import BaseSession, SubSession
from .utils import MockRevlog, PartialDict, SaveAttr, saving_attr

if TYPE_CHECKING:
    from aqt.qt import QAction

    from ankiwanikanisync.collection import WKCollection

    from .stubs import aqt
else:
    import aqt

from ankiwanikanisync.promise import Promise
from ankiwanikanisync.promise_asyncio import AsyncIOScheduler

_asyncio_scheduler = AsyncIOScheduler()
Promise.set_scheduler(_asyncio_scheduler)


res = importlib.resources.files("ankiwanikanisync")
with (res / "config.json").open("r") as f:
    config = json.load(f)
    config["WK_API_KEY"] = "4be6fb9a-0929-40b5-90f3-a98cef816c55"
    # Mocking for this is not implemented yet
    config["FETCH_CONTEXT_PATTERNS"] = False
    config["SYNC_ALL"] = True
    aqt.mw.addonManager.getConfig.return_value = config

aqt.mw.progress.want_cancel.return_value = False


def pytest_assertrepr_compare(
    config: pytest.Config, op: str, left: object, right: object
) -> list[str] | None:
    if isinstance(left, PartialDict) or isinstance(right, PartialDict):
        return PartialDict.assertrepr_compare(config, op, left, right)
    return None


@pytest.fixture(scope="session", autouse=True)
def col(tmp_path_factory: pytest.TempPathFactory) -> Collection:
    anki.lang.set_lang("en_US")

    path = tmp_path_factory.mktemp("anki")
    aqt.mw.col = Collection(str(path / "anki.anki2"))
    return aqt.mw.col


@pytest.fixture(scope="session")
def wk_col(col: Collection) -> WKCollection:
    from ankiwanikanisync.collection import wk_col

    return wk_col


@pytest.fixture(scope="session")
def tools_menu(col: Collection) -> dict[str, QAction]:
    import aqt
    from aqt.qt import QAction

    from ankiwanikanisync import ui

    ui.init_tools_menu()

    menuAction = aqt.mw.form.menuTools.actions()[0]
    assert isinstance(menuAction, QAction)
    menu = menuAction.menu()
    assert menu

    assert menu.title() == "WaniKani"

    res = dict[str, Any]()
    for action in menu.actions():
        if not action.isSeparator():
            res[action.text()] = action

    return res


type AddFinalizer = Callable[[Callable[[], None]], None]


@pytest.fixture
def add_finalizer():
    class AddFinalizer:
        def __init__(self):
            self.finalizers = list[Callable[[], None]]()

        def __call__(self, cb: Callable[[], None]):
            self.finalizers.append(cb)

    add_finalizer = AddFinalizer()

    yield add_finalizer

    for cb in add_finalizer.finalizers:
        try:
            cb()
        except Exception as e:
            traceback.print_exception(e)


@pytest.fixture
def save_attr() -> Generator[SaveAttr]:
    with SaveAttr() as save_attr:
        yield save_attr


@pytest.fixture(scope="session", autouse=True)
def base_session_mock(col) -> Generator[BaseSession]:
    from ankiwanikanisync import importer

    importer.get_pitch_data = functools.cache(importer.get_pitch_data)

    with BaseSession() as mock:
        yield mock


@pytest.fixture(scope="class")
def session_mock(base_session_mock) -> Generator[SubSession]:
    with base_session_mock.sub_session() as mock:
        yield mock


@pytest.fixture(scope="class")
def revlog_mock(col: Collection) -> Generator[MockRevlog]:
    with MockRevlog(col) as mock:
        yield mock


@pytest_asyncio.fixture(autouse=True)
async def asyncio_scheduler() -> AsyncGenerator[AsyncIOScheduler]:
    with saving_attr(_asyncio_scheduler, "loop"), saving_attr(aqt.mw.taskman, "loop"):
        loop = asyncio.get_event_loop()
        _asyncio_scheduler.loop = loop
        aqt.mw.taskman.loop = loop

        yield _asyncio_scheduler

        await aqt.mw.taskman.pending_ops_completed()
