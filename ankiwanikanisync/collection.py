from __future__ import annotations

import operator
import time
from collections.abc import Iterable, Mapping, Sequence
from functools import reduce
from typing import Final, Literal, cast

from anki.cards import Card, CardId
from anki.collection import Collection, OpChangesWithCount, SearchNode
from anki.consts import (
    CARD_TYPE_LRN,
    CARD_TYPE_NEW,
    CARD_TYPE_REV,
    QUEUE_TYPE_LRN,
    QUEUE_TYPE_NEW,
    QUEUE_TYPE_SUSPENDED,
)
from anki.notes import Note, NoteId
from aqt import mw

from .config import config
from .utils import chunked, collection_op, compose, query_op, report_progress
from .wk_api import SubjectId

FieldName = Literal[
    "card_id",
    "sort_id",
    "components",
    "Level",
    "DocumentURL",
    "Characters",
    "Card_Type",
    "Word_Type",
    "Meaning",
    "Meaning_Mnemonic",
    "Meaning_Hint",
    "Meaning_Whitelist",
    "Meaning_Blacklist",
    "Reading",
    "Reading_Onyomi",
    "Reading_Kunyomi",
    "Reading_Nanori",
    "Reading_Whitelist",
    "Reading_Mnemonic",
    "Reading_Hint",
    "Comps",
    "Similar",
    "Found_in",
    "Context_Patterns",
    "Context_Sentences",
    "Audio",
    "Keisei",
    "last_upstream_sync_time",
    "raw_data",
]


# This is a fairly ugly hack for the sake of type checking. This class is
# never actually used, but Anki Note objects are presented to the type checker
# as instances of this class so that the validity of its dict keys can be
# checked.
class WKNote(Note):
    def __getitem__(  # type: ignore[empty-body]
        self,
        key: FieldName,  # type: ignore[override]
    ) -> str: ...

    def cards(self) -> list[WKCard]: ...  # type: ignore[empty-body,override]

    @staticmethod
    def cast(note: Note) -> WKNote:
        return cast(WKNote, note)


class WKCard(Card):
    def note(self, reload: bool = ...) -> WKNote: ...  # type: ignore[empty-body]

    @staticmethod
    def cast(card: Card) -> WKCard:
        return cast(WKCard, card)


def format_id(id_: SubjectId) -> str:
    """
    Formats a SubjectId as a fixed-with hexidecimal integer. Allows dependency
    list fields to be searched using simple substring queries without having
    to check for surrounding spaces or start/end of line.
    """
    return f"{id_:08x}"


def search_node(**kwargs: str) -> SearchNode:
    """
    Returns a SearchNode representing an exact string match query of the fields
    specified in the keyword arguments. If multiple keywords are provided,
    all fields must match.
    """
    return wk_col.col.group_searches(
        *(
            SearchNode(field=SearchNode.Field(field_name=key, text=val))
            for key, val in kwargs.items()
        )
    )


def card_is_guru(card: WKCard) -> bool:
    return card.type == CARD_TYPE_REV and card.ivl >= config.GURU_INTERVAL


def note_is_guru(note: WKNote) -> bool:
    return all(map(card_is_guru, note.cards()))


def note_is_wk(note: WKNote) -> bool:
    if note_type := note.note_type():
        return note_type["name"] == config.NOTE_TYPE_NAME
    return False


