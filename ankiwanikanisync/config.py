from __future__ import annotations

from typing import Any, TypedDict

from aqt import mw


class TimeDeltaArgs(TypedDict, total=False):
    days: int
    seconds: int
    microseconds: int
    milliseconds: int
    minutes: int
    hours: int
    weeks: int


class Prop[T]:
    def __init__(self, default_value: T):
        self.default_value = default_value

    def __set_name__(self, owner, name: str):
        self.name = name

    def __get__(self, inst: WKConfig, model) -> T:
        return inst.config.get(self.name, self.default_value)

    def __set__(self, inst: WKConfig, value: T):
        inst.config[self.name] = value
        mw.addonManager.writeConfig(__name__, inst.config)


class WKConfig(object):
    _config: None | dict[str, Any] = None

    @property
    def config(self) -> dict[str, Any]:
        if not self._config:
            self._config = mw.addonManager.getConfig(__name__)
        assert self._config is not None
        return self._config

    AUTO_SYNC = Prop[bool](False)
    DECK_NAME = Prop[str]("WaniKani Sync")
    FETCH_CONTEXT_PATTERNS = Prop[bool](True)
    GURU_INTERVAL = Prop[int](5)
    LEVEL_COMPLETE_RATIO = Prop[float](0.9)
    NOTE_TYPE_NAME = Prop[str]("WaniKani Sync")
    SYNC_ALL = Prop[bool](False)
    SYNC_INTERVAL_REVIEWS_MAX = Prop[TimeDeltaArgs]({"days": 1})
    SYNC_INTERVAL_LESSONS = Prop[TimeDeltaArgs]({"hours": 1})
    SYNC_INTERVAL_DUE = Prop[TimeDeltaArgs]({"hours": 1})
    UNLOCK_EXTRA_LEVELS_KANJI = Prop[int](0)
    UNLOCK_EXTRA_LEVELS_RADICAL = Prop[int](1)
    UNLOCK_EXTRA_LEVELS_VOCAB = Prop[int](0)
    WK_API_KEY = Prop[str]("")
    _current_level = Prop[int](1)
    _last_subjects_sync = Prop[str]("")
    _last_assignments_sync = Prop[str]("")
    _last_lessons_sync = Prop[str]("")
    _last_due_sync = Prop[str]("")
    _version = Prop[str]("")


config = WKConfig()
