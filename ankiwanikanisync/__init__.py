import sys
from pathlib import Path
from typing import Any, Callable

sys.path.append(str(Path(__file__).parent / "deps"))

from aqt import gui_hooks, mw
from aqt.browser.browser import Browser
from aqt.qt import QAction, QMenu, qconnect

from .collection import wk_col
from .importer import do_update_html, ensure_audio
from .play_all_audio import install_play_all_audio
from .sync import auto_sync, do_clear_cache, do_process, do_sync, do_update_intervals
from .timers import timers


def init_tools_menu():
    menu = QMenu("WaniKani", mw)
    mw.form.menuTools.addMenu(menu)

    def add_action(label: str, fn: Callable[[], Any]) -> None:
        def callback():
            fn()
        action = QAction(label, mw)
        qconnect(action.triggered, callback)
        menu.addAction(action)

    add_action("Sync Notes", do_sync)

    add_action("Sync Due Dates", do_update_intervals)

    add_action("Reprocess Notes", do_process)

    # add_action("Review Mature Cards", do_autoreview)

    menu.addSeparator()

    add_action("Clear Cache", do_clear_cache)

    menu.addSeparator()

    add_action("Overwrite Card HTML", do_update_html)


class BrowserMenu(object):
    def __init__(self):
        gui_hooks.browser_menus_did_init.append(self.create_browser_menu)
        gui_hooks.browser_will_show_context_menu.append(self.update_browser_menu)

    def create_browser_menu(self, browser: Browser) -> None:
        self.browser = browser

        self.unlock_action = QAction("Study WaniKani note", self.browser)
        self.browser.form.menu_Notes.addAction(self.unlock_action)
        qconnect(self.unlock_action.triggered, self.unlock_selected_notes)

    def update_browser_menu(self, browser: Browser, menu: QMenu) -> None:
        enable = any(
            wk_col.is_unlockable(wk_col.get_note(note_id))
            for note_id in self.browser.table.get_selected_note_ids()
        )
        self.unlock_action.setDisabled(not enable)

    def unlock_selected_notes(self) -> None:
        wk_col.unlock_notes(self.browser.table.get_selected_note_ids())


class Hooks:
    just_loaded = False
    anki_closing = False

    def __init__(self):
        gui_hooks.profile_did_open.append(self.on_load)
        gui_hooks.profile_will_close.append(self.on_close)
        gui_hooks.sync_did_finish.append(self.on_synced)

    def on_load(self):
        self.just_loaded = True
        self.anki_closing = False
        ensure_audio()
        timers.start_timers()

    def on_close(self):
        self.anki_closing = True

    def on_synced(self):
        if self.anki_closing:
            return
        if self.just_loaded:
            auto_sync()
        self.just_loaded = False
        wk_col.update_current_level()


init_tools_menu()

brower_menu = BrowserMenu()
hooks = Hooks()

install_play_all_audio()
