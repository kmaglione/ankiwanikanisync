from __future__ import annotations

import re
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING, Any, Final, NamedTuple, cast
from unittest.mock import call, patch

import pytest
from anki.consts import CARD_TYPE_LRN, QUEUE_TYPE_LRN
from pytest_mock import MockerFixture

if TYPE_CHECKING:
    from requests_mock.request import Request
    from requests_mock.response import Context

from ankiwanikanisync.types import (
    WKAssignment,
    WKMeaning,
    WKReading,
    WKReadingType,
    WKSubject,
    WKSubjectDataBase,
)
from ankiwanikanisync.wk_api import WKReviewData

from .fixtures import SubSession
from .utils import (
    ApproxDatetime,
    MockRevlog,
    PartialDict,
    approx_reltime,
    cleanup_after,
    forward_args,
    get_note,
    iso_reltime,
    lazy,
    make_card_learn,
    make_card_new,
    make_card_review,
    pending_ops_complete,
    reltime,
    update_note,
)

if TYPE_CHECKING:
    from ankiwanikanisync.collection import WKCard, WKCollection, WKNote

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


@forward_args(reltime)
def ts(*args, **kwargs):
    return int(reltime(*args, **kwargs).timestamp())


@pytest.mark.asyncio
async def test_should_sync_upstream(
    revlog_mock: MockRevlog,
    session_mock: SubSession,
    subtests: pytest.Subtests,
    wk_col: WKCollection,
):
    kanji1 = session_mock.add_subject("kanji")
    subject = cast(WKSubject, kanji1)
    await lazy.sync.do_sync()
    note = get_note(kanji1)

    assignment = session_mock.add_assignment(subject_id=kanji1["id"], srs_stage=0)
    data = assignment["data"]

    def check(as_of: datetime = reltime()):
        return lazy.sync.SyncOp().should_sync_upstream(
            get_note(kanji1), lazy.sync.Assignment(assignment, subject), as_of
        )

    Reason = lazy.sync.Reason

    with subtests.test("Card is new"):
        revlog_mock.add_entry(note, button_chosen=3, time=ts(days=-1))
        assert check() is None
        revlog_mock.clear_entries(note)

    for card in note.cards():
        make_card_review(card, ivl=1)

    with subtests.test("No local reviews"):
        assert check() is None

    with subtests.test("Local failing reviews, srs_level=0"):
        revlog_mock.add_entry(note, button_chosen=1, time=ts(days=-2))
        assert check() is None

    with subtests.test("Local failing and passing reviews, srs_level=0"):
        timestamp = ts(days=-1)
        revlog_mock.add_entry(note, button_chosen=3, time=timestamp)
        revlog_mock.add_entry(note.cards()[0], button_chosen=1, time=ts(days=-1.5))
        revlog_mock.add_entry(note, button_chosen=3, time=ts(days=-3))
        assert check() == {
            "Meaning": 2,
            "Reading": 1,
            "timestamp": timestamp,
            "reason": Reason.LAST_REVIEW_AFTER_WK_AVAILABLE,
        }

    data["srs_stage"] = 7
    data["available_at"] = iso_reltime(days=-1)
    with subtests.test("Local review after available_at", srs_stage=data["srs_stage"]):
        timestamp = ts(days=0)
        revlog_mock.clear_entries(note)
        revlog_mock.add_entry(note, button_chosen=3, time=timestamp)

        assert check() == {
            "Meaning": 0,
            "Reading": 0,
            "timestamp": timestamp,
            "reason": Reason.LAST_REVIEW_AFTER_WK_AVAILABLE,
        }

    timestamp = ts(days=-2)
    with subtests.test("Local review before available_at", srs_stage=data["srs_stage"]):
        revlog_mock.clear_entries(note)
        revlog_mock.add_entry(note, button_chosen=3, time=timestamp)

        # Our next review would come before WaniKani's next review at the
        # current interval, so we should not submit.
        assert check() is None

    data["srs_stage"] = 1
    with subtests.test("Local review before available_at", srs_stage=data["srs_stage"]):
        revlog_mock.clear_entries(note)
        revlog_mock.add_entry(note, button_chosen=3, time=timestamp)

        # Our next review would come after WaniKani's next review, so we
        # should submit.
        assert check() == {
            "Meaning": 0,
            "Reading": 0,
            "timestamp": 0,
            "reason": Reason.NEXT_ANKI_DUE_AFTER_NEXT_WK_DUE,
        }

    data["srs_stage"] = 3
    with subtests.test("Local review before available_at", srs_stage=data["srs_stage"]):
        revlog_mock.clear_entries(note)
        revlog_mock.add_entry(note, button_chosen=3, time=timestamp)

        assert check() == {
            "Meaning": 0,
            "Reading": 0,
            "timestamp": 0,
            "reason": Reason.SUBSEQUENT_ANKI_DUE_AFTER_NEXT_WK_DUE,
        }

    for card in note.cards():
        card.type = CARD_TYPE_LRN
        card.queue = QUEUE_TYPE_LRN
        wk_col.col.update_card(card)

    data["srs_stage"] = 1
    with subtests.test("Card is Learning", srs_stage=data["srs_stage"]):
        revlog_mock.clear_entries(note)
        revlog_mock.add_entry(note, button_chosen=3, time=timestamp)

        assert check() is None


