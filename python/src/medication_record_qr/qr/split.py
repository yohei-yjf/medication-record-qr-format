"""データの分割と結合(仕様書 3.2.9(3) データを分割した場合の出力方法)。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime

from ..issues import Issue, IssueCode
from ..spec.records import RecordNo
from ..text import FIELD_SEPARATOR, RECORD_SEPARATOR, parse_raw_records
from .charset import DEFAULT_ENCODING, byte_length

#: 1シンボルあたりの既定の最大バイト数。
#:
#: QRコード(型番40・誤り訂正レベルM・8ビットバイトモード)の理論上限は2331バイトだが、
#: 携帯電話等での読み取り性能を考慮して控えめな既定値としている。
DEFAULT_MAX_BYTES_PER_SYMBOL = 1800


@dataclass(frozen=True)
class MergeResult:
    """分割されたデータの結合結果。"""

    #: 結合後のテキスト(分割制御レコードは取り除かれる)
    text: str
    #: 分割制御レコードが示す分割数
    total_count: int
    data_id: str | None = None
    issues: list[Issue] = field(default_factory=list)


def _generate_data_id() -> str:
    """データ固有ID(数値14桁)を採番する。"""
    return datetime.now().strftime("%Y%m%d%H%M%S")


def split_for_qr(
    text: str,
    *,
    max_bytes_per_symbol: int = DEFAULT_MAX_BYTES_PER_SYMBOL,
    encoding: str = DEFAULT_ENCODING,
    data_id: str | None = None,
    newline: str = RECORD_SEPARATOR,
) -> list[str]:
    """お薬手帳データのテキストを、1つのQRコードに収まる大きさへ分割する。

    - 分割はレコード単位で行う
    - 分割された全てのデータの先頭にバージョンレコードを出力する
    - 分割された全てのデータの末尾に分割制御レコード(911)を出力する

    分割が不要な場合は、分割制御レコードを付けずに元のテキストをそのまま1件返す。
    """
    records = parse_raw_records(text)
    if not records:
        return []
    if byte_length(text, encoding) <= max_bytes_per_symbol:
        return [text]

    version_line = records[0].raw
    body_lines = [record.raw for record in records[1:] if record.record_no != RecordNo.SPLIT_CONTROL]

    resolved_data_id = data_id or _generate_data_id()
    newline_bytes = byte_length(newline, encoding)
    # 分割制御レコードは `911,<データ固有ID>,<分割数>,<データ連番>`。分割数・連番は最大3桁。
    split_record_bytes = (
        byte_length(FIELD_SEPARATOR.join([RecordNo.SPLIT_CONTROL, resolved_data_id, "999", "999"]), encoding)
        + newline_bytes
    )
    budget = max_bytes_per_symbol - byte_length(version_line, encoding) - newline_bytes - split_record_bytes

    chunks: list[list[str]] = []
    current: list[str] = []
    current_bytes = 0

    for line in body_lines:
        line_bytes = byte_length(line, encoding) + newline_bytes
        if line_bytes > budget:
            raise ValueError(
                f"1レコードが1シンボルの上限({max_bytes_per_symbol}バイト)に収まりません。"
                f"max_bytes_per_symbol を増やしてください: {line}"
            )
        if current and current_bytes + line_bytes > budget:
            chunks.append(current)
            current = []
            current_bytes = 0
        current.append(line)
        current_bytes += line_bytes

    if current:
        chunks.append(current)

    return [
        newline.join(
            [
                version_line,
                *chunk,
                FIELD_SEPARATOR.join([RecordNo.SPLIT_CONTROL, resolved_data_id, str(len(chunks)), str(index + 1)]),
            ]
        )
        for index, chunk in enumerate(chunks)
    ]


@dataclass(frozen=True)
class _SplitPart:
    version_line: str | None
    data_id: str | None
    total_count: int | None
    sequence: int | None
    body_lines: list[str]


def _to_number(value: str | None) -> int | None:
    if value is None or not value.strip():
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _decode_part(text: str) -> _SplitPart:
    records = parse_raw_records(text)
    split_record = next((record for record in records if record.record_no == RecordNo.SPLIT_CONTROL), None)

    def at(index: int) -> str | None:
        if split_record is None or index >= len(split_record.fields):
            return None
        return split_record.fields[index]

    return _SplitPart(
        version_line=records[0].raw if records else None,
        data_id=at(1),
        total_count=_to_number(at(2)),
        sequence=_to_number(at(3)),
        body_lines=[
            record.raw
            for index, record in enumerate(records)
            if index != 0 and record.record_no != RecordNo.SPLIT_CONTROL
        ],
    )


def merge_split_parts(parts: Sequence[str], newline: str = RECORD_SEPARATOR) -> MergeResult:
    """分割された複数シンボル分のテキストを1つのテキストへ復元する。

    分割制御レコード(911)のデータ連番順に並べ替えるため、読み取り順は問わない。
    """
    issues: list[Issue] = []

    def error(message: str) -> None:
        issues.append(Issue(level="error", code=IssueCode.SPLIT_MISMATCH, message=message))

    decoded = [_decode_part(part) for part in parts]

    data_ids = list(dict.fromkeys(part.data_id for part in decoded if part.data_id is not None))
    if len(data_ids) > 1:
        error(f"異なるデータ固有IDのシンボルが混在しています: {', '.join(data_ids)}")

    total_counts = list(dict.fromkeys(part.total_count for part in decoded if part.total_count is not None))
    if len(total_counts) > 1:
        error(f"分割数が一致していません: {', '.join(str(count) for count in total_counts)}")

    expected_total = total_counts[0] if total_counts else None
    if expected_total is not None and expected_total != len(parts):
        error(f"分割数 {expected_total} に対して {len(parts)} 件のシンボルしかありません。")

    ordered = sorted(decoded, key=lambda part: part.sequence if part.sequence is not None else 1)
    seen: set[int] = set()
    for part in ordered:
        if part.sequence is None:
            continue
        if part.sequence in seen:
            error(f"データ連番 {part.sequence} のシンボルが重複しています。")
        seen.add(part.sequence)

    version_line = ordered[0].version_line if ordered else None
    lines: list[str] = []
    if version_line is not None:
        lines.append(version_line)
        for part in ordered:
            lines.extend(part.body_lines)

    return MergeResult(
        text=newline.join(lines),
        total_count=expected_total if expected_total is not None else len(parts),
        data_id=data_ids[0] if data_ids else None,
        issues=issues,
    )
