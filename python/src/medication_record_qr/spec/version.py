"""バージョンレコードのバージョン情報(仕様書 3.1)。

バージョン情報は ``"JAHISTC"`` + 半角数字2桁(9桁固定)で、仕様書の改版に伴い数値を1つ上げる。
ただしバージョン情報が変わらない改版もあるため、バージョン情報と仕様書バージョンは1対多になる。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

VERSION_PATTERN = re.compile(r"^JAHISTC(\d{2})$")


@dataclass(frozen=True)
class FormatVersionInfo:
    #: バージョン情報 (例: "JAHISTC08")
    version: str
    #: このバージョン情報を使用する仕様書バージョン
    spec_versions: tuple[str, ...]


#: 仕様書の改訂履歴に基づくバージョン情報の対応表
FORMAT_VERSIONS: tuple[FormatVersionInfo, ...] = (
    FormatVersionInfo("JAHISTC01", ("1.0",)),
    FormatVersionInfo("JAHISTC02", ("1.1",)),
    FormatVersionInfo("JAHISTC03", ("2.0",)),
    FormatVersionInfo("JAHISTC04", ("2.1",)),
    FormatVersionInfo("JAHISTC05", ("2.2",)),
    FormatVersionInfo("JAHISTC06", ("2.3",)),
    FormatVersionInfo("JAHISTC07", ("2.4",)),
    # Ver.2.6 はバージョン情報を変更していない(改訂内容は薬品コードの備考追加のみ)
    FormatVersionInfo("JAHISTC08", ("2.5", "2.6")),
)

#: このライブラリが対象とする仕様書バージョン
TARGET_SPEC_VERSION = "2.6"

#: このライブラリが既定で出力するバージョン情報 (仕様書 Ver.2.6)
DEFAULT_VERSION = "JAHISTC08"

_BY_VERSION = {info.version: info for info in FORMAT_VERSIONS}


def is_version_record(value: str) -> bool:
    """``JAHISTC`` + 2桁数字 の形式かどうかを返す。"""
    return VERSION_PATTERN.match(value) is not None


def find_format_version(version: str) -> FormatVersionInfo | None:
    return _BY_VERSION.get(version)


def spec_versions_of(version: str) -> tuple[str, ...] | None:
    """バージョン情報に対応する仕様書バージョンを返す(未知の場合は ``None``)。"""
    info = _BY_VERSION.get(version)
    return None if info is None else info.spec_versions


def version_number_of(version: str) -> int | None:
    """バージョン情報に含まれるバージョン番号を返す。"""
    matched = VERSION_PATTERN.match(version)
    return None if matched is None else int(matched.group(1))