@dataclass(init=False)
class Req:
    method: str
    path: str

    def __init__(
        self,
        request: Request | None = None,
        /,
        method: str | None = None,
        path: str | None = None,
    ):
        if request:
            self.method = request.method
            self.path = request.path.removeprefix("/v2/")
        else:
            assert method and path
            self.method = method
            self.path = path


@dataclass(init=False)
class StartReq(Req):
    id: int

    def __init__(self, request: Request | None = None, /, id: int | None = None):
        if request:
            super().__init__(request)

            match = MockReviews.START_URL_RE.search(self.path)
            assert match
            self.id = int(match.group(1))
        else:
            super().__init__(method="PUT", path=f"assignments/{id}/start")

            assert id is not None
            self.id = id


@dataclass(init=False)
class ReviewReq(Req):
    json: WKReviewData

    def __init__(
        self, request: Request | None = None, /, json: WKReviewData | None = None
    ):
        if request:
            super().__init__(request)

            self.json = request.json()
        else:
            super().__init__(method="POST", path="reviews")

            assert json
            self.json = json


class MockReviews:
    START_URL_RE: Final = re.compile(r"^assignments/(\d+)/start")

    def __init__(self, session_mock: SubSession):
        self.session_mock = session_mock
        self.requests = list[Req]()

        session_mock.put(self.START_URL_RE, json=self.handle_start)
        session_mock.post("reviews", json=self.handle_review)

    def handle_start(self, request: Request, context: Context) -> WKAssignment:
        req = StartReq(request)

        assignment = self.session_mock.assignments[req.id]

        assert not assignment["data"]["started_at"]
        assignment["data"]["started_at"] = iso_reltime()
        assignment["data"]["srs_stage"] = 1
        assignment["data"]["available_at"] = iso_reltime(hours=4)

        self.requests.append(req)
        return assignment

    def handle_review(self, request: Request, context: Context) -> object:
        self.requests.append(ReviewReq(request))
        return {}


