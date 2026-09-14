"""JAHIS電子版お薬手帳データのテキストを構造化データへ変換する。"""

from __future__ import annotations

from dataclasses import dataclass, field

from .issues import Issue, IssueCode, IssueCollector, ParseError
from .models import (
    Dispensing,
    DispensingInstitution,
    DispensingStaff,
    DoctorGroup,
    Drug,
    FamilyPharmacist,
    MedicationNotebook,
    NotebookMemo,
    OtcDrug,
    OtcDrugIngredient,
    Patient,
    PatientEntry,
    PatientRemark,
    PrescribingDoctor,
    PrescribingInstitution,
    ProvidedInfo,
    RawRecord,
    Rp,
    SplitControl,
    TextNote,
    UnknownRecord,
    Usage,
)
from .spec.records import Direction, RecordNo, RecordSpec, direction_of, find_record_spec
from .spec.version import DEFAULT_VERSION, find_format_version, is_version_record, spec_versions_of
from .text import field_at, parse_raw_records
from .validation import ValidationOptions, validate_record, validate_usage_name

Values = dict[str, str | None]


@dataclass(frozen=True)
class ParseResult:
    """解析結果。"""

    #: エラーが無ければ ``True`` (strict 指定時は警告が1件でもあれば ``False``)
    ok: bool
    #: 構造化データ。解析できた範囲を常に返す。
    notebook: MedicationNotebook
    issues: list[Issue] = field(default_factory=list)
    #: 解析前のレコード
    records: list[RawRecord] = field(default_factory=list)


def _read_fields(record: RawRecord, spec: RecordSpec) -> Values:
    """レコードレイアウトの定義に従って項目値を読み出す。"""
    return {item.key: field_at(record, item.index) for item in spec.fields}


def _to_note(values: Values) -> TextNote:
    return TextNote(text=values["text"], record_creator=values["record_creator"])


