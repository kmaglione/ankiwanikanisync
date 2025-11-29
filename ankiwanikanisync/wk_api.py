import urllib.parse
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime, timedelta
from time import sleep
from typing import (
    Any,
    Final,
    Literal,
    NotRequired,
    TypedDict,
    TypeGuard,
    overload,
)

import requests
from aqt import mw
from pyrate_limiter import Duration, Limiter, Rate
from requests.adapters import HTTPAdapter, Retry

from .config import config

type AssignmentID = int
type DateString = str
type SRSID = int
type SubjectId = int
type SubjectType = Literal["kana_vocabulary", "kanji", "radical", "vocabulary"]
type WKLevel = int


# FIXME: Ideally, these should all be protocols that actually validate the data
# that we receive from the server.
class WKResponse(TypedDict):
    object: str
    url: str
    data_updated_at: None | DateString


class WKMeaning(TypedDict):
    meaning: str
    primary: bool
    accepted_answer: bool


class WKAuxMeaning(TypedDict):
    meaning: str
    type: Literal["whitelist", "blacklist"]


class WKReading(TypedDict):
    reading: str
    primary: bool
    accepted_answer: bool
    type: Literal["kunyomi", "nanori", "onyomi"]


class WKContextSentence(TypedDict):
    en: str
    ja: str


class WKAudioMetadata(TypedDict):
    gender: Literal["male", "female"]
    source_id: int
    pronunciation: str
    voice_actor_id: int
    voice_actor_name: str
    voice_description: str


class WKAudio(TypedDict):
    url: str
    content_type: str
    metadata: WKAudioMetadata


class WKSubjectDataBase(TypedDict):
    auxiliary_meanings: Sequence[WKAuxMeaning]
    characters: str
    created_at: DateString
    document_url: str
    hidden_at: None | DateString
    lesson_position: int
    level: WKLevel
    meaning_mnemonic: str
    meanings: Sequence[WKMeaning]
    slug: str
    spaced_repetition_system_id: SRSID


class WKReadable(TypedDict):
    readings: Sequence[WKReading]


class WKComponentData(WKSubjectDataBase):
    amalgamation_subject_ids: Sequence[SubjectId]


class WKRadicalData(WKComponentData):
    character_images: Sequence[dict]


class WKAmalgumData(TypedDict):
    component_subject_ids: Sequence[SubjectId]


class WKKanjiData(WKAmalgumData, WKComponentData, WKReadable):
    meaning_hint: None | str
    reading_hint: None | str
    reading_mnemonic: str
    visually_similar_subject_ids: Sequence[SubjectId]


class WKVocabBase(WKSubjectDataBase):
    context_sentences: Sequence[WKContextSentence]
    parts_of_speech: Sequence[str]
    pronunciation_audios: Sequence[WKAudio]


class WKVocabData(WKAmalgumData, WKVocabBase, WKReadable):
    reading_mnemonic: str


class WKKanaVocabData(WKVocabBase):
    pass


type WKSubjectData = (
    WKKanaVocabData | WKKanjiData | WKRadicalData | WKSubjectDataBase | WKVocabData
)


def is_WKAmalgumData(data: WKSubjectData) -> TypeGuard[WKAmalgumData]:
    return "component_subject_ids" in data


def is_WKComponentData(data: WKSubjectData) -> TypeGuard[WKComponentData]:
    return "amalgamation_subject_ids" in data


def is_WKKanjiData(data: WKSubjectData) -> TypeGuard[WKKanjiData]:
    return "visually_similar_subject_ids" in data


def is_WKRadicalData(data: WKSubjectData) -> TypeGuard[WKRadicalData]:
    return "character_images" in data


def is_WKReadable(data: WKSubjectDataBase) -> TypeGuard[WKReadable]:
    return "readings" in data


def is_WKVocabBase(data: WKSubjectData) -> TypeGuard[WKVocabBase]:
    return "context_sentences" in data


class WKSubject(WKResponse):
    id: int
    data: WKSubjectData


class WKSubjectsResponse(WKResponse):
    data: Sequence[WKSubject]
    total_count: int


class WKAssignmentData(TypedDict):
    available_at: None | DateString
    burned_at: None | DateString
    created_at: DateString
    hidden: bool
    passed_at: None | DateString
    resurrected_at: None | DateString
    srs_stage: int
    started_at: None | DateString
    subject_id: int
    subject_type: SubjectType
    unlocked_at: None | DateString


class WKAssignment(WKResponse):
    id: AssignmentID
    data: WKAssignmentData


class WKAssignmentsResponse(WKResponse):
    data: Sequence[WKAssignment]
    total_count: int


class WKStudyMaterialData(TypedDict):
    created_at: DateString
    hidden: bool
    meaning_note: str
    meaning_synonyms: Sequence[str]
    reading_note: str
    subject_id: int
    subject_type: SubjectType


class WKStudyMaterial(WKResponse):
    data: WKStudyMaterialData


class WKStudyMaterialsResponse(WKResponse):
    data: Sequence[WKStudyMaterial]
    total_count: int