@pytest.mark.asyncio
async def test_upstream_assignment(
    mocker: MockerFixture,
    revlog_mock: MockRevlog,
    session_mock: SubSession,
    subtests: pytest.Subtests,
    wk_col: WKCollection,
):
    reviews_mock = MockReviews(session_mock)
    submit_reviews_at_mock = mocker.patch.object(lazy.timers, "submit_reviews_at")

    kanji1 = session_mock.add_subject("kanji")
    radical1 = session_mock.add_subject("radical")
    await lazy.sync.do_sync()
    note = get_note(kanji1)

    kanji1_assignment = session_mock.add_assignment(
        subject_id=kanji1["id"], srs_stage=0, started_at=None, available_at=None
    )
    assignment = kanji1_assignment
    data = assignment["data"]

    srs = lazy.wk.get_srs(kanji1["data"]["spaced_repetition_system_id"])

    for card in note.cards():
        make_card_review(card, ivl=1)

    async def upstream[T: WKSubjectDataBase](subj: WKSubject[T]):
        op = lazy.sync.SyncOp()
        with patch.object(op, "upstream_available_assignments_op") as mock:
            await op.upstream_review_op(get_note(subj))
            await pending_ops_complete()
            return mock.mock_calls

    @contextmanager
    def subtest(*args, **kwargs):
        with subtests.test(*args, **kwargs):
            yield
        reviews_mock.requests.clear()
        submit_reviews_at_mock.reset_mock()
        lazy.timers.stop_timers()

    with subtest("No submission"):
        res = await upstream(kanji1)
        assert res == []

        assert get_note(kanji1)["last_upstream_sync_time"] == ""

        assert reviews_mock.requests == []
        assert not submit_reviews_at_mock.called

    dt = reltime()
    revlog_mock.add_entry(note.cards()[0], button_chosen=1, time=ts(minutes=-10))
    revlog_mock.add_entry(note, button_chosen=3, time=int(dt.timestamp()))

    with subtest("Start new assignment"):
        res = await upstream(kanji1)
        assert res == []

        assert get_note(kanji1)["last_upstream_sync_time"] == approx_reltime()

        assert reviews_mock.requests == [StartReq(id=assignment["id"])]
        submit_reviews_at_mock.assert_called_once_with(approx_reltime(hours=4))

    data["available_at"] = iso_reltime(days=-1)
    review = WKReviewData(
        review={
            "assignment_id": assignment["id"],
            "incorrect_meaning_answers": 1,
            "incorrect_reading_answers": 0,
            "created_at": cast(str, ApproxDatetime(dt)),
        }
    )

    with subtest("Submit kanji review", might_guru=False):
        res = await upstream(kanji1)
        assert res == []

        assert get_note(kanji1)["last_upstream_sync_time"] == approx_reltime()

        assert reviews_mock.requests == [ReviewReq(json=review)]
        assert not submit_reviews_at_mock.called

    with subtest("Submit kanji review", might_guru=True):
        data["srs_stage"] = srs.passing_stage_position - 1

        res = await upstream(kanji1)
        assert res == [call(lessons=True, reviews=False)]

        assert get_note(kanji1)["last_upstream_sync_time"] == approx_reltime()

        assert reviews_mock.requests == [ReviewReq(json=review)]
        assert not submit_reviews_at_mock.called

    note = get_note(radical1)
    for card in note.cards():
        make_card_review(card, ivl=1)

    radical1_assignment = session_mock.add_assignment(
        subject_id=radical1["id"], srs_stage=1, available_at=iso_reltime(hours=-1)
    )
    assignment = radical1_assignment
    data = assignment["data"]

    revlog_mock.add_entry(note.cards()[0], button_chosen=1, time=ts(minutes=-10))
    revlog_mock.add_entry(note, button_chosen=3, time=int(dt.timestamp()))

    review = WKReviewData(
        review={
            "assignment_id": assignment["id"],
            "incorrect_meaning_answers": 1,
            "incorrect_reading_answers": 0,
            "created_at": cast(str, ApproxDatetime(dt)),
        }
    )

    with subtest("Submit radical review", might_guru=False):
        res = await upstream(radical1)
        assert res == []

        assert get_note(radical1)["last_upstream_sync_time"] == approx_reltime()

        assert reviews_mock.requests == [ReviewReq(json=review)]
        assert not submit_reviews_at_mock.called

    kanji1_assignment["data"]["started_at"] = None
    kanji1_assignment["data"]["available_at"] = None
    with subtest("Submit available reviews"):
        await lazy.sync.SyncOp().upstream_available_assignments_op(
            reviews=True, lessons=True
        )

        assert reviews_mock.requests == [
            StartReq(id=kanji1_assignment["id"]),
            ReviewReq(json=review),
        ]
        submit_reviews_at_mock.assert_called_once_with(approx_reltime(hours=4))


