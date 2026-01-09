from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING

from pytest_mock import MockerFixture

from .utils import SaveAttr, lazy

if TYPE_CHECKING:
    from ankiwanikanisync.collection import WKCollection


def test_version():
    from ankiwanikanisync import __version__

    root = Path(__file__).parent.parent

    with (root / "package.json").open("r") as f:
        package_json = json.load(f)

    with (root / "pyproject.toml").open("rb") as bf:
        pyproject = tomllib.load(bf)

    assert __version__ == package_json["version"]
    assert __version__ == pyproject["project"]["version"]


def test_on_sync(mocker: MockerFixture, save_attr: SaveAttr, wk_col: WKCollection):
    from aqt import gui_hooks

    from ankiwanikanisync import hooks

    save_attr(hooks, "anki_closing")

    auto_sync = mocker.patch("ankiwanikanisync.sync.auto_sync", autospec=True)
    update_level = mocker.patch.object(wk_col, "update_current_level_op", autospec=True)

    gui_hooks.profile_did_open()
    gui_hooks.sync_did_finish()

    auto_sync.assert_called_once_with()
    update_level.assert_called_once_with()
    mocker.resetall()

    gui_hooks.sync_did_finish()

    assert not auto_sync.called
    update_level.assert_called_once_with()
    mocker.resetall()

    gui_hooks.profile_will_close()
    gui_hooks.sync_did_finish()

    assert not auto_sync.called
    assert not update_level.called


def test_on_init(mocker: MockerFixture, save_attr: SaveAttr, wk_col: WKCollection):
    from aqt import gui_hooks

    import ankiwanikanisync

    save_attr(lazy.config, "_version")

    ui_init = mocker.patch("ankiwanikanisync.ui.init")
    update_html = mocker.patch("ankiwanikanisync.importer.update_html")

    lazy.config._version = ""

    gui_hooks.main_window_did_init()

    ui_init.assert_called_once_with()
    update_html.assert_called_once_with()
    mocker.resetall()

    assert lazy.config._version == ankiwanikanisync.__version__

    gui_hooks.main_window_did_init()

    ui_init.assert_called_once_with()
    assert not update_html.called
