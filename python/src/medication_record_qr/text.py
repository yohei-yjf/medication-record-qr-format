"""レコード行の分解と組み立て(仕様書 3.2.1 ファイル形式 / 3.2.4 注意事項等)。"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence

from .issues import SerializeError
from .models import RawRecord

#: レコード終端(CR+LF)
RECORD_SEPARATOR = "\r\n"
#: 項目区切り文字
FIELD_SEPARATOR = ","
#: ファイル終端(EOF, 0x1A)
EOF_CHARACTER = "\x1a"

_NEWLINE_PATTERN = re.compile(r"\r\n|\n|\r")
_TRAILING_EOF_PATTERN = re.compile(r"\x1a+$")
_BOM = "﻿"


def parse_raw_records(text: str) -> list[RawRecord]:
    """お薬手帳データのテキストを1行=1レコードに分解する。

    - 改行は CR+LF / LF / CR のいずれも受け付ける。
    - 先頭のBOMおよび末尾のファイル終端(EOF, 0x1A)は取り除く。
    - 空行は読み飛ばす(行番号は元のテキストに対する1始まりの値を保持する)。
    - 仕様上、項目値に半角カンマ・改行は含められないため引用符処理は行わない。
    """
    normalized = _TRAILING_EOF_PATTERN.sub("", text.removeprefix(_BOM))
    records: list[RawRecord] = []

    for index, line in enumerate(_NEWLINE_PATTERN.split(normalized)):
        if not line.strip():
            continue
        values = tuple(line.split(FIELD_SEPARATOR))
        records.append(RawRecord(line=index + 1, record_no=values[0].strip(), fields=values, raw=line))

    return records


def _assert_field_value(record_no: str, value: str) -> None:
    if FIELD_SEPARATOR in value:
        raise SerializeError(
            f"項目値に半角カンマを含めることはできません(レコード {record_no}): {value!r}。"
            "仕様では、薬品名称等で半角カンマを使用している場合は全角カンマに置き換えることとされています。",
            record_no=record_no,
            value=value,
        )
    if "\r" in value or "\n" in value:
        raise SerializeError(
            f"項目値に改行を含めることはできません(レコード {record_no}): {value!r}",
            record_no=record_no,
            value=value,
        )


def format_record(
    record_no: str,
    values: Iterable[str | None],
    *,
    omit_trailing_empty_fields: bool = False,
) -> str:
    """レコード番号と項目値から1レコード分の行文字列を生成する。

    仕様書の出力データ例は末尾の項目まで区切り文字を出力しているため、既定では省略しない。
    QRコードの容量を節約したい場合は ``omit_trailing_empty_fields=True`` を指定する。
    """
    items = ["" if value is None else value for value in values]
    for value in items:
        _assert_field_value(record_no, value)

    if omit_trailing_empty_fields:
        while items and items[-1] == "":
            items.pop()

    return FIELD_SEPARATOR.join([record_no, *items])


def field_at(record: RawRecord, index: int) -> str | None:
    """項目値を取得する(未指定・空文字は ``None`` を返す)。"""
    if index >= len(record.fields):
        return None
    value = record.fields[index].strip()
    return value or None


def join_records(lines: Sequence[str], newline: str = RECORD_SEPARATOR) -> str:
    """行の配列を1つのテキストにまとめる。"""
    return newline.join(lines)


def sjis_byte_length(value: str, encoding: str = "cp932") -> int:
    """仕様書の「バイト数」に対応するバイト長を返す(全角文字は2バイト)。

    Shift_JIS で表現できない文字は、代替文字1バイトとして数える。
    """
    return len(value.encode(encoding, errors="replace"))
