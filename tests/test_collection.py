from __future__ import annotations

from typing import TYPE_CHECKING, cast

import pytest
from anki.consts import QUEUE_TYPE_LRN, QUEUE_TYPE_SUSPENDED

from ankiwanikanisync.types import (
    WKMeaning,
    WKReading,
    WKReadingType,
    WKSubject,
    WKSubjectDataBase,
)

from .fixtures import SubSession
from .utils import (
    cleanup_after,
    get_note,
    lazy,
    make_card_learn,
    make_card_review,
    reltime,
)

if TYPE_CHECKING:
    from ankiwanikanisync.collection import WKCollection

cleanup = cleanup_after("function")


def meaning(meaning: str, primary: bool = True) -> WKMeaning:
    return WKMeaning(meaning=meaning, primary=primary, accepted_answer=True)


def reading(
    reading: str, primary: bool = True, type_: WKReadingType | None = None
) -> WKReading:
    res = WKReading(reading=reading, primary=primary, accepted_answer=True)
    if type_:
        res["type"] = type_
    return res


@pytest.mark.asyncio
async def test_unlock_notes(session_mock: SubSession, wk_col: WKCollection):
    radical1 = session_mock.add_subject(
        "radical",
        characters="工",
        meanings=[meaning("Construction")],
    )

    radical2 = session_mock.add_subject(
        "radical",
        characters="口",
        meanings=[meaning("Mouth")],
    )

    session_mock.add_subject("kanji", characters="一", level=1)

    kanji2 = session_mock.add_subject(
        "kanji",
        characters="右",
        component_subject_ids=[radical2["id"]],
        meanings=[meaning("Right")],
        readings=[
            reading("ゆう", True, "onyomi"),
            reading("う", False, "onyomi"),
            reading("みぎ", False, "kunyomi"),
        ],
    )
    radical2["data"]["amalgamation_subject_ids"] = [kanji2["id"]]

    kanji3 = session_mock.add_subject(
        "kanji",
        characters="左",
        component_subject_ids=[radical1["id"]],
        meanings=[meaning("Left")],
        readings=[
            reading("さ", True, "onyomi"),
            reading("ひだり", False, "kunyomi"),
        ],
    )
    radical1["data"]["amalgamation_subject_ids"] = [kanji3["id"]]

    vocab1 = session_mock.add_subject(
        "vocabulary",
        characters="左右",
        component_subject_ids=[kanji2["id"], kanji3["id"]],
        meanings=[
            meaning("Left And Right"),
            meaning("Both Ways", False),
            meaning("Influence", False),
            meaning("Control", False),
        ],
        readings=[reading("さゆう")],
    )
    kanji2["data"]["amalgamation_subject_ids"] = [vocab1["id"]]
    kanji3["data"]["amalgamation_subject_ids"] = [vocab1["id"]]

    lazy.config._current_level = 1
    await lazy.sync.do_sync()

    subjs = cast(
        list[WKSubject[WKSubjectDataBase]], [radical1, radical2, kanji2, kanji3, vocab1]
    )
    for subj in subjs:
        note = get_note(subj)
        for card in note.cards():
            assert card.queue == QUEUE_TYPE_SUSPENDED

    def check_note[T: WKSubjectDataBase](subj: WKSubject[T], delta_ts: int):
        note = get_note(subj)
        for card in note.cards():
            assert card.queue == QUEUE_TYPE_LRN
            assert card.due == pytest.approx(
                reltime(seconds=delta_ts).timestamp(), abs=10
            )

    await wk_col.unlock_notes([get_note(vocab1).id])

    delta = 60 * 10
    check_note(radical1, 0)
    check_note(radical2, 0)
    check_note(kanji2, delta)
    check_note(kanji3, delta)
    check_note(vocab1, delta * 2)


@pytest.mark.asyncio
async def test_is_unlockable(session_mock: SubSession, wk_col: WKCollection):
    kanji1 = session_mock.add_subject("kanji", level=60)

    kanji2 = session_mock.add_subject("kanji", level=1)

    await lazy.sync.do_sync()

    assert wk_col.is_unlockable(get_note(kanji1))

    note = get_note(kanji2)
    assert wk_col.is_unlockable(note)

    make_card_learn(note, due=reltime())
    assert not wk_col.is_unlockable(note)

    make_card_review(note, ivl=1)
    assert not wk_col.is_unlockable(note)
