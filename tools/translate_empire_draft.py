#!/usr/bin/env python3
"""Create a reviewable Korean draft from the extracted Empire script.

This is deliberately a draft generator, not a release builder.  It preserves
every dynamic-name/control marker, applies the project's canonical Korean
proper nouns, caches external translations by source hash, and refuses output
when a batch marker or control count changes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen


GOOGLE_TRANSLATE_ENDPOINT = "https://translate.googleapis.com/translate_a/single"
CONTROL_RE = re.compile(r"\{([0-9A-F]{4})\}")
BATCH_RE = re.compile(
    r"ZXB(?P<id>\d{6})QXZ\s*\n(?P<text>.*?)\nZXE(?P=id)QXZ",
    re.DOTALL,
)

# Longest source spelling wins.  Static proper nouns are hidden from machine
# translation, then restored with the terminology already used by this repo.
CANONICAL_TERMS = (
    ("贝伦哈鲁特", "베른하르트"),
    ("贝伦哈尔特", "베른하르트"),
    ("贝伦哈特", "베른하르트"),
    ("伯伦哈特", "베른하르트"),
    ("埃格贝尔特", "에그베르트"),
    ("卡尔萨斯", "칼자스"),
    ("雷卡尔特", "레이갈드"),
    ("雷卡特", "레이갈드"),
    ("萨尔拉斯", "살라스"),
    ("艾斯德鲁", "에스톨"),
    ("维尔泽利亚", "벨제리아"),
    ("米雷鲁", "미레일"),
    ("莉亚娜", "리아나"),
    ("莉亚纳", "리아나"),
    ("艾尔文", "엘윈"),
    ("斯科特", "스코트"),
    ("杰西卡", "제시카"),
    ("伊梅尔达", "이멜다"),
    ("索尼娅", "소니아"),
    ("索尼亚", "소니아"),
    ("索尼雅", "소니아"),
    ("巴尔加斯", "발가스"),
    ("瓦尔加斯", "발가스"),
    ("埃尔温", "엘윈"),
    ("利斯塔", "레스터"),
    ("雷斯塔", "레스터"),
    ("波塞尔", "보젤"),
    ("波赞鲁", "보젤"),
    ("黑暗权杖", "다크로드"),
    ("光之巫女", "빛의 무녀"),
    ("暗之巫女", "어둠의 무녀"),
    ("黑龙魔导师团", "흑룡마도사단"),
    ("青龙骑士团", "청룡기사단"),
    ("炎龙兵团", "염룡병단"),
    ("水龙兵团", "수룡병단"),
    ("拉娜", "라나"),
    ("雪莉", "쉐리"),
    ("海恩", "헤인"),
    ("基斯", "키스"),
    ("阿伦", "아론"),
    ("利昂", "레온"),
    ("利亚特", "레아드"),
    ("洛加", "로우가"),
    ("罗伦", "로렌"),
    ("摩根", "모건"),
    ("伊梅达", "이멜다"),
    ("兰古利萨", "랑그릿사"),
    ("阿鲁哈萨特", "알하자드"),
)


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def clean_source(text: str) -> str:
    # One unused condition record references the word after its terminated
    # local list.  It is a source anomaly, not visible text.
    return text.replace("[GLYPH:FFFF]", "").strip()


def mask_text(text: str) -> tuple[str, dict[str, str]]:
    replacements: dict[str, str] = {}
    masked = clean_source(text)

    def marker(target: str) -> str:
        value = f"QZX{len(replacements):05d}XZQ"
        replacements[value] = target
        return value

    for source, target in CANONICAL_TERMS:
        if source not in masked:
            continue
        masked = re.sub(re.escape(source), lambda _match: marker(target), masked)
    masked = CONTROL_RE.sub(
        lambda match: "A-C-T-" + "-".join(match.group(1)), masked
    )
    masked = re.sub("\f", lambda _match: marker("\f"), masked)
    return masked, replacements


def restore_text(text: str, replacements: dict[str, str]) -> str:
    restored = re.sub(
        r"A-C-T-([0-9A-F])-([0-9A-F])-([0-9A-F])-([0-9A-F])",
        lambda match: "{" + "".join(match.groups()) + "}",
        text.strip(),
    )
    for marker, target in replacements.items():
        restored = restored.replace(marker, target)
    # Normalize typography to glyphs already established by the Korean build.
    restored = (
        restored.replace("“", '"')
        .replace("”", '"')
        .replace("‘", "'")
        .replace("’", "'")
        .replace("～", "~")
        .replace("……", "…")
    )
    return restored


def translate_request(text: str, timeout: int = 60) -> str:
    query = urlencode(
        {
            "client": "gtx",
            "sl": "zh-CN",
            "tl": "ko",
            "dt": "t",
            "q": text,
        }
    )
    request = Request(
        f"{GOOGLE_TRANSLATE_ENDPOINT}?{query}",
        headers={"User-Agent": "Langrisser-II-Korean-Empire-Draft/1.0"},
    )
    with urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return "".join(str(row[0]) for row in payload[0])


def translate_batches(
    sources: list[str],
    cache: dict[str, str],
    cache_path: Path,
    max_batch_chars: int,
    request_delay: float,
) -> dict[str, str]:
    missing = [text for text in dict.fromkeys(sources) if digest(text) not in cache]
    cursor = 0
    while cursor < len(missing):
        batch: list[str] = []
        payload_size = 0
        while cursor < len(missing):
            source = missing[cursor]
            masked, _ = mask_text(source)
            marker_overhead = 44
            if batch and payload_size + len(masked) + marker_overhead > max_batch_chars:
                break
            batch.append(source)
            payload_size += len(masked) + marker_overhead
            cursor += 1

        request_rows: list[str] = []
        replacement_rows: list[dict[str, str]] = []
        for index, source in enumerate(batch):
            masked, replacements = mask_text(source)
            request_rows.append(
                f"ZXB{index:06d}QXZ\n{masked}\nZXE{index:06d}QXZ"
            )
            replacement_rows.append(replacements)
        request_text = "\n".join(request_rows)

        last_error: Exception | None = None
        for attempt in range(5):
            try:
                translated = translate_request(request_text)
                matches = list(BATCH_RE.finditer(translated))
                if len(matches) != len(batch):
                    raise ValueError(
                        f"translation batch lost markers: {len(matches)} != {len(batch)}"
                    )
                for match, source, replacements in zip(
                    matches, batch, replacement_rows
                ):
                    target = restore_text(match.group("text"), replacements)
                    if CONTROL_RE.findall(source) != CONTROL_RE.findall(target):
                        raise ValueError(
                            "dynamic-name controls changed during translation: "
                            f"{source!r} -> {target!r}"
                        )
                    if source.count("\f") != target.count("\f"):
                        raise ValueError(
                            "page controls changed during translation: "
                            f"{source!r} -> {target!r}"
                        )
                    cache[digest(source)] = target
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(
                    json.dumps(cache, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                print(f"translated {cursor}/{len(missing)} unique source records")
                last_error = None
                break
            except Exception as exc:  # pragma: no cover - network retry path
                last_error = exc
                time.sleep(2 ** attempt)
        if last_error is not None:
            raise last_error
        if request_delay:
            time.sleep(request_delay)
    return {text: cache[digest(text)] for text in dict.fromkeys(sources)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--inventory",
        type=Path,
        default=Path("localization/empire/source/text_inventory.json"),
    )
    parser.add_argument(
        "--cache",
        type=Path,
        default=Path("localization/empire/draft/translation_cache.json"),
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("localization/empire/draft/script_ko.json"),
    )
    parser.add_argument("--max-batch-chars", type=int, default=2800)
    parser.add_argument("--request-delay", type=float, default=0.20)
    args = parser.parse_args()

    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    cache = (
        json.loads(args.cache.read_text(encoding="utf-8"))
        if args.cache.exists()
        else {}
    )
    records: list[dict[str, object]] = []
    for kind in ("condition_records", "scenario_description_records"):
        for row in inventory[kind]:
            records.append({"kind": kind, **row})
    for scenario, rows in inventory["event_scenarios"].items():
        for row in rows:
            records.append({"kind": "event", "scenario": int(scenario), **row})

    sources = [clean_source(str(row["source_chinese_line_ocr"])) for row in records]
    translated = translate_batches(
        sources,
        cache,
        args.cache,
        args.max_batch_chars,
        args.request_delay,
    )

    output = {
        "edition": "Empire V2.0 (96%) Korean localization",
        "source_sha256": inventory["source_sha256"],
        "status": "machine-assisted draft; human/context review required",
        "provider": "Google Translate zh-CN to ko draft with canonical-term masking",
        "control_syntax": "{NNNN}=FFF7 actor/name; newline=FFFE; form feed=FFFD",
        "condition_records": [],
        "scenario_description_records": [],
        "event_scenarios": {str(index): [] for index in range(1, 32)},
    }
    for row, source in zip(records, sources):
        target_row = {
            key: value
            for key, value in row.items()
            if key not in {"kind", "source_chinese_ocr", "source_chinese_line_ocr"}
        }
        target_row["source_chinese"] = source
        target_row["draft_korean"] = translated[source]
        if row["kind"] == "event":
            output["event_scenarios"][str(row["scenario"])].append(target_row)
        else:
            output[str(row["kind"])].append(target_row)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {args.out} with {len(records)} records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
