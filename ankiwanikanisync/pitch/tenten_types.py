# From https://github.com/birchill/jpdict-idb/blob/main/src/words.ts
from __future__ import annotations

from typing import Literal, NotRequired, TypedDict


class WordRecord(TypedDict):
    id: int

    # Kanji readings for the entry
    k: NotRequired[list[str]]
    km: NotRequired[list[None | KanjiMeta]]

    # Kana readings for the entry
    r: list[str]
    rm: NotRequired[list[None | ReadingMeta]]

    # Sense information
    s: list[WordSense]


class KanjiMeta(TypedDict):
    # Information about a kanji headword

    # Typically this should be of type KanjiInfo but we allow it to be any string
    # in case new types are introduced in future and the client has yet to be
    # updated.
    i: NotRequired[list[str]]

    # Priority information
    p: NotRequired[list[str]]

    # Bunpro vocab fuzzy match source text
    bv: NotRequired[str]

    # Bunpro grammar fuzzy match source text
    bg: NotRequired[str]


class ReadingMeta(TypedDict):
    # Information about the reading

    # Typically this should be of type ReadingInfo but we allow it to be any
    # string in case new types are introduced in future and the client has yet to
    # be updated.
    i: NotRequired[list[str]]

    # Priority information
    p: NotRequired[list[str]]

    # Bitfield representing which kanji entries (based on their order in the k
    # array) the reading applies to. 0 means it applies to none of them. If the
    # field is absent, it means the reading applies to all of the kanji entries.
    app: NotRequired[int]

    # Pitch accent information.
    a: NotRequired[int | list[Accent]]

    # Bunpro vocab fuzzy match source text
    bv: NotRequired[str]

    # Bunpro grammar fuzzy match source text
    bg: NotRequired[str]


class Accent(TypedDict):
    # Syllable number of the accent (after which the drop occurs).
    # 0 = 平板
    i: int

    # This should typically be a PartOfSpeech value.
    pos: NotRequired[list[str]]


class WordSense(TypedDict):
    g: list[str]

    # A bitfield representing the type of the glosses in `g`. Two bits are used
    # to represent the type of each item in `g`, where each two-bit value is one
    # of the GlossType values below.

    # Undefined if the value is 0 (i.e. no glosses have a type, the most common
    # case).
    gt: NotRequired[int]

    # undefined = 'en'
    lang: NotRequired[str]

    # Bit field representing the kanji / kana entries this sense applies to.
    # If the sense applies to all entries the field will be undefined.
    kapp: NotRequired[int]
    rapp: NotRequired[int]

    # Extra information about the sense.

    # Typically a PartOfSpeech value
    pos: NotRequired[list[str]]

    # Typically a FieldType value
    field: NotRequired[list[str]]

    # Typically a MiscType value
    misc: NotRequired[list[str]]

    # Typically a Dialect value
    dial: NotRequired[list[str]]
    inf: NotRequired[str]
    xref: NotRequired[list[CrossReference]]
    ant: NotRequired[list[CrossReference]]

    # Language source information.
    lsrc: NotRequired[list[LangSource]]


class CrossReference_0(TypedDict):
    k: str
    sense: NotRequired[int]


class CrossReference_1(TypedDict):
    r: str
    sense: NotRequired[int]


class CrossReference_2(TypedDict):
    k: str
    r: str
    sense: NotRequired[int]


type CrossReference = CrossReference_0 | CrossReference_1 | CrossReference_2


class LangSource(TypedDict):
    # undefined = 'en'
    lang: NotRequired[str]

    # The term in the source language

    # This may be empty in some cases.
    src: NotRequired[str]

    # Partial source (i.e. this only represents part of the string)
    # absent = false
    part: NotRequired[Literal[True]]

    # The Japanese word is made from words from another language but doesn't
    # actually represent the meaning of those words literally.
    wasei: NotRequired[Literal[True]]