class _NotebookBuilder:
    def __init__(self, version: str, issues: IssueCollector, direction: Direction | None) -> None:
        self.notebook = MedicationNotebook(version=version, spec_versions=spec_versions_of(version))
        self._issues = issues
        self._direction = direction
        self._dispensing: Dispensing | None = None
        self._rp: Rp | None = None
        self._drug: Drug | None = None
        self._last_otc_drug: OtcDrug | None = None

    # -- 補助 ---------------------------------------------------------------

    def _duplicate(self, record: RawRecord, spec: RecordSpec) -> None:
        self._issues.warn(
            IssueCode.DUPLICATE_RECORD,
            f"{spec.label}({spec.record_no}) は「{spec.repetition}」ですが複数回出現しました。"
            "最初のレコードを採用します。",
            line=record.line,
            record_no=spec.record_no,
        )

    def _ensure_dispensing(self, record: RawRecord, spec: RecordSpec) -> Dispensing:
        """調剤等年月日レコード(5)より前に調剤情報グループのレコードが現れた場合の救済。"""
        if self._dispensing is None:
            self._issues.warn(
                IssueCode.ORPHAN_RECORD,
                f"{spec.label}({spec.record_no}) が調剤等年月日レコード(5)より前に出現したため、"
                "暗黙の調剤情報として扱います。",
                line=record.line,
                record_no=spec.record_no,
            )
            self._dispensing = Dispensing()
            self.notebook.dispensings.append(self._dispensing)
        return self._dispensing

    def _ensure_doctor_group(self, record: RawRecord, spec: RecordSpec) -> DoctorGroup:
        """処方－医師レコード(55)が出力されない場合は、医師を持たない1グループにまとめる。"""
        dispensing = self._ensure_dispensing(record, spec)
        if dispensing.doctor_groups:
            return dispensing.doctor_groups[-1]
        group = DoctorGroup()
        dispensing.doctor_groups.append(group)
        return group

    def _rp_of(self, record: RawRecord, spec: RecordSpec, rp_number: str | None) -> Rp:
        group = self._ensure_doctor_group(record, spec)
        key = rp_number or ""
        dispensing = self._dispensing
        assert dispensing is not None

        for existing_group in dispensing.doctor_groups:
            for existing in existing_group.rps:
                if existing.rp_number == key:
                    if self._rp is not existing:
                        self._rp = existing
                        self._drug = None
                    return existing

        rp = Rp(rp_number=key)
        group.rps.append(rp)
        self._rp = rp
        self._drug = None
        return rp

    # -- レコードごとの組み立て ---------------------------------------------

    def set_patient(self, record: RawRecord, spec: RecordSpec, values: Values) -> None:
        if self.notebook.patient is not None:
            self._duplicate(record, spec)
            return
        self.notebook.patient = Patient(**values)

    def start_dispensing(self, values: Values) -> None:
        dispensing = Dispensing(date=values["date"], record_creator=values["record_creator"])
        self.notebook.dispensings.append(dispensing)
        self._dispensing = dispensing
        self._rp = None
        self._drug = None

    def set_dispensing_institution(self, record: RawRecord, spec: RecordSpec, values: Values) -> None:
        dispensing = self._ensure_dispensing(record, spec)
        if dispensing.institution is not None:
            self._duplicate(record, spec)
            return
        dispensing.institution = DispensingInstitution(**values)

    def set_dispensing_staff(self, record: RawRecord, spec: RecordSpec, values: Values) -> None:
        dispensing = self._ensure_dispensing(record, spec)
        if dispensing.staff is not None:
            self._duplicate(record, spec)
            return
        dispensing.staff = DispensingStaff(**values)

    def set_prescribing_institution(self, record: RawRecord, spec: RecordSpec, values: Values) -> None:
        dispensing = self._ensure_dispensing(record, spec)
        if dispensing.prescribing_institution is not None:
            self._duplicate(record, spec)
            return
        dispensing.prescribing_institution = PrescribingInstitution(**values)

    def start_doctor_group(self, record: RawRecord, spec: RecordSpec, values: Values) -> None:
        dispensing = self._ensure_dispensing(record, spec)
        dispensing.doctor_groups.append(DoctorGroup(doctor=PrescribingDoctor(**values)))
        self._rp = None
        self._drug = None

    def add_drug(self, record: RawRecord, spec: RecordSpec, values: Values) -> None:
        rp = self._rp_of(record, spec, values["rp_number"])
        drug = Drug(
            name=values["name"],
            dose=values["dose"],
            unit_name=values["unit_name"],
            code_type=values["code_type"],
            code=values["code"],
            record_creator=values["record_creator"],
            general_name=values["general_name"],
            general_name_code_type=values["general_name_code_type"],
            general_name_code=values["general_name_code"],
        )
        rp.drugs.append(drug)
        self._drug = drug

    def add_drug_note(self, record: RawRecord, spec: RecordSpec, values: Values, target: str) -> None:
        rp = self._rp_of(record, spec, values["rp_number"])
        note = _to_note(values)
        if self._drug is None or not any(drug is self._drug for drug in rp.drugs):
            self._issues.warn(
                IssueCode.ORPHAN_RECORD,
                f"{spec.label}({spec.record_no}) に対応する薬品レコード(201)が直前にありません。"
                "RP単位の情報として保持します。",
                line=record.line,
                record_no=spec.record_no,
            )
            rp.orphan_drug_notes.append(note)
            return
        getattr(self._drug, target).append(note)

    def set_usage(self, record: RawRecord, spec: RecordSpec, values: Values) -> None:
        rp = self._rp_of(record, spec, values["rp_number"])
        if rp.usage is not None:
            self._issues.warn(
                IssueCode.DUPLICATE_RECORD,
                f"RP{rp.rp_number} に用法レコード(301)が複数存在します。",
                line=record.line,
                record_no=spec.record_no,
            )
        rp.usage = Usage(
            name=values["name"],
            dispensing_quantity=values["dispensing_quantity"],
            dispensing_unit=values["dispensing_unit"],
            dosage_form_code=values["dosage_form_code"],
            code_type=values["code_type"],
            code=values["code"],
            record_creator=values["record_creator"],
        )

        validate_usage_name(
            self._issues,
            line=record.line,
            direction=self._direction,
            dispensed_by_pharmacy=(
                self._dispensing is not None and self._dispensing.prescribing_institution is not None
            ),
            dosage_form_code=values["dosage_form_code"],
            name=values["name"],
        )

    def add_rp_note(self, record: RawRecord, spec: RecordSpec, values: Values, target: str) -> None:
        rp = self._rp_of(record, spec, values["rp_number"])
        getattr(rp, target).append(_to_note(values))

    def add_otc_drug(self, values: Values) -> None:
        otc_drug = OtcDrug(
            name=values["name"],
            start_date=values["start_date"],
            end_date=values["end_date"],
            record_creator=values["record_creator"],
            sequence=values["sequence"],
            jan_code=values["jan_code"],
        )
        self.notebook.otc_drugs.append(otc_drug)
        self._last_otc_drug = otc_drug

    def add_otc_ingredient(self, record: RawRecord, spec: RecordSpec, values: Values) -> None:
        sequence = values["otc_drug_sequence"]
        matched = next(
            (drug for drug in self.notebook.otc_drugs if sequence is not None and drug.sequence == sequence),
            None,
        )
        target = matched or self._last_otc_drug

        if target is None:
            self._issues.warn(
                IssueCode.ORPHAN_RECORD,
                f"{spec.label}({spec.record_no}) に対応する要指導医薬品・一般用医薬品服用レコード(3)がありません。",
                line=record.line,
                record_no=spec.record_no,
            )
            return
        if matched is None:
            self._issues.warn(
                IssueCode.ORPHAN_RECORD,
                f"通番 {sequence or '(未設定)'} に一致する要指導医薬品・一般用医薬品服用レコード(3)が"
                "無いため、直前のレコードに紐づけました。",
                line=record.line,
                record_no=spec.record_no,
            )

        target.ingredients.append(
            OtcDrugIngredient(
                name=values["name"],
                code_type=values["code_type"],
                code=values["code"],
                record_creator=values["record_creator"],
            )
        )

    def add_dispensing_note(self, record: RawRecord, spec: RecordSpec, values: Values, target: str) -> None:
        getattr(self._ensure_dispensing(record, spec), target).append(_to_note(values))

    def add_provided_info(self, record: RawRecord, spec: RecordSpec, values: Values) -> None:
        self._ensure_dispensing(record, spec).provided_infos.append(ProvidedInfo(**values))

    def add_patient_entry(self, record: RawRecord, spec: RecordSpec, values: Values) -> None:
        self._ensure_dispensing(record, spec).patient_entries.append(PatientEntry(**values))

    def set_split(self, record: RawRecord, spec: RecordSpec, values: Values) -> None:
        if self.notebook.split is not None:
            self._duplicate(record, spec)
            return
        self.notebook.split = SplitControl(**values)