@pytest.mark.asyncio
async def test_maybe_sync_downstream(
    mocker: MockerFixture,
    revlog_mock: MockRevlog,
    session_mock: SubSession,
    subtests: pytest.Subtests,
    wk_col: WKCollection,
):
    kanji1 = session_mock.add_subject("kanji")
    subject = cast(WKSubject, kanji1)
    await lazy.sync.do_sync()
    note = get_note(kanji1)

    kanji1_assignment = session_mock.add_assignment(
        subject_id=kanji1["id"],
        srs_stage=4,
    )
    assignment = kanji1_assignment
    data = assignment["data"]

    def attrs(card: WKCard) -> dict[str, Any]:
        import anki.consts as C

        res = dict[str, Any]()
        match card.type:
            case C.CARD_TYPE_NEW:
                assert card.queue == C.QUEUE_TYPE_NEW
                res["type"] = "new"
                res["due"] = card.due
            case C.CARD_TYPE_LRN:
                assert card.queue == C.QUEUE_TYPE_LRN
                res["type"] = "learn"
                res["due"] = datetime.fromtimestamp(card.due).astimezone()
            case C.CARD_TYPE_REV:
                assert card.queue == C.QUEUE_TYPE_REV
                res["type"] = "review"
                res["due"] = reltime(days=card.due)

        res["ivl"] = card.ivl
        return res

    class Result(NamedTuple):
        card: WKCard
        changed: bool

    def check(note: WKNote):
        card = note.cards()[0]
        changed = lazy.sync.SyncOp().maybe_sync_downstream(
            card, lazy.sync.Assignment(assignment, subject)
        )
        return Result(card, changed)

    assignment["data_updated_at"] = iso_reltime()
    data["available_at"] = iso_reltime(days=1)
    make_card_learn(note, due=reltime(minutes=10))
    with subtests.test("LRN->REV"):
        res = check(note)
        assert res.changed
        assert attrs(res.card) >= PartialDict({
            "type": "review",
            "ivl": 2,
            "due": approx_reltime(days=1),
        })

    @contextmanager
    def checksync(msg: str, changed: bool):
        with subtests.test(msg):
            assignment["data_updated_at"] = iso_reltime()
            data["available_at"] = iso_reltime(days=1)
            make_card_learn(note, due=reltime(minutes=10))
            yield
            res = check(note)
            assert res.changed == changed

    with checksync("No WK reviews", changed=False):
        data["available_at"] = None

    last_upstream_sync = iso_reltime(days=-2)
    with checksync("Last sync before last review and last changed", changed=True):
        update_note(note, last_upstream_sync_time=last_upstream_sync)

    with checksync("No WK reviews", changed=False):
        data["available_at"] = None

    with checksync("WK reviewed before last sync", changed=False):
        data["available_at"] = iso_reltime(days=-1)

    with checksync("WK last updated before last sync", changed=False):
        assignment["data_updated_at"] = iso_reltime(days=-2)

    assignment["data_updated_at"] = iso_reltime()

    with subtests.test("NEW->LRN"):
        data["available_at"] = iso_reltime(hours=4)
        data["srs_stage"] = 1
        make_card_new(note)

        res = check(note)
        assert res.changed
        assert attrs(res.card) >= PartialDict({
            "type": "learn",
            "due": approx_reltime(hours=4),
        })

    with subtests.test("NEW->REV"):
        data["available_at"] = iso_reltime(days=1)
        data["srs_stage"] = 4
        make_card_new(note)

        res = check(note)
        assert res.changed
        assert attrs(res.card) >= PartialDict({
            "type": "review",
            "ivl": 2,
            "due": approx_reltime(days=1),
        })

    with subtests.test("LRN->REV"):
        data["available_at"] = iso_reltime(days=1)
        data["srs_stage"] = 4
        make_card_learn(note, due=reltime(hours=1))

        res = check(note)
        assert res.changed
        assert attrs(res.card) >= PartialDict({
            "type": "review",
            "ivl": 2,
            "due": approx_reltime(days=1),
        })

    with subtests.test("REV->REV greater interval"):
        data["available_at"] = iso_reltime(days=1)
        data["srs_stage"] = 4
        make_card_review(note, ivl=1, due=4)

        res = check(note)
        assert res.changed
        assert attrs(res.card) >= PartialDict({
            "type": "review",
            "ivl": 2,
            "due": approx_reltime(days=4),
        })

    with subtests.test("REV->REV greater due date"):
        data["available_at"] = iso_reltime(days=4)
        data["srs_stage"] = 4
        make_card_review(note, ivl=4, due=1)

        res = check(note)
        assert res.changed
        assert attrs(res.card) >= PartialDict({
            "type": "review",
            "ivl": 4,
            "due": approx_reltime(days=4),
        })

    with subtests.test("REV->REV no changes"):
        data["available_at"] = iso_reltime(days=1)
        data["srs_stage"] = 4
        make_card_review(note, ivl=4, due=4)

        res = check(note)
        assert not res.changed
        assert attrs(res.card) >= PartialDict({
            "type": "review",
            "ivl": 4,
            "due": approx_reltime(days=4),
        })

    with subtests.test("REV!->LRN"):
        data["available_at"] = iso_reltime(hours=4)
        data["srs_stage"] = 1
        make_card_review(note, ivl=1, due=0)

        res = check(note)
        assert not res.changed
        assert attrs(res.card) >= PartialDict({
            "type": "review",
            "ivl": 1,
            "due": approx_reltime(days=0),
        })

    with subtests.test("update_intervals"):
        lazy.config._last_due_sync = iso_reltime(days=-4)

        data["available_at"] = iso_reltime(days=4)
        data["srs_stage"] = 4
        make_card_review(note, ivl=1, due=1)

        await lazy.sync.SyncOp().update_intervals()

        card = get_note(kanji1).cards()[0]
        assert attrs(card) >= PartialDict({
            "type": "review",
            "ivl": 2,
            "due": approx_reltime(days=4),
        })