class WKSubscription(TypedDict):
    active: bool
    max_level_granted: WKLevel
    period_ends_at: None | DateString
    type: Literal["free", "recurring", "lifetime"]


class WKPreferences(TypedDict):
    default_voice_actor_id: int
    extra_study_autoplay_audio: bool
    lessons_autoplay_audio: bool
    lessons_batch_size: int
    lessons_presentation_order: Literal["ascending_level_then_subject"]
    reviews_autoplay_audio: bool
    reviews_display_srs_indicator: bool
    reviews_presentation_order: Literal["shuffled", "lower_levels_first"]


class WKUserData(TypedDict):
    current_vacation_started_at: DateString | None
    level: WKLevel
    preferences: WKPreferences
    profile_url: str
    started_at: DateString
    subscription: WKSubscription
    username: str


class WKUser(WKResponse):
    data: WKUserData


class WKSRSStageBase(TypedDict):
    position: int


class WKSRSStageEmpty(WKSRSStageBase):
    interval: None
    interval_unit: None


class WKSRSStageNonEmpty(WKSRSStageBase):
    interval: int
    interval_unit: Literal[
        "milliseconds", "seconds", "minutes", "hours", "days", "weeks"
    ]


type WKSpacedRepetitionSystemStage = WKSRSStageNonEmpty | WKSRSStageEmpty


class WKSpacedRepetitionSystemData(TypedDict):
    burning_stage_position: int
    created_at: DateString
    description: str
    name: str
    passing_stage_position: int
    stages: Sequence[WKSpacedRepetitionSystemStage]
    starting_stage_position: int
    unlocking_stage_position: int


class WKSpacedRepetitionSystem(WKResponse):
    data: WKSpacedRepetitionSystemData


class WKAssignmentsQuery(TypedDict, total=False):
    available_after: DateString | datetime
    available_before: DateString | datetime
    burned: bool
    hidden: bool
    ids: Iterable[AssignmentID]
    immediately_available_for_lessons: bool
    immediately_available_for_review: bool
    in_review: bool
    levels: Iterable[WKLevel]
    srs_stages: Iterable[int]
    started: bool
    subject_ids: Iterable[SubjectId]
    subject_types: Iterable[SubjectType]
    unlocked: bool
    updated_after: DateString | datetime


class WKStudyMaterialsQuery(TypedDict, total=False):
    hidden: bool
    ids: Iterable[int]
    subject_ids: Iterable[int]
    subject_types: Iterable[SubjectType]
    updated_after: DateString | datetime


class WKSubjectsQuery(TypedDict, total=False):
    ids: Iterable[SubjectId]
    types: Iterable[str]
    slugs: Iterable[str]
    levels: Iterable[WKLevel]
    hidden: bool
    updated_after: DateString | datetime


class WKReviewDataReview(TypedDict):
    # Note: One of the following must be included, but including both causes
    # an error.
    assignment_id: NotRequired[AssignmentID]
    subject_id: NotRequired[SubjectId]

    incorrect_meaning_answers: int
    incorrect_reading_answers: int
    created_at: NotRequired[DateString]


class WKReviewData(TypedDict):
    review: WKReviewDataReview


WK_API_BASE: Final = "https://api.wanikani.com/v2"
WK_REV: Final = "20170710"


class WKSRSStage(object):
    class UnitsDict(TypedDict):
        milliseconds: timedelta
        seconds: timedelta
        minutes: timedelta
        hours: timedelta
        days: timedelta
        weeks: timedelta

    UNITS: Final = UnitsDict(
        milliseconds=timedelta(microseconds=1000),
        seconds=timedelta(seconds=1),
        minutes=timedelta(minutes=1),
        hours=timedelta(hours=1),
        days=timedelta(days=1),
        weeks=timedelta(weeks=1),
    )
    interval: timedelta | None = None

    def __init__(self, data: WKSpacedRepetitionSystemStage) -> None:
        if data["interval"] is not None:
            self.interval = data["interval"] * self.UNITS[data["interval_unit"]]
        self.position = data["position"]


class WKSRS(object):
    def __init__(self, data: WKSpacedRepetitionSystem):
        self.stages = list(map(WKSRSStage, data["data"]["stages"]))

        self.passing_stage_position = data["data"]["passing_stage_position"]


class WKReqCancelledException(Exception):
    pass


def param_to_str(val):
    if isinstance(val, str):
        return val
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, Iterable):
        return ",".join(map(param_to_str, val))
    return str(val)


