"""レコードの検証(仕様書 3.2.2 データの型 / 3.2.8 各種レコードレイアウト)。"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .issues import IssueCode, IssueCollector
from .models import RawRecord
from .spec.codes import CODE_TABLES
from .spec.records import Direction, FieldSpec, RecordNo, RecordSpec
from .text import field_at, sjis_byte_length

_WESTERN_DATE = re.compile(r"^(\d{4})(\d{2})(\d{2})$")
_JAPANESE_DATE = re.compile(r"^([MTSHR])(\d{2})(\d{2})(\d{2})$")
_NUMERIC = re.compile(r"^\d*$")
#: 型X: 英数字、ピリオド、ハイフン
_ALPHANUMERIC = re.compile(r"^[0-9A-Za-z.-]*$")

_DAYS_IN_MONTH = (31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


@dataclass(frozen=True)
class ValidationOptions:
    """検証の切り替え。"""

    #: コード表による区分値の検証を行う
    check_code_tables: bool = True
    #: バイト数・データ型の検証を行う
    check_field_format: bool = True


def _is_valid_month_day(month: int, day: int) -> bool:
    return 1 <= month <= 12 and 1 <= day <= _DAYS_IN_MONTH[month - 1]


def is_valid_date(value: str) -> bool:
    """西暦8桁 ``YYYYMMDD`` または和暦7桁 ``GYYMMDD`` の年月日かどうかを返す。"""
    western = _WESTERN_DATE.match(value)
    if western is not None:
        year, month, day = (int(group) for group in western.groups())
        if not _is_valid_month_day(month, day):
            return False
        if month == 2 and day == 29:
            return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
        return True

    japanese = _JAPANESE_DATE.match(value)
    if japanese is not None:
        return _is_valid_month_day(int(japanese.group(3)), int(japanese.group(4)))

    return False


def _validate_field(
    record: RawRecord,
    spec: RecordSpec,
    field: FieldSpec,
    issues: IssueCollector,
    direction: Direction | None,
    options: ValidationOptions,
) -> None:
    context = {
        "line": record.line,
        "record_no": spec.record_no,
        "field_index": field.index,
        "field_key": field.key,
    }
    value = field_at(record, field.index)

    if value is None:
        if field.is_required_for(direction):
            issues.error(
                IssueCode.MISSING_REQUIRED_FIELD,
                f"{spec.label}({spec.record_no}) の必須項目「{field.label}」が未設定です。",
                **context,
            )
        return

    if options.check_field_format:
        length = sjis_byte_length(value)
        if length > field.bytes:
            issues.warn(
                IssueCode.FIELD_TOO_LONG,
                f"{spec.label}({spec.record_no}) の「{field.label}」が仕様のバイト数 "
                f"{field.bytes} を超えています({length}バイト)。",
                **context,
            )

        if field.is_date:
            if not is_valid_date(value):
                issues.warn(
                    IssueCode.INVALID_DATE,
                    f"{spec.label}({spec.record_no}) の「{field.label}」は"
                    f"西暦8桁(YYYYMMDD)または和暦7桁(GYYMMDD)である必要があります: {value}",
                    **context,
                )
        elif field.type == "9" and _NUMERIC.match(value) is None:
            issues.warn(
                IssueCode.INVALID_TYPE,
                f"{spec.label}({spec.record_no}) の「{field.label}」は数値(型9)である必要があります: {value}",
                **context,
            )
        elif field.type == "X" and _ALPHANUMERIC.match(value) is None:
            issues.warn(
                IssueCode.INVALID_TYPE,
                f"{spec.label}({spec.record_no}) の「{field.label}」は"
                f"英数字・ピリオド・ハイフン(型X)である必要があります: {value}",
                **context,
            )

    if options.check_code_tables and field.code_table is not None:
        table = CODE_TABLES[field.code_table]
        if not table.is_valid(value):
            issues.warn(
                IssueCode.INVALID_CODE,
                f"{spec.label}({spec.record_no}) の「{field.label}」に"
                f"{table.label}として未定義のコード値が指定されています: {value}",
                **context,
            )


def _validate_code_pair(
    record: RawRecord,
    spec: RecordSpec,
    issues: IssueCollector,
    code_type_index: int,
    code_index: int,
) -> None:
    """コード種別が「1:コードなし」以外のときに、対応するコード項目が必須であることを検証する。"""
    code_type = field_at(record, code_type_index)
    code = field_at(record, code_index)
    if code_type is None or code_type == "1" or code is not None:
        return

    code_type_field = spec.fields[code_type_index - 1]
    code_field = spec.fields[code_index - 1]
    issues.error(
        IssueCode.MISSING_REQUIRED_FIELD,
        f"{spec.label}({spec.record_no}) の「{code_type_field.label}」が {code_type} のため"
        f"「{code_field.label}」は必須です。",
        line=record.line,
        record_no=spec.record_no,
        field_index=code_index,
        field_key=code_field.key,
    )


def validate_record(
    record: RawRecord,
    spec: RecordSpec,
    issues: IssueCollector,
    direction: Direction | None,
    options: ValidationOptions | None = None,
) -> None:
    """1レコードを仕様のレコードレイアウトに照らして検証する。"""
    options = options or ValidationOptions()

    field_count = len(record.fields) - 1
    if field_count > len(spec.fields):
        issues.warn(
            IssueCode.TOO_MANY_FIELDS,
            f"{spec.label}({spec.record_no}) の項目数が仕様({len(spec.fields)})より多くなっています({field_count})。",
            line=record.line,
            record_no=spec.record_no,
        )

    for field in spec.fields:
        _validate_field(record, spec, field, issues, direction, options)

    if spec.record_no == RecordNo.DRUG:
        _validate_code_pair(record, spec, issues, 5, 6)
        _validate_code_pair(record, spec, issues, 9, 10)
    elif spec.record_no == RecordNo.OTC_DRUG_INGREDIENT:
        _validate_code_pair(record, spec, issues, 3, 4)
    elif spec.record_no == RecordNo.USAGE:
        _validate_code_pair(record, spec, issues, 6, 7)


def validate_usage_name(
    issues: IssueCollector,
    *,
    line: int | None,
    direction: Direction | None,
    dispensed_by_pharmacy: bool,
    dosage_form_code: str | None,
    name: str | None,
) -> None:
    """用法名称の条件付き必須を検証する(仕様書 表3-23)。

    薬局が出力する場合(処方－医療機関レコードが出力されている場合)は、
    剤形コードが「9:材料」「10:その他」以外であれば用法名称が必須となる。
    """
    if name is not None:
        return

    exempt = dosage_form_code in {"9", "10"}
    required = direction == "to_provider" or (dispensed_by_pharmacy and not exempt)
    if not required:
        return

    issues.error(
        IssueCode.MISSING_REQUIRED_FIELD,
        "用法レコード(301) の必須項目「用法名称」が未設定です。",
        line=line,
        record_no=RecordNo.USAGE,
        field_index=2,
        field_key="name",
    )