class WKCollection(object):
    CHUNK_SIZE: Final[int] = 256

    def __init__(self):
        assert mw.col
        self.col = mw.col

    def get_note(self, nid: NoteId) -> WKNote:
        return WKNote.cast(self.col.get_note(nid))

    def get_card(self, cid: CardId) -> WKCard:
        return WKCard.cast(self.col.get_card(cid))

    def _construct_query(
        self,
        args: Sequence[str | SearchNode],
        kwargs: Mapping[str, str],
    ) -> str:
        return self.col.build_search_string(
            SearchNode(note=config.NOTE_TYPE_NAME),
            *args,
            *(
                SearchNode(field=SearchNode.Field(field_name=key, text=val))
                for key, val in kwargs.items()
            ),
        )

    def find_cards(self, *args: str | SearchNode, **kwargs: str) -> Sequence[CardId]:
        """
        Finds cards of the WaniKani note type matching the given query
        parameters. Constructs an AND query which must match all of the given
        args.

        Positional arguments may be arbitrary search strings or SearchNodes.

        Keyword arguments match fields with the same name as the keyword which
        exactly match their string value, with the `search_node` helper
        function.
        """
        return self.col.find_cards(self._construct_query(args, kwargs))

    def find_notes(self, *args: str | SearchNode, **kwargs: str) -> Sequence[NoteId]:
        """
        Finds notes of the WaniKani note type matching the given query
        parameters. Arguments are handled in exactly the same manner as in
        the `find_cards` method.
        """
        return self.col.find_notes(self._construct_query(args, kwargs))

    def get_note_for_subject(self, subject_id: SubjectId) -> WKNote | None:
        """
        Returns the Note for the given WaniKani subject ID if it exits, or None
        if it does not.
        """
        if ids := self.find_notes(card_id=str(subject_id)):
            return self.get_note(ids[0])
        return None

    def find_notes_for_subjects(
        self, subject_ids: Sequence[SubjectId], update_progress: bool = False
    ) -> dict[SubjectId, WKNote]:
        """
        Finds Notes for the given WaniKani subject IDs, and returns a dict
        mapping SubjectIds to notes.

        When querying multiple subjects, this method should be strongly
        preferred to individual queries for each subject ID, since the latter
        is incredibly slow and inefficient.
        """
        notes = {}
        for i, chunk in chunked(subject_ids, self.CHUNK_SIZE):
            if update_progress:
                if mw.progress.want_cancel():
                    break

                report_progress(
                    f"Reading notes {i + 1}/{len(subject_ids)}...", i, len(subject_ids)
                )

            query = wk_col.col.group_searches(
                *(search_node(card_id=str(subj_id)) for subj_id in chunk),
                joiner="OR",
            )

            for note_id in self.find_notes(query):
                note = self.get_note(note_id)
                notes[int(note["card_id"])] = note

        return notes

    def find_cards_for_subjects(
        self, subject_ids: Sequence[SubjectId], update_progress: bool = False
    ) -> dict[SubjectId, list[WKCard]]:
        """
        Finds Cards for the given WaniKani subject IDs, and returns a dict
        mapping SubjectIds to a list of all of its related cards.

        When querying multiple subjects, this method should be strongly
        preferred to individual queries for each subject ID, since the latter
        is incredibly slow and inefficient.
        """

        cards: dict[SubjectId, list[WKCard]] = {}
        for i, chunk in chunked(subject_ids, self.CHUNK_SIZE):
            if update_progress:
                if mw.progress.want_cancel():
                    break

                report_progress(
                    f"Reading notes {i + 1}/{len(subject_ids)}...", i, len(subject_ids)
                )

            query = wk_col.col.group_searches(
                *(search_node(card_id=str(subj_id)) for subj_id in chunk),
                joiner="OR",
            )

            for card_id in self.find_cards(query):
                card = self.get_card(card_id)
                cards.setdefault(int(card.note()["card_id"]), []).append(card)

        return cards

    def get_components(self, note: WKNote) -> list[WKNote]:
        """
        Returns the Note objects corresponding to each of the given Note's
        components. For Kanji notes, this will be a list of Radicals. For
        Vocab notes, it will be a list of Kanji. For Radicals, the result
        will always be empty.
        """
        return list(
            self.find_notes_for_subjects(
                [int(comp, 16) for comp in note["components"].split()]
            ).values()
        )

    def get_level_complete_ratio(self, level: int) -> float:
        """
        Returns the proportion of Kanji notes in the given level which have
        reached Guru status, as determined by config.GURU_INTERVAL.
        """
        card_ids = self.find_cards(
            SearchNode(deck=f"{config.DECK_NAME}::Level {level:02}::2 - Kanji")
        )
        guru_cnt = reduce(
            operator.add,
            map(compose(card_is_guru, self.get_card), card_ids),
            0,
        )
        return guru_cnt / len(card_ids) if card_ids else 1

    @query_op
    def update_current_level_op(self) -> None:
        """
        Updates the user's current level, based on the value of
        config.LEVEL_COMPLETE_RATIO. The config._current_level property will
        be set to the highest level beyond the current level which has a ratio
        of Guru level Kanji notes meeting or exceeding that ratio.

        If the level increases, any suspended cards in the newly-unlocked which
        have their dependencies satisfied will be moved to the New queue.
        """
        current_level = config._current_level
        while current_level < 60:
            ratio = self.get_level_complete_ratio(current_level)
            if ratio < config.LEVEL_COMPLETE_RATIO:
                break
            current_level += 1

        if current_level > config._current_level:
            levels = range(config._current_level + 1, current_level + 1)
            config._current_level = current_level

            self.update_suspended_cards(levels=levels)

    def note_level_is_learnable(self, note: WKNote) -> bool:
        match note["Card_Type"]:
            case "Kanji":
                delta = config.UNLOCK_EXTRA_LEVELS_KANJI
            case "Radical":
                delta = config.UNLOCK_EXTRA_LEVELS_RADICAL
            case _:
                delta = config.UNLOCK_EXTRA_LEVELS_VOCAB

        return int(note["Level"]) <= config._current_level + delta

    @collection_op
    def update_suspended_cards_op(
        self, levels: None | Iterable[int] = None
    ) -> OpChangesWithCount:
        return self.update_suspended_cards(levels=levels)

    def update_suspended_cards(
        self, levels: None | Iterable[int] = None
    ) -> OpChangesWithCount:
        report_progress("Updating suspended cards for level...", 0, 0)

        immature_subjects = {
            format_id(int(self.get_note(nid)["card_id"]))
            for nid in self.find_notes(
                # Only radical and kanji subjects can be components, so don't
                # bother checking vocabulary cards.
                self.col.group_searches(
                    SearchNode(tag="Radical"), SearchNode(tag="Kanji"), joiner="OR"
                ),
                f"(prop:ivl<{config.GURU_INTERVAL} OR -is:review)",
            )
        }

        filters = []
        if levels:
            filters.append(
                self.col.group_searches(
                    *(
                        SearchNode(deck=f"{config.DECK_NAME}::Level {level:02}")
                        for level in levels
                    ),
                    joiner="OR",
                )
            )

        changed_cards = []
        note_ids = self.find_notes(*filters)
        for i, nid in enumerate(note_ids):
            report_progress("Updating suspended cards for level...", i, len(note_ids))
            note = self.get_note(nid)
            if any(
                subj in immature_subjects for subj in note["components"].split()
            ) or not self.note_level_is_learnable(note):
                for card in note.cards():
                    if card.type == CARD_TYPE_NEW:
                        card.queue = QUEUE_TYPE_SUSPENDED
                        changed_cards.append(card)
            else:
                for card in note.cards():
                    if card.queue == QUEUE_TYPE_SUSPENDED:
                        card.type = CARD_TYPE_NEW
                        card.queue = QUEUE_TYPE_NEW
                        changed_cards.append(card)

        self.col.update_cards(changed_cards)

        result = OpChangesWithCount()
        result.count = len(changed_cards)
        result.changes.card = True
        return result

    def is_unlockable(self, note: WKNote) -> bool:
        return note_is_wk(note) and any(
            card.queue in (QUEUE_TYPE_NEW, QUEUE_TYPE_SUSPENDED)
            for card in note.cards()
        )

    @collection_op
    def unlock_notes(self, note_ids: Sequence[NoteId]) -> OpChangesWithCount:
        notes_by_id = {}

        # Normalize all notes with the same ID to the same instance so they
        # can be used as dict/set keys for dependency tracking.
        def normalize_note(note: WKNote) -> WKNote:
            if note.id not in notes_by_id:
                notes_by_id[note.id] = note
            return notes_by_id[note.id]

        seen = set()
        deps = {}

        def rec(note: WKNote) -> None:
            if note.id in seen:
                return
            seen.add(note.id)

            notes = set(map(normalize_note, wk_col.get_components(note)))
            deps[note] = notes

            for note in notes:
                rec(note)

        for note_id in note_ids:
            rec(normalize_note(wk_col.get_note(note_id)))

        # Separate the dependency tree into tiers, which each tier containing
        # only cards without dependencies in later tiers.
        unprocessed = set(deps.keys())
        tiers = []
        while len(unprocessed):
            tier = set()
            for note in unprocessed:
                if not (deps[note] & unprocessed):
                    tier.add(note)

            unprocessed -= tier
            tiers.append(tier)

        # Schedule the cards in each tier to be learned in groups ten minutes
        # apart, so dependencies will always be learned before cards that
        # depend on them.
        DUE_DELTA = 60 * 10
        due = int(time.time())
        changed_cards = []
        for tier in tiers:
            found = False
            for note in tier:
                for card in note.cards():
                    if card.queue in (QUEUE_TYPE_SUSPENDED, QUEUE_TYPE_NEW):
                        card.queue = QUEUE_TYPE_LRN
                        card.type = CARD_TYPE_LRN
                        card.due = due
                        changed_cards.append(card)
                        found = True
            if found:
                due += DUE_DELTA

        self.col.update_cards(changed_cards)

        result = OpChangesWithCount()
        result.count = len(changed_cards)
        result.changes.card = True
        return result

    @collection_op
    def update_dependents(self, note: WKNote) -> OpChangesWithCount:
        # Dependency IDs are fixed width hex integers so that they can be
        # searched with simple substring searches. Checking for surrounding
        # spaces or start/end of line is not necessary.
        deps_ids = self.find_notes(
            SearchNode(card_state=SearchNode.CARD_STATE_SUSPENDED),
            f"components:*{format_id(int(note['card_id']))}*",
        )

        changed_cards = []
        for dep in map(self.get_note, deps_ids):
            if self.note_level_is_learnable(dep):
                comps = self.get_components(dep)
                if all(map(note_is_guru, comps)):
                    for card in dep.cards():
                        if card.queue == QUEUE_TYPE_SUSPENDED:
                            card.queue = QUEUE_TYPE_NEW
                            card.type = CARD_TYPE_NEW
                            changed_cards.append(card)

        self.col.update_cards(changed_cards)

        result = OpChangesWithCount()
        result.count = len(changed_cards)
        result.changes.card = len(changed_cards) > 0
        return result


wk_col = WKCollection()