def _handle_record(record: RawRecord, spec: RecordSpec, builder: _NotebookBuilder) -> None:
    values = _read_fields(record, spec)
    notebook = builder.notebook
    record_no = spec.record_no

    if record_no == RecordNo.PATIENT:
        builder.set_patient(record, spec, values)
    elif record_no == RecordNo.PATIENT_REMARK:
        notebook.patient_remarks.append(PatientRemark(**values))
    elif record_no == RecordNo.OTC_DRUG:
        builder.add_otc_drug(values)
    elif record_no == RecordNo.OTC_DRUG_INGREDIENT:
        builder.add_otc_ingredient(record, spec, values)
    elif record_no == RecordNo.NOTEBOOK_MEMO:
        notebook.notebook_memos.append(NotebookMemo(**values))
    elif record_no == RecordNo.DISPENSING_DATE:
        builder.start_dispensing(values)
    elif record_no == RecordNo.DISPENSING_INSTITUTION:
        builder.set_dispensing_institution(record, spec, values)
    elif record_no == RecordNo.DISPENSING_STAFF:
        builder.set_dispensing_staff(record, spec, values)
    elif record_no == RecordNo.PRESCRIBING_INSTITUTION:
        builder.set_prescribing_institution(record, spec, values)
    elif record_no == RecordNo.PRESCRIBING_DOCTOR:
        builder.start_doctor_group(record, spec, values)
    elif record_no == RecordNo.DRUG:
        builder.add_drug(record, spec, values)
    elif record_no == RecordNo.DRUG_SUPPLEMENT:
        builder.add_drug_note(record, spec, values, "supplements")
    elif record_no == RecordNo.DRUG_CAUTION:
        builder.add_drug_note(record, spec, values, "cautions")
    elif record_no == RecordNo.USAGE:
        builder.set_usage(record, spec, values)
    elif record_no == RecordNo.USAGE_SUPPLEMENT:
        builder.add_rp_note(record, spec, values, "usage_supplements")
    elif record_no == RecordNo.PRESCRIPTION_CAUTION:
        builder.add_rp_note(record, spec, values, "prescription_cautions")
    elif record_no == RecordNo.CAUTION:
        builder.add_dispensing_note(record, spec, values, "cautions")
    elif record_no == RecordNo.PROVIDED_INFO:
        builder.add_provided_info(record, spec, values)
    elif record_no == RecordNo.REMAINING_DRUG_CHECK:
        builder.add_dispensing_note(record, spec, values, "remaining_drug_checks")
    elif record_no == RecordNo.REMARK:
        builder.add_dispensing_note(record, spec, values, "remarks")
    elif record_no == RecordNo.PATIENT_ENTRY:
        builder.add_patient_entry(record, spec, values)
    elif record_no == RecordNo.FAMILY_PHARMACIST:
        notebook.family_pharmacists.append(FamilyPharmacist(**values))
    elif record_no == RecordNo.SPLIT_CONTROL:
        builder.set_split(record, spec, values)


