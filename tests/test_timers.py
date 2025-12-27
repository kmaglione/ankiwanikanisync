from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING
from unittest.mock import call

import pytest
from pytest_mock import MockerFixture

from ankiwanikanisync.promise import Promise

from .conftest import aqt
from .fixtures import SubSession
from .utils import (
    MockRevlog,
    forward_args,
    get_note,
    iso_reltime,
    lazy,
    make_card_review,
    reltime,
    to_timedelta,
)

if TYPE_CHECKING:
    from ankiwanikanisync.collection import WKCollection


@pytest.fixture(autouse=True)
def stop_timers():
    yield
    lazy.timers.stop_timers()


@forward_args(to_timedelta)
def approx_ivl(*args, **kwargs):
    delta = to_timedelta(*args, **kwargs)
    return pytest.approx(delta.total_seconds() * 1000, abs=10000)


@pytest.mark.asyncio
async def test_timers_basic():
    timers = lazy.timers

    timers.start_timers()

    ivl = timedelta(hours=1)
    assert timers.submit_lessons_timer.remainingTime() == approx_ivl(ivl)
    assert timers.sync_due_timer.remainingTime() == approx_ivl(ivl)

    await aqt.mw.taskman.pending_ops_completed()

    ivl = timedelta(days=1)
    assert timers.submit_reviews_timer.remainingTime() == approx_ivl(ivl)


@pytest.mark.asyncio
async def test_timers_reviews(
    revlog_mock: MockRevlog,
    session_mock: SubSession,
    subtests: pytest.Subtests,
    wk_col: WKCollection,
):
    timers = lazy.timers
    timer = timers.submit_reviews_timer

    kanji = session_mock.add_subject("kanji")
    await lazy.sync.do_sync()

    for card in get_note(kanji).cards():
        make_card_review(card, ivl=1)

        revlog_mock.add_entry(card, button_chosen=3, time=reltime().timestamp())

    max_ivl = timedelta(**lazy.config.SYNC_INTERVAL_REVIEWS_MAX)
    assignment = session_mock.add_assignment(
        subject_id=kanji["id"],
        available_at=iso_reltime(max_ivl * 2),
        srs_stage=0,
    )

    with subtests.test("Interval greater than max"):
        await timers.start_reviews_timer()
        assert timer.remainingTime() == approx_ivl(max_ivl)

    ivl = timedelta(hours=3)
    with subtests.test("Interval less than max"):
        assignment["data"]["available_at"] = iso_reltime(ivl)
        await timers.start_reviews_timer()
        assert timer.remainingTime() == approx_ivl(ivl)

    with subtests.test("Interval greater than current"):
        assignment["data"]["available_at"] = iso_reltime(hours=4)
        await timers.start_reviews_timer()
        assert timer.remainingTime() == approx_ivl(ivl)


def pending_ops_complete():
    return aqt.mw.taskman.pending_ops_completed()


def test_timers_sync_due(mocker: MockerFixture):
    sync_op = mocker.patch("ankiwanikanisync.sync.SyncOp", autospec=True)

    lazy.timers.sync_due_timer.timeout.emit()

    assert sync_op.mock_calls == [call(), call().update_intervals()]


@pytest.mark.asyncio
async def test_timers_submit_lessons(mocker: MockerFixture):
    sync_op = mocker.patch("ankiwanikanisync.sync.SyncOp", autospec=True)

    last_time = iso_reltime(days=-1)
    lazy.config._last_lessons_sync = last_time

    time = reltime(hours=-1)
    sync_op.return_value.upstream_available_assignments_op.return_value = (
        Promise.resolve(time)
    )

    lazy.timers.submit_lessons_timer.timeout.emit()
    await pending_ops_complete()

    assert sync_op.mock_calls == [
        call(),
        call().upstream_available_assignments_op(
            reviews=False, lessons=True, updated_after=last_time
        ),
    ]

    assert lazy.config._last_lessons_sync == time.isoformat()


@pytest.mark.asyncio
async def test_timers_submit_reviews(mocker: MockerFixture):
    sync_op = mocker.patch("ankiwanikanisync.sync.SyncOp", autospec=True)

    time = reltime(hours=1)
    sync_op.return_value.get_next_assignment_available_op.return_value = (
        Promise.resolve(time)
    )

    lazy.timers.submit_reviews_timer.timeout.emit()
    await pending_ops_complete()

    assert lazy.timers.submit_reviews_timer.remainingTime() == approx_ivl(
        timedelta(hours=1)
    )

    assert sync_op.mock_calls == [
        call(),
        call().upstream_available_assignments_op(reviews=True, lessons=False),
        call(),
        call().get_next_assignment_available_op(),
    ]
