from __future__ import annotations

import re
import threading
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Final, Iterable, Literal, Unpack, cast, overload
from unittest import mock

if TYPE_CHECKING:
    from requests_mock.request import Request
    from requests_mock.response import Context

from ankiwanikanisync import types

from ..utils import iso_reltime, read_fixture_json
from ..wk_session import ResponseDict, SessionMock

base_session: BaseSession | None = None
_next_id: int = 0


def get_id() -> int:
    global _next_id
    _next_id += 1
    return _next_id


def dt(dtstring: str) -> datetime:
    return datetime.fromisoformat(dtstring)


def get_latest_updated(objs: Iterable[types.WKResponse]) -> datetime | None:
    updated = None
    for obj in objs:
        if obj["data_updated_at"]:
            timestamp = dt(obj["data_updated_at"])
            if not updated or timestamp > updated:  # type: ignore[unreachable]
                updated = timestamp
    return updated


def return_if_exists[T](id_: int, objs: dict[int, T], context: Context) -> T | None:
    if id_ in objs:
        return objs[id_]
    context.status_code = 404
    context.reason = "Not found"
    return None


class Responder[T]:
    def __init__(self, objs: dict[int, T]):
        self.objs = objs

    def __call__(self, request: Request, context: Context) -> T | None:
        id_ = int(request.path.split("/")[-1])
        return return_if_exists(id_, self.objs, context)


