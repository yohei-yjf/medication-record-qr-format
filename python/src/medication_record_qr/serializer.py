"""構造化データを JAHIS電子版お薬手帳データのテキストへ変換する(仕様書 3.2.6 レコード出力順)。"""

from __future__ import annotations

from collections.abc import Iterable

from .models import MedicationNotebook, TextNote, field_values
from .spec.records import RecordKind, record_spec_of
from .spec.version import DEFAULT_VERSION
from .text import FIELD_SEPARATOR, RECORD_SEPARATOR, format_record

Values = dict[str, object]


def _emit(lines: list[str], kind: str, values: Values, *, omit_trailing_empty_fields: bool) -> None:
    spec = record_spec_of(kind)
    lines.append(
        format_record(
            spec.record_no,
            [values.get(item.key) for item in spec.fields],  # type: ignore[misc]
            omit_trailing_empty_fields=omit_trailing_empty_fields,
        )
    )


def _emit_notes(
    lines: list[str],
    kind: str,
    notes: Iterable[TextNote],
    *,
    omit_trailing_empty_fields: bool,
    extra: Values | None = None,
) -> None:
    for note in notes:
        values: Values = dict(extra or {})
        values.update({"text": note.text, "record_creator": note.record_creator})
        _emit(lines, kind, values, omit_trailing_empty_fields=omit_trailing_empty_fields)


def to_record_lines(
    notebook: MedicationNotebook,
    *,
    version: str | None = None,
    omit_trailing_empty_fields: bool = False,
) -> list[str]:
    """構造化データを、仕様書「レコード出力順」に従った行の配列へ変換する。

    先頭要素はバージョンレコード、分割制御レコード(911)がある場合は末尾になる。
    """
    lines: list[str] = []
    omit = omit_trailing_empty_fields

    lines.append(
        format_record(
            version or notebook.version or DEFAULT_VERSION,
            [notebook.output_category],
            omit_trailing_empty_fields=omit,
        )
    )

    if notebook.patient is not None:
        _emit(lines, RecordKind.PATIENT, field_values(notebook.patient), omit_trailing_empty_fields=omit)
    for remark in notebook.patient_remarks:
        _emit(lines, RecordKind.PATIENT_REMARK, field_values(remark), omit_trailing_empty_fields=omit)

    for otc_drug in notebook.otc_drugs:
        _emit(lines, RecordKind.OTC_DRUG, field_values(otc_drug), omit_trailing_empty_fields=omit)
        for ingredient in otc_drug.ingredients:
            values = field_values(ingredient)
            values["otc_drug_sequence"] = otc_drug.sequence
            _emit(lines, RecordKind.OTC_DRUG_INGREDIENT, values, omit_trailing_empty_fields=omit)

    for memo in notebook.notebook_memos:
        _emit(lines, RecordKind.NOTEBOOK_MEMO, field_values(memo), omit_trailing_empty_fields=omit)

    for dispensing in notebook.dispensings:
        _emit(
            lines,
            RecordKind.DISPENSING_DATE,
            {"date": dispensing.date, "record_creator": dispensing.record_creator},
            omit_trailing_empty_fields=omit,
        )

        if dispensing.institution is not None:
            _emit(
                lines,
                RecordKind.DISPENSING_INSTITUTION,
                field_values(dispensing.institution),
                omit_trailing_empty_fields=omit,
            )
        if dispensing.staff is not None:
            _emit(
                lines,
                RecordKind.DISPENSING_STAFF,
                field_values(dispensing.staff),
                omit_trailing_empty_fields=omit,
            )
        if dispensing.prescribing_institution is not None:
            _emit(
                lines,
                RecordKind.PRESCRIBING_INSTITUTION,
                field_values(dispensing.prescribing_institution),
                omit_trailing_empty_fields=omit,
            )

        for group in dispensing.doctor_groups:
            if group.doctor is not None:
                _emit(
                    lines,
                    RecordKind.PRESCRIBING_DOCTOR,
                    field_values(group.doctor),
                    omit_trailing_empty_fields=omit,
                )

            for rp in group.rps:
                extra: Values = {"rp_number": rp.rp_number}
                _emit_notes(
                    lines,
                    RecordKind.DRUG_SUPPLEMENT,
                    rp.orphan_drug_notes,
                    omit_trailing_empty_fields=omit,
                    extra=extra,
                )

                for drug in rp.drugs:
                    values = field_values(drug)
                    values.update(extra)
                    _emit(lines, RecordKind.DRUG, values, omit_trailing_empty_fields=omit)
                    _emit_notes(
                        lines,
                        RecordKind.DRUG_SUPPLEMENT,
                        drug.supplements,
                        omit_trailing_empty_fields=omit,
                        extra=extra,
                    )
                    _emit_notes(
                        lines,
                        RecordKind.DRUG_CAUTION,
                        drug.cautions,
                        omit_trailing_empty_fields=omit,
                        extra=extra,
                    )

                if rp.usage is not None:
                    values = field_values(rp.usage)
                    values.update(extra)
                    _emit(lines, RecordKind.USAGE, values, omit_trailing_empty_fields=omit)
                _emit_notes(
                    lines,
                    RecordKind.USAGE_SUPPLEMENT,
                    rp.usage_supplements,
                    omit_trailing_empty_fields=omit,
                    extra=extra,
                )
                _emit_notes(
                    lines,
                    RecordKind.PRESCRIPTION_CAUTION,
                    rp.prescription_cautions,
                    omit_trailing_empty_fields=omit,
                    extra=extra,
                )

        _emit_notes(lines, RecordKind.CAUTION, dispensing.cautions, omit_trailing_empty_fields=omit)
        for info in dispensing.provided_infos:
            _emit(lines, RecordKind.PROVIDED_INFO, field_values(info), omit_trailing_empty_fields=omit)
        _emit_notes(
            lines,
            RecordKind.REMAINING_DRUG_CHECK,
            dispensing.remaining_drug_checks,
            omit_trailing_empty_fields=omit,
        )
        _emit_notes(lines, RecordKind.REMARK, dispensing.remarks, omit_trailing_empty_fields=omit)
        for entry in dispensing.patient_entries:
            _emit(lines, RecordKind.PATIENT_ENTRY, field_values(entry), omit_trailing_empty_fields=omit)

    for pharmacist in notebook.family_pharmacists:
        _emit(lines, RecordKind.FAMILY_PHARMACIST, field_values(pharmacist), omit_trailing_empty_fields=omit)

    for unknown in notebook.unknown_records:
        lines.append(FIELD_SEPARATOR.join([unknown.record_no, *unknown.fields]))

    if notebook.split is not None:
        _emit(lines, RecordKind.SPLIT_CONTROL, field_values(notebook.split), omit_trailing_empty_fields=omit)

    return lines


def serialize(
    notebook: MedicationNotebook,
    *,
    version: str | None = None,
    newline: str = RECORD_SEPARATOR,
    omit_trailing_empty_fields: bool = False,
) -> str:
    """構造化データを JAHIS電子版お薬手帳データのテキストへ変換する。"""
    return newline.join(
        to_record_lines(notebook, version=version, omit_trailing_empty_fields=omit_trailing_empty_fields)
    )