class WKAPI:
    def __init__(self) -> None:
        self.limiter = Limiter(
            Rate(50, Duration.MINUTE), raise_when_fail=False, max_delay=250
        )
        self.session = requests.Session()
        self.session.mount(
            "https://", HTTPAdapter(max_retries=Retry(total=50, backoff_factor=0.5))
        )

        self.spaced_repetition_systems: dict[SRSID, WKSRS] = {}

    def _do_limit(self, name: str) -> bool:
        while not mw.progress.want_cancel():
            if self.limiter.try_acquire(name):
                return True
            assert self.limiter.max_delay
            sleep(self.limiter.max_delay / 1000)
        raise WKReqCancelledException("The request was cancelled.")

    def get_srs(self, srs_id: SRSID) -> WKSRS:
        if srs_id not in self.spaced_repetition_systems:
            self.spaced_repetition_systems[srs_id] = WKSRS(
                self.api_req("spaced_repetition_systems", str(srs_id))
            )
        return self.spaced_repetition_systems[srs_id]

    @overload
    def api_req(
        self,
        ep: Literal["review"],
        /,
        *,
        data: WKReviewData,
        full: bool = ...,
        timeout: int = ...,
    ) -> WKStudyMaterialsResponse: ...

    @overload
    def api_req(
        self,
        ep: Literal["study_materials"],
        /,
        query=...,
        *,
        full: bool = ...,
        timeout: int = ...,
    ) -> WKStudyMaterialsResponse: ...

    @overload
    def api_req(
        self,
        ep: Literal["assignments"],
        /,
        query=...,
        *,
        full: bool = ...,
        timeout: int = ...,
    ) -> WKAssignmentsResponse: ...

    @overload
    def api_req(
        self,
        ep: Literal["spaced_repetition_systems"],
        /,
        query: str,
        *,
        timeout: int = ...,
    ) -> WKSpacedRepetitionSystem: ...

    @overload
    def api_req(
        self,
        ep: Literal["subjects"],
        /,
        query: WKSubjectsQuery | None = ...,
        *,
        full: bool = ...,
        timeout: int = ...,
    ) -> WKSubjectsResponse: ...

    @overload
    def api_req(
        self,
        ep: Literal["subjects"],
        /,
        query: str,
        *,
        timeout: int = ...,
    ) -> WKSubject: ...

    @overload
    def api_req(
        self,
        ep: Literal["user"],
        /,
        *,
        data=...,
        put: bool = ...,
        timeout: int = ...,
    ) -> WKUser: ...

    @overload
    def api_req(
        self,
        ep: Any,
        /,
        query: None | str | Mapping[str, Any] = ...,
        *,
        full: bool = ...,
        data=...,
        put: bool = ...,
        timeout: int = ...,
    ) -> Any: ...

    def api_req(
        self,
        ep,
        /,
        query: None | str | Mapping[str, Any] = None,
        *,
        full: bool = True,
        data=None,
        put: bool = False,
        timeout: int = 5,
    ):
        api_key = config.WK_API_KEY
        if not api_key:
            raise Exception("No API Key!")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Wanikani-Revision": WK_REV,
        }

        self._do_limit(api_key)

        if isinstance(query, str):
            ep += f"/{query}"
        elif query is not None:
            ep += "?" + urllib.parse.urlencode(
                {key: param_to_str(val) for key, val in query.items()}
            )

        if data is not None:
            if put:
                res = self.session.put(
                    f"{WK_API_BASE}/{ep}",
                    headers=headers,
                    json=data,
                    timeout=timeout,
                )
            else:
                res = self.session.post(
                    f"{WK_API_BASE}/{ep}",
                    headers=headers,
                    json=data,
                    timeout=timeout,
                )
        else:
            res = self.session.get(
                f"{WK_API_BASE}/{ep}", headers=headers, timeout=timeout
            )
        res.raise_for_status()
        data = res.json()

        if full and "object" in data and data["object"] == "collection":
            next_url = data["pages"]["next_url"]
            while next_url:
                if not self._do_limit(api_key):
                    return None
                res = self.session.get(next_url, headers=headers, timeout=timeout)
                res.raise_for_status()
                new_data = res.json()

                data["data"] += new_data["data"]
                next_url = new_data["pages"]["next_url"]

        return data

    @overload
    def query(
        self,
        path: Literal["study_materials"],
        query: None | WKStudyMaterialsQuery = ...,
        *,
        full: bool = ...,
        timeout: int = ...,
    ) -> WKStudyMaterialsResponse: ...

    @overload
    def query(
        self,
        path: Literal["assignments"],
        query: None | WKAssignmentsQuery = ...,
        *,
        full: bool = ...,
        timeout: int = ...,
    ) -> WKAssignmentsResponse: ...

    @overload
    def query(
        self,
        path: Literal["subjects"],
        query: None | WKSubjectsQuery = ...,
        *,
        full: bool = ...,
        timeout: int = ...,
    ) -> WKSubjectsResponse: ...

    @overload
    def query(self, path: Literal["user"], *, timeout: int = ...) -> WKUser: ...

    def query(
        self,
        path: Literal["study_materials", "assignments", "subjects", "user"],
        query=None,
        *,
        full: bool = True,
        timeout: int = 5,
    ):
        return self.api_req(path, query=query, full=full, timeout=timeout)

    def post(
        self,
        path: Literal["reviews"],
        data: WKReviewData,
        *,
        timeout: int = 5,
    ) -> WKSubjectsResponse:
        return self.api_req(path, data=data, timeout=timeout)


wk = WKAPI()