class BaseSession(SessionMock):
    BASE_RESPONSES: Final[dict[str, ResponseDict]] = {
        "spaced_repetition_systems/1": {
            "json": read_fixture_json("srs_1.json"),
        },
        "user": {
            "json": read_fixture_json("user.json"),
        },
    }

    def __init__(self):
        super().__init__(real_http=False)

        from ankiwanikanisync.importer import Downloader
        from ankiwanikanisync.wk_api import wk

        try_acquire = mock.patch.object(wk.limiter, "try_acquire").__enter__()
        try_acquire.return_value = True

        try_acquire2 = mock.patch.object(Downloader.limiter, "try_acquire").__enter__()
        try_acquire2.return_value = True

        self.audio_lock = threading.Lock()

        self.assignments = dict[int, types.WKAssignment]()
        self.study_materials = dict[int, types.WKStudyMaterial]()
        self.subjects = dict[int, types.WKSubject]()

        self._add_responder("assignments", self.assignments)
        self._add_responder("study_materials", self.study_materials)
        self._add_responder("subjects", self.subjects)

        self.get(re.compile(r"^audio/"), text=self._respond_audio)

        self.get("assignments", json=self._respond_assignments)
        self.get("study_materials", json=self._respond_study_materials)
        self.get("subjects", json=self._respond_subjects)

        for url, resp in self.BASE_RESPONSES.items():
            self.get(url, **resp)

    def _add_responder[U](self, obj_type: str, objs: dict[int, U]) -> None:
        self.get(re.compile(f"^{obj_type}/\\d+"), json=Responder(objs))

    def _respond_audio(self, request: Request, context: Context) -> str:
        # Hold a lock to allow tests to delay requests from the audio
        # downloader
        with self.audio_lock:
            return request.url

    def _respond_assignments(self, request: Request, context: Context) -> object:
        now = datetime.now(timezone.utc)

        results: Iterable[types.WKAssignment] = self.assignments.values()

        if after := request.qs.get("available_after"):
            after_dt = dt(after[0])
            results = (
                res
                for res in results
                if res["data"]["available_at"]
                and dt(res["data"]["available_at"]) >= after_dt
            )

        if before := request.qs.get("available_before"):
            before_dt = dt(before[0])
            results = (
                res
                for res in results
                if res["data"]["available_at"]
                and dt(res["data"]["available_at"]) <= before_dt
            )

        if after := request.qs.get("updated_after"):
            after_dt = dt(after[0])
            results = (
                res
                for res in results
                if res["data_updated_at"] and dt(res["data_updated_at"]) > after_dt
            )

        if ids_ := request.qs.get("ids"):
            ids = list(map(int, ids_[0].split(",")))
            results = (res for res in results if res["id"] in ids)

        if subj_ids_ := request.qs.get("subject_ids"):
            subj_ids = list(map(int, subj_ids_[0].split(",")))
            results = (res for res in results if res["data"]["subject_id"] in subj_ids)

        if subj_types_ := request.qs.get("subject_types"):
            subj_types = subj_types_[0].split(",")
            results = (
                res for res in results if res["data"]["subject_type"] in subj_types
            )

        if immed_reviewable := request.qs.get("immediately_available_for_review"):
            reviewable = immed_reviewable[0] == "true"
            results = (
                res
                for res in results
                if (
                    res["data"]["available_at"]
                    and dt(res["data"]["available_at"]) <= now
                )
                == reviewable
            )

        if immed_learnable := request.qs.get("immediately_available_for_lessons"):
            learnable = immed_learnable[0] == "true"
            results = (
                res
                for res in results
                if bool(res["data"]["unlocked_at"] and not res["data"]["started_at"])
                == learnable
            )

        if hidden_q := request.qs.get("hidden"):
            hidden = hidden_q[0] == "true"
            results = (res for res in results if res["data"]["hidden"] == hidden)

        if unlocked_q := request.qs.get("unlocked"):
            unlocked = unlocked_q[0] == "true"
            results = (
                res for res in results if bool(res["data"]["unlocked_at"]) == unlocked
            )

        for key in (
            "burned",
            "in_review",
            "levels",
            "srs_stages",
            "started",
        ):
            if key in request.qs:
                raise NotImplementedError(f"Unsupported query param: {key}")

        objects = list(results)
        updated = get_latest_updated(objects)

        return types.WKAssignmentsResponse(
            object="collection",
            url=request.url,
            pages={
                "per_page": 1000000,
                "next_url": None,
                "previous_url": None,
            },
            data_updated_at=updated.isoformat() if updated else None,
            total_count=len(objects),
            data=objects,
        )

    def _respond_study_materials(self, request: Request, context: Context) -> object:
        results: Iterable[types.WKStudyMaterial] = self.study_materials.values()

        if after := request.qs.get("updated_after"):
            after_dt = dt(after[0])
            results = (
                res
                for res in results
                if res["data_updated_at"] and dt(res["data_updated_at"]) > after_dt
            )

        if ids_ := request.qs.get("ids"):
            ids = list(map(int, ids_[0].split(",")))
            results = (res for res in results if res["id"] in ids)

        if subj_ids_ := request.qs.get("subject_ids"):
            subj_ids = list(map(int, subj_ids_[0].split(",")))
            results = (res for res in results if res["data"]["subject_id"] in subj_ids)

        if subj_types_ := request.qs.get("subject_types"):
            subj_types = subj_types_[0].split(",")
            results = (
                res for res in results if res["data"]["subject_type"] in subj_types
            )

        objects = list(results)
        updated = get_latest_updated(objects)

        return types.WKStudyMaterialsResponse(
            object="collection",
            url=request.url,
            pages={
                "per_page": 1000000,
                "next_url": None,
                "previous_url": None,
            },
            data_updated_at=updated.isoformat() if updated else None,
            total_count=len(objects),
            data=objects,
        )

    def _respond_subjects(self, request: Request, context: Context) -> object:
        results: Iterable[types.WKSubject] = self.subjects.values()

        if after := request.qs.get("updated_after"):
            after_dt = dt(after[0])
            results = (
                res
                for res in results
                if res["data_updated_at"] and dt(res["data_updated_at"]) > after_dt
            )

        if ids_ := request.qs.get("ids"):
            ids = list(map(int, ids_[0].split(",")))
            results = (res for res in results if res["id"] in ids)

        if levels_ := request.qs.get("levels"):
            levels = list(map(int, levels_[0].split(",")))
            results = (res for res in results if res["data"]["level"] in levels)

        if subj_types_ := request.qs.get("types"):
            subj_types = subj_types_[0].split(",")
            results = (res for res in results if res["object"] in subj_types)

        if hidden_q := request.qs.get("hidden"):
            hidden = hidden_q[0] == "true"
            results = (
                res
                for res in results
                if (res["data"]["hidden_at"] is not None) == hidden
            )

        if "slugs" in request.qs:
            raise NotImplementedError()

        objects = list(results)
        updated = get_latest_updated(objects)

        return types.WKSubjectsResponse(
            object="collection",
            url=request.url,
            pages={
                "per_page": 1000000,
                "next_url": None,
                "previous_url": None,
            },
            data_updated_at=updated.isoformat() if updated else None,
            total_count=len(objects),
            data=objects,
        )

    def sub_session(self) -> SubSession:
        return SubSession(self)