def parse(
    text: str,
    *,
    strict: bool = False,
    validate: bool = True,
    check_code_tables: bool = True,
    check_field_format: bool = True,
    keep_raw_records: bool = True,
    direction: Direction | None = None,
) -> ParseResult:
    """JAHIS電子版お薬手帳データのテキストを構造化データへ変換する。

    :param text: QRコードから読み取ったテキスト。複数シンボルに分割されている場合は
        :func:`medication_record_qr.qr.merge_split_parts` で結合してから渡す。
    :param strict: ``True`` の場合、警告もエラーとして扱い ``ok`` を ``False`` にする。
        構造化データ自体は ``strict`` でも取得できる。
    :param direction: 出力区分が読み取れない場合に仮定する情報提供方向。
    """
    issues = IssueCollector()
    records = parse_raw_records(text)

    if not records:
        issues.error(IssueCode.EMPTY_INPUT, "入力にレコードが1件も含まれていません。")
        return ParseResult(
            ok=False,
            notebook=MedicationNotebook(version=DEFAULT_VERSION),
            issues=issues.all,
            records=[],
        )

    header = records[0]
    has_version_record = is_version_record(header.record_no)
    version = header.record_no if has_version_record else DEFAULT_VERSION
    body = records[1:] if has_version_record else records

    if not has_version_record:
        issues.error(
            IssueCode.MISSING_VERSION_RECORD,
            f"先頭レコードがバージョンレコード(JAHISTC**)ではありません: {header.record_no}",
            line=header.line,
            record_no=header.record_no,
        )
    elif find_format_version(version) is None:
        issues.warn(
            IssueCode.UNKNOWN_VERSION,
            f"未知のバージョン情報です: {version}。解析は継続します。",
            line=header.line,
            record_no=version,
        )

    output_category = field_at(header, 1) if has_version_record else None
    if has_version_record and output_category is None:
        issues.error(
            IssueCode.MISSING_REQUIRED_FIELD,
            "バージョンレコードの必須項目「出力区分」が未設定です。",
            line=header.line,
            record_no=version,
            field_index=1,
            field_key="output_category",
        )
    elif output_category is not None and output_category not in {"1", "2"}:
        issues.warn(
            IssueCode.INVALID_CODE,
            f"バージョンレコードの「出力区分」が不正です: {output_category}",
            line=header.line,
            record_no=version,
            field_index=1,
            field_key="output_category",
        )

    resolved_direction = direction_of(output_category) or direction
    builder = _NotebookBuilder(version, issues, resolved_direction)
    builder.notebook.output_category = output_category

    options = ValidationOptions(check_code_tables=check_code_tables, check_field_format=check_field_format)

    for record in body:
        spec = find_record_spec(record.record_no)
        if spec is None:
            issues.warn(
                IssueCode.UNKNOWN_RECORD,
                f"未知のレコード番号です: {record.record_no}",
                line=record.line,
                record_no=record.record_no,
            )
            builder.notebook.unknown_records.append(
                UnknownRecord(record_no=record.record_no, fields=record.fields[1:], line=record.line)
            )
            continue

        if validate:
            validate_record(record, spec, issues, resolved_direction, options)
        _handle_record(record, spec, builder)

    for dispensing in builder.notebook.dispensings:
        for group in dispensing.doctor_groups:
            for rp in group.rps:
                if rp.usage is None:
                    issues.warn(
                        IssueCode.MISSING_USAGE,
                        f"RP{rp.rp_number} に用法レコード(301)がありません。",
                    )

    all_issues = issues.all
    ok = not all_issues if strict else not issues.has_error

    return ParseResult(
        ok=ok,
        notebook=builder.notebook,
        issues=all_issues,
        records=records if keep_raw_records else [],
    )


def parse_or_raise(
    text: str,
    *,
    strict: bool = False,
    validate: bool = True,
    check_code_tables: bool = True,
    check_field_format: bool = True,
    keep_raw_records: bool = True,
    direction: Direction | None = None,
) -> MedicationNotebook:
    """:func:`parse` と同じだが、エラーがある場合に :class:`ParseError` を送出する。"""
    result = parse(
        text,
        strict=strict,
        validate=validate,
        check_code_tables=check_code_tables,
        check_field_format=check_field_format,
        keep_raw_records=keep_raw_records,
        direction=direction,
    )
    if not result.ok:
        detail = "\n".join(
            f"- [{issue.level}] {issue.code}{f' ({issue.line}行目)' if issue.line else ''}: {issue.message}"
            for issue in result.issues
            if issue.level == "error" or strict
        )
        raise ParseError(f"お薬手帳データの解析に失敗しました:\n{detail}", result.issues)
    return result.notebook
