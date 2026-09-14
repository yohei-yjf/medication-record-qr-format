"""解析・検証で検出した問題と、ライブラリが送出する例外。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

IssueLevel = Literal["error", "warning"]


class IssueCode:
    """問題の種別。"""

    EMPTY_INPUT = "empty-input"
    MISSING_VERSION_RECORD = "missing-version-record"
    UNKNOWN_VERSION = "unknown-version"
    UNKNOWN_RECORD = "unknown-record"
    DUPLICATE_RECORD = "duplicate-record"
    MISSING_REQUIRED_FIELD = "missing-required-field"
    TOO_MANY_FIELDS = "too-many-fields"
    FIELD_TOO_LONG = "field-too-long"
    INVALID_CODE = "invalid-code"
    INVALID_DATE = "invalid-date"
    INVALID_TYPE = "invalid-type"
    ORPHAN_RECORD = "orphan-record"
    MISSING_USAGE = "missing-usage"
    SPLIT_MISMATCH = "split-mismatch"


@dataclass(frozen=True)
class Issue:
    """解析・検証で検出した1件の問題。"""

    level: IssueLevel
    code: str
    message: str
    #: 1始まりの行番号
    line: int | None = None
    record_no: str | None = None
    #: レコード内の項目位置(レコード番号を 0 とした連番)
    field_index: int | None = None
    field_key: str | None = None


class IssueCollector:
    """問題を集めるための入れ物。"""

    def __init__(self) -> None:
        self._issues: list[Issue] = []

    def add(self, issue: Issue) -> None:
        self._issues.append(issue)

    def error(self, code: str, message: str, **context: object) -> None:
        self.add(Issue(level="error", code=code, message=message, **context))  # type: ignore[arg-type]

    def warn(self, code: str, message: str, **context: object) -> None:
        self.add(Issue(level="warning", code=code, message=message, **context))  # type: ignore[arg-type]

    @property
    def all(self) -> list[Issue]:
        return self._issues

    @property
    def has_error(self) -> bool:
        return any(issue.level == "error" for issue in self._issues)


class MedicationNotebookError(Exception):
    """このライブラリが送出する例外の基底クラス。"""


class ParseError(MedicationNotebookError):
    """エラーを含むデータを ``parse_or_raise`` で解析した場合に送出される。"""

    def __init__(self, message: str, issues: list[Issue]) -> None:
        super().__init__(message)
        self.issues = issues


class SerializeError(MedicationNotebookError):
    """構造化データをテキストへ変換できない場合に送出される。"""

    def __init__(self, message: str, *, record_no: str | None = None, value: str | None = None) -> None:
        super().__init__(message)
        self.record_no = record_no
        self.value = value


class QrCodeError(MedicationNotebookError):
    """QRコードの生成・読み取りに失敗した場合に送出される。"""
