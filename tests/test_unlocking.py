from __future__ import annotations

from typing import TYPE_CHECKING, Literal
from unittest.mock import call

import pytest
from anki.consts import (
    QUEUE_TYPE_NEW,
    QUEUE_TYPE_SUSPENDED,
)
from aqt import gui_hooks, mw
from aqt.reviewer import Reviewer
from pytest_mock import MockerFixture

from ankiwanikanisync.types import (
    WKKanjiData,
    WKRadicalData,
    WKSubject,
)

from .fixtures import SubSession
from .utils import (
    NoteMatcher,
    cleanup_after,
    cleanup_collection,
    get_note,
    lazy,
    make_card_review,
)

if TYPE_CHECKING:
    from ankiwanikanisync.collection import WKCollection

cleanup = cleanup_after("function")


@pytest.mark.asyncio
async def test_review_hooks(
    mocker: MockerFixture,
    session_mock: SubSession,
    subtests: pytest.Subtests,
    wk_col: WKCollection,
):
    from ankiwanikanisync.config import config

    SyncOp_mock = mocker.patch("ankiwanikanisync.sync.SyncOp", autospec=True)
    update_dependents_mock = mocker.patch.object(wk_col, "update_dependents")
    update_current_level_op_mock = mocker.patch.object(
        wk_col, "update_current_level_op"
    )

    kanji = session_mock.add_subject("kanji")
    await lazy.sync.do_sync()
    note = get_note(kanji)

    cards = note.cards()
    make_card_review(cards[0], ivl=config.GURU_INTERVAL)
    make_card_review(cards[1], ivl=1)

    ease: tuple[bool, Literal[3]] = (True, 3)
    reviewer = Reviewer(mw)

    def check_SyncOp():
        assert SyncOp_mock.mock_calls[-1] == call().upstream_review_op(
            NoteMatcher(note)
        )
        SyncOp_mock.reset_mock()

    with subtests.test("Not guru to not guru"):
        res = gui_hooks.reviewer_will_answer_card(ease, reviewer, cards[1])
        assert res == ease
        gui_hooks.reviewer_did_answer_card(reviewer, cards[1], ease[1])
        assert not update_dependents_mock.called
        assert not update_current_level_op_mock.called
        check_SyncOp()

    with subtests.test("Not guru to guru"):
        res = gui_hooks.reviewer_will_answer_card(ease, reviewer, cards[1])
        assert res == ease
        cards[1].ivl = config.GURU_INTERVAL
        wk_col.col.update_cards(cards)

        gui_hooks.reviewer_did_answer_card(reviewer, cards[1], ease[1])
        update_dependents_mock.assert_called_once_with(cards[1].note())
        assert not update_current_level_op_mock.called
        check_SyncOp()

        update_dependents_mock.reset_mock()

    with subtests.test("Guru to guru"):
        res = gui_hooks.reviewer_will_answer_card(ease, reviewer, cards[1])
        gui_hooks.reviewer_did_answer_card(reviewer, cards[1], ease[1])
        assert not update_dependents_mock.called
        assert not update_current_level_op_mock.called
        check_SyncOp()

    with subtests.test("Not guru to guru - current level"):
        cards[1].ivl = 1
        wk_col.col.update_cards(cards)

        config._current_level = int(note["Level"])

        res = gui_hooks.reviewer_will_answer_card(ease, reviewer, cards[1])
        assert res == ease
        cards[1].ivl = config.GURU_INTERVAL
        wk_col.col.update_cards(cards)

        gui_hooks.reviewer_did_answer_card(reviewer, cards[1], ease[1])
        update_dependents_mock.assert_called_once_with(cards[1].note())
        update_current_level_op_mock.assert_called_once_with()
        check_SyncOp()

        update_dependents_mock.reset_mock()
        update_current_level_op_mock.reset_mock()


@pytest.mark.asyncio
async def test_update_dependents_and_level(
    mocker: MockerFixture,
    session_mock: SubSession,
    subtests: pytest.Subtests,
    wk_col: WKCollection,
):
    from ankiwanikanisync.config import config

    cleanup_collection()

    class Level:
        def __init__(self):
            self.radicals = list[WKSubject[WKRadicalData]]()
            self.kanji = list[WKSubject[WKKanjiData]]()

    levels = dict[int, Level]()
    for level_no in (1, 4):
        levels[level_no] = level = Level()

        for i in range(0, 10):
            radical = session_mock.add_subject(
                "radical", characters=f"r{i}", level=level_no
            )
            level.radicals.append(radical)

            kanji = session_mock.add_subject(
                "kanji",
                characters=f"k{i}",
                component_subject_ids=[radical["id"]],
                level=level_no,
            )
            level.kanji.append(kanji)

    await lazy.sync.do_sync()

    assert config._current_level == 1

    def check_radicals(level_no: int):
        radical_queue = (
            QUEUE_TYPE_SUSPENDED
            if level_no > config._current_level
            else QUEUE_TYPE_NEW
        )

        for radical in levels[level_no].radicals:
            note = get_note(radical)
            for card in note.cards():
                assert card.queue == radical_queue

    def check_kanji(level_no: int, unlocked: bool):
        kanji_queue = (
            QUEUE_TYPE_SUSPENDED
            if not unlocked or level_no > config._current_level
            else QUEUE_TYPE_NEW
        )

        for kanji in levels[level_no].kanji:
            note = get_note(kanji)
            for card in note.cards():
                assert card.queue == kanji_queue

    for level_no in levels:
        with subtests.test("Initial level status", level_no=level_no):
            check_radicals(level_no)
            check_kanji(level_no, False)

    for level_no, level in levels.items():
        with subtests.test("Guru radicals", level_no=level_no):
            for radical in level.radicals:
                note = get_note(radical)
                for card in note.cards():
                    make_card_review(card, ivl=config.GURU_INTERVAL)

            for radical in level.radicals:
                await wk_col.update_dependents(get_note(radical))

            check_kanji(level_no, True)

    level = levels[1]
    for i, kanji in enumerate(level.kanji):
        ratio = (i + 1) / len(level.kanji)
        with subtests.test("Update level complete", ratio=ratio):
            note = get_note(kanji)
            for card in note.cards():
                make_card_review(card, ivl=config.GURU_INTERVAL)

            await wk_col.update_current_level_op()

            complete = ratio >= config.LEVEL_COMPLETE_RATIO
            expected_level = 4 if complete else 1
            assert config._current_level == expected_level

            check_kanji(4, True)
