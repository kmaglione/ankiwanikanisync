#!/usr/bin/env python
from __future__ import annotations

import json
import lzma
import pickle
import re
import sys
import tarfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from typing import TYPE_CHECKING

import requests
from requests.adapters import HTTPAdapter, Retry

if TYPE_CHECKING:
    from .tenten_types import WordRecord
else:
    from tenten_types import WordRecord

# Needed by requests to decode 10ten data
try:
    import brotli  # type: ignore[import-not-found] # noqa: F401
except ImportError:
    import brotlicffi  # type: ignore[import-not-found] # noqa: F401

type HirasDict = dict[tuple[str, ...], tuple[int, ...]]
type AccentsDict = dict[str, HirasDict]

session = requests.Session()
session.mount(
    "https://", HTTPAdapter(max_retries=Retry(total=50, backoff_factor=0.5))
)


def fetch_10ten_data() -> AccentsDict:
    req = session.get("https://data.10ten.life/jpdict/reader/version-en.json")
    req.raise_for_status()
    version_info = req.json()

    major = "2"
    minor = version_info["words"][major]["minor"]
    patch = version_info["words"][major]["patch"]
    parts = version_info["words"][major]["parts"]

    res: AccentsDict = defaultdict(dict)

    # format from: https://github.com/birchill/jpdict-idb/blob/main/src/words.ts
    for part in range(1, parts + 1):
        req = session.get(
            f"https://data.10ten.life/jpdict/reader/words/en/{major}.{minor}.{patch}-{part}.jsonl"
        )
        req.raise_for_status()
        for line in req.iter_lines():
            line_data = json.loads(line)
            if "type" in line_data and line_data["type"] == "header":
                continue
            if any(k not in line_data for k in ("rm", "k", "r")):
                continue

            data: WordRecord = line_data

            rn = []
            rmn = []
            for r, rm in zip(data["r"], data["rm"]):
                if not rm or "a" not in rm:
                    continue

                if "app" in rm and rm["app"] == 0:
                    continue

                a = rm["a"]
                if isinstance(a, int):
                    rmn.append(a)
                else:
                    rmn.append(a[0]["i"])

                rn.append(r)

            if not rn:
                continue

            for reading in data["k"]:
                for pair in zip(rn, rmn):
                    if (pair[0],) not in res[reading]:
                        res[reading][pair[0],] = pair[1],

    return res


def fetch_wadoku_data() -> AccentsDict:
    req = session.get(
        "https://www.wadoku.de/downloads/xml-export/wadoku-xml-latest.tar.xz",
        stream=True,
    )
    req.raise_for_status()

    tree = None
    with tarfile.open(fileobj=req.raw, mode="r|xz") as tf:
        for member in tf:
            if member.name.endswith("/wadoku.xml"):
                f = tf.extractfile(member)
                assert f
                with f as contents:
                    tree = ET.parse(contents)
                break
    if tree is None:
        raise Exception("No wadoku.xml found!")

    root = tree.getroot()

    ns = {"": "http://www.wadoku.de/xml/entry"}
    hira_reg = re.compile(r"(\[Akz\]|[ぁ-ゔゞ゛゜ー])")

    res: AccentsDict = defaultdict(dict)

    for child in root.findall("entry", ns):
        orths = [
            orth.text for orth in child.findall("form/orth", ns) if orth.text
        ]
        if not orths:
            continue

        elem = child.find("form/reading/hatsuon", ns)
        assert elem is not None and elem.text
        hatsu = elem.text
        hiras = tuple("".join(hira_reg.findall(hatsu)).split("[Akz]"))

        # There can be multiple accent values, first one seems to be default though.
        accent_elem = child.find("form/reading/accent", ns)
        if accent_elem is None:
            continue
        assert accent_elem.text
        sub_accents = tuple(map(int, accent_elem.text.split("—")))

        if len(sub_accents) == 1 and len(hiras) > 1:
            # Sometimes there's multiple accent patterns, but the default
            # spans the whole reading
            hiras = ("".join(hiras),)
        elif len(sub_accents) != len(hiras):
            # Invalid config, should not happen
            raise Exception(
                f"Invalid accent config for {orths!r}: {sub_accents!r} / {hiras!r}"
            )

        for orth in orths:
            if hiras not in res[orth]:
                res[orth][hiras] = sub_accents

    return res


def combine_data(data1: AccentsDict, data2: AccentsDict) -> AccentsDict:
    res: AccentsDict = defaultdict(dict)
    res.update(data1)
    for orth, hiras in data2.items():
        for hira, accent in hiras.items():
            if orth in res and hira in res[orth]:
                if accent != res[orth][hira]:
                    print(
                        f"Found discrepancy for {orth}/{hira}: "
                        f"10ten: {res[orth][hira]}, Wadoku: {accent}",
                        file=sys.stderr,
                    )
                continue
            res[orth][hira] = accent
    return res


class HashableDict[K, V](dict[K, V]):
    def __hash__(self) -> int:  # type: ignore[override]
        return hash(tuple(sorted(self.items())))


def print_data(data: AccentsDict):
    comb_data = defaultdict[HirasDict, list[str]](list[str])
    for orth, hiras in data.items():
        comb_data[HashableDict(hiras)].append(orth)

    res = {}
    for hiras, orths in comb_data.items():
        for hira, acc in hiras.items():
            pitch_data = list(zip(hira, acc))
            for orth in orths:
                key = (orth, "".join(hira))
                if key not in res:
                    res[key] = pitch_data

    res_dict = {}
    for k, v in sorted(list(res.items()), key=lambda i: (i[0][1], i[0][0])):
        res_dict[k] = v

    with lzma.open(sys.argv[1], "wb") as f:
        pickle.dump(res_dict, f)


if __name__ == "__main__":
    print("Fetching 10ten...", file=sys.stderr)
    ten_data = fetch_10ten_data()
    print("Fetching Wadoku...", file=sys.stderr)
    wd_data = fetch_wadoku_data()
    print("Combining data...", file=sys.stderr)
    final_data = combine_data(ten_data, wd_data)
    print("Printing data...", file=sys.stderr)
    print_data(final_data)