def make_audio(pronunciation: str) -> list[types.WKAudio]:
    res = list[types.WKAudio]()
    voices: list[types.WKAudioMetadataPartial] = [
        {
            "gender": "female",
            "voice_actor_id": 1,
            "voice_actor_name": "Kyoko",
            "voice_description": "Tokyo accent",
        },
        {
            "gender": "male",
            "voice_actor_id": 2,
            "voice_actor_name": "Kenichi",
            "voice_description": "Tokyo accent",
        },
    ]
    for voice in voices:
        source_id = get_id()
        for format in ("audio/mpeg", "audio/webm"):
            res.append(
                types.WKAudio(
                    url=f"https://api.wanikani.com/v2/audio/{uuid.uuid4().hex}",
                    content_type=format,
                    metadata=cast(
                        types.WKAudioMetadata,
                        {
                            "source_id": source_id,
                            "pronunciation": pronunciation,
                            **voice,
                        },
                    ),
                )
            )
    return res


class SubSession(SessionMock):
    def __init__(self, base_session: BaseSession):
        super().__init__(real_http=True)

        self.base_session = base_session

        self.assignments = dict[int, types.WKAssignment]()
        self.study_materials = dict[int, types.WKStudyMaterial]()
        self.subjects = dict[int, types.WKSubject]()

    def __exit__(self, exc_type: type, exc_value, traceback) -> None:
        super().__exit__(exc_type, exc_value, traceback)

        for attr in ("assignments", "study_materials", "subjects"):
            ours: dict = getattr(self, attr)
            theirs: dict = getattr(self.base_session, attr)
            for key in ours:
                del theirs[key]

    def add_assignment(
        self, **partial_data: Unpack[types.WKAssignmentDataPartial]
    ) -> types.WKAssignment:
        id_ = get_id()
        data: types.WKAssignmentData = {
            "created_at": "2025-10-04T20:18:22.033650Z",
            "subject_id": 0,
            "subject_type": "vocabulary",
            "srs_stage": 7,
            "unlocked_at": "2025-10-04T20:18:22.030974Z",
            "started_at": "2025-10-04T20:45:04.075905Z",
            "passed_at": "2025-10-08T18:29:27.110119Z",
            "burned_at": None,
            "available_at": "2025-12-21T20:00:00.000000Z",
            "resurrected_at": None,
            "hidden": False,
        }
        data.update(partial_data)
        if "subject_id" in partial_data and "subject_type" not in partial_data:
            data["subject_type"] = cast(
                types.SubjectType, self.subjects[data["subject_id"]]["object"]
            )

        assignment: types.WKAssignment = {
            "id": id_,
            "object": "assignment",
            "url": f"https://api.wanikani.com/v2/assignments/{id_}",
            "data_updated_at": iso_reltime(),
            "data": data,
        }
        self.assignments[id_] = assignment
        self.base_session.assignments[id_] = assignment
        return assignment

    def add_study_materials(
        self, **partial_data: Unpack[types.WKStudyMaterialDataPartial]
    ) -> types.WKStudyMaterial:
        id_ = get_id()
        data: types.WKStudyMaterialData = {
            "created_at": "2025-10-04T20:18:22.033650Z",
            "hidden": False,
            "meaning_note": "",
            "meaning_synonyms": [],
            "reading_note": "",
            "subject_id": 0,
            "subject_type": "vocabulary",
        }
        data.update(partial_data)
        if "subject_id" in partial_data and "subject_type" not in partial_data:
            data["subject_type"] = cast(
                types.SubjectType, self.subjects[data["subject_id"]]["object"]
            )

        study_material: types.WKStudyMaterial = {
            "id": id_,
            "object": "study_material",
            "url": f"https://api.wanikani.com/v2/study_materials/{id_}",
            "data_updated_at": iso_reltime(),
            "data": data,
        }
        self.study_materials[id_] = study_material
        self.base_session.study_materials[id_] = study_material
        return study_material

    @overload
    def add_subject(
        self,
        type_: Literal["radical"],
        **partial_data: Unpack[types.WKRadicalDataPartial],
    ) -> types.WKSubject[types.WKRadicalData]: ...

    @overload
    def add_subject(
        self, type_: Literal["kanji"], **partial_data: Unpack[types.WKKanjiDataPartial]
    ) -> types.WKSubject[types.WKKanjiData]: ...

    @overload
    def add_subject(
        self,
        type_: Literal["vocabulary"],
        **partial_data: Unpack[types.WKVocabDataPartial],
    ) -> types.WKSubject[types.WKVocabData]: ...

    @overload
    def add_subject(
        self,
        type_: Literal["kana_vocabulary"],
        **partial_data: Unpack[types.WKKanaVocabDataPartial],
    ) -> types.WKSubject[types.WKKanaVocabData]: ...

    def add_subject(self, type_: types.SubjectType, **partial_data) -> Any:
        id_ = get_id()
        characters = partial_data.get("characters", "")
        slug = partial_data.get("slug", "")
        data = {
            "created_at": "2012-03-03T00:03:50.000000Z",
            "level": 4,
            "slug": characters,
            "hidden_at": None,
            "document_url": f"https://www.wanikani.com/{type_}/{characters or slug}",
            "characters": characters,
            "meanings": [
                {"meaning": "Foo", "primary": True, "accepted_answer": True},
                {"meaning": "Bar", "primary": False, "accepted_answer": True},
            ],
            "auxiliary_meanings": [
                {"meaning": "Baz", "type": "blacklist"},
                {"meaning": "Quux", "type": "whitelist"},
            ],
            "meaning_mnemonic": "Lorem ipsem",
            "lesson_position": 42,
            "spaced_repetition_system_id": 1,
        }
        if type_ == "kanji":
            data.update(
                types.WKKanjiDataPartial(
                    readings=[
                        {
                            "reading": "ふ",
                            "primary": True,
                            "accepted_answer": True,
                            "type": "onyomi",
                        }
                    ],
                    component_subject_ids=[],
                    reading_mnemonic="dolor sit amet",
                )
            )
        if type_ in ("kanji", "vocabulary"):
            data.update(types.WKAmalgumData(component_subject_ids=[]))
        if type_ == "vocabulary":
            data.update(
                types.WKVocabDataPartial(
                    readings=[
                        {"reading": "ふ", "primary": True, "accepted_answer": True}
                    ],
                    reading_mnemonic="Phasellus egestas purus in tristique sodales.",
                )
            )
        if type_ in ("kana_vocabulary", "vocabulary"):
            audios = list[types.WKAudio]()
            if "readings" in data:
                readings = cast(
                    list[types.WKReading],
                    partial_data.get("readings") or data["readings"],
                )
                for reading in readings:
                    audios.extend(make_audio(reading["reading"]))
            else:
                audios.extend(make_audio(cast(str, data["characters"])))

            data.update(
                types.WKVocabBasePartial(
                    context_sentences=[
                        {
                            "en": "Lorem ipsum dolor sit amet.",
                            "ja": "こんにちは、とても痛いですね。",
                        }
                    ],
                    parts_of_speech=["noun", "の adjective"],
                    pronunciation_audios=audios,
                )
            )
        data.update(partial_data)

        subject: types.WKSubject = {
            "id": id_,
            "object": type_,
            "url": f"https://api.wanikani.com/v2/subjects/{id_}",
            "data_updated_at": iso_reltime(),
            "data": cast(types.WKSubjectData, data),
        }
        self.subjects[id_] = subject
        self.base_session.subjects[id_] = subject
        return subject
