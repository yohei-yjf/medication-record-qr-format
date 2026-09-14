"""仕様書 3.2.8「各種レコードレイアウト」のレコード定義表。

解析(:mod:`medication_record_qr.parser`)・出力(:mod:`medication_record_qr.serializer`)・
検証(:mod:`medication_record_qr.validation`)は、すべてこの定義表から駆動される。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


class RecordKind:
    """構造化データ上のレコード種別。"""

    VERSION = "version"
    PATIENT = "patient"
    PATIENT_REMARK = "patient_remark"
    OTC_DRUG = "otc_drug"
    OTC_DRUG_INGREDIENT = "otc_drug_ingredient"
    NOTEBOOK_MEMO = "notebook_memo"
    DISPENSING_DATE = "dispensing_date"
    DISPENSING_INSTITUTION = "dispensing_institution"
    DISPENSING_STAFF = "dispensing_staff"
    PRESCRIBING_INSTITUTION = "prescribing_institution"
    PRESCRIBING_DOCTOR = "prescribing_doctor"
    DRUG = "drug"
    DRUG_SUPPLEMENT = "drug_supplement"
    DRUG_CAUTION = "drug_caution"
    USAGE = "usage"
    USAGE_SUPPLEMENT = "usage_supplement"
    PRESCRIPTION_CAUTION = "prescription_caution"
    CAUTION = "caution"
    PROVIDED_INFO = "provided_info"
    REMAINING_DRUG_CHECK = "remaining_drug_check"
    REMARK = "remark"
    PATIENT_ENTRY = "patient_entry"
    FAMILY_PHARMACIST = "family_pharmacist"
    SPLIT_CONTROL = "split_control"


class RecordNo:
    """レコード番号。バージョンレコードのみレコード番号を持たない。"""

    PATIENT = "1"
    PATIENT_REMARK = "2"
    OTC_DRUG = "3"
    OTC_DRUG_INGREDIENT = "31"
    NOTEBOOK_MEMO = "4"
    DISPENSING_DATE = "5"
    DISPENSING_INSTITUTION = "11"
    DISPENSING_STAFF = "15"
    PRESCRIBING_INSTITUTION = "51"
    PRESCRIBING_DOCTOR = "55"
    DRUG = "201"
    DRUG_SUPPLEMENT = "281"
    DRUG_CAUTION = "291"
    USAGE = "301"
    USAGE_SUPPLEMENT = "311"
    PRESCRIPTION_CAUTION = "391"
    CAUTION = "401"
    PROVIDED_INFO = "411"
    REMAINING_DRUG_CHECK = "421"
    REMARK = "501"
    PATIENT_ENTRY = "601"
    FAMILY_PHARMACIST = "701"
    SPLIT_CONTROL = "911"


#: 仕様書 表3-2「データの型」(9:数値 / X:英数字、ピリオド、ハイフン / N:文字列)
FieldType = Literal["9", "X", "N"]

#: 情報の提供方向。仕様書の必須区分・レコード出力条件はこの方向によって異なる。
Direction = Literal["to_patient", "to_provider"]

#: 必須区分。
#: ``both`` はどちらの方向でも必須、``to_patient`` / ``to_provider`` はその方向でのみ必須、
#: ``conditional`` は備考欄に条件が記載されている項目、``None`` は任意。
RequiredKind = Literal["both", "to_patient", "to_provider", "conditional"]


@dataclass(frozen=True)
class FieldSpec:
    """レコード内の1項目の定義。"""

    #: レコード内の項目位置(レコード番号を 0 とした 1 始まりの連番)
    index: int
    #: 構造化データ上の属性名
    key: str
    #: 仕様書上の項目名称
    label: str
    #: 仕様書上の型
    type: FieldType
    #: 仕様書上のバイト数
    bytes: int
    required: RequiredKind | None = None
    #: 年月日項目(西暦8桁 YYYYMMDD / 和暦7桁 GYYMMDD)
    is_date: bool = False
    #: 参照するコード表名(:data:`medication_record_qr.spec.codes.CODE_TABLES` のキー)
    code_table: str | None = None
    note: str | None = None

    def is_required_for(self, direction: Direction | None) -> bool:
        """指定した提供方向において、この項目が必須かどうかを返す。"""
        if self.required == "both":
            return True
        if self.required is None or self.required == "conditional":
            return False
        # 提供方向が不明な場合は、どちらの方向でも必須である項目のみを必須として扱う
        return direction is not None and self.required == direction


@dataclass(frozen=True)
class RecordSpec:
    """1レコードの定義。"""

    record_no: str
    kind: str
    #: 仕様書上のレコード名称
    label: str
    #: 仕様書 表3-8「レコード出力条件」の同一№レコード出力
    repetition: str
    fields: tuple[FieldSpec, ...]
    #: 先頭項目がRP番号のレコード
    rp_scoped: bool = False
    note: str | None = None

    def field(self, key: str) -> FieldSpec:
        """属性名から項目定義を引く。"""
        for item in self.fields:
            if item.key == key:
                return item
        raise KeyError(f"{self.label}({self.record_no}) に項目 {key} は存在しません")


def _f(
    index: int,
    key: str,
    label: str,
    type_: FieldType,
    bytes_: int,
    *,
    required: RequiredKind | None = None,
    is_date: bool = False,
    code_table: str | None = None,
    note: str | None = None,
) -> FieldSpec:
    return FieldSpec(
        index=index,
        key=key,
        label=label,
        type=type_,
        bytes=bytes_,
        required=required,
        is_date=is_date,
        code_table=code_table,
        note=note,
    )


def _record_creator(index: int) -> FieldSpec:
    return _f(index, "record_creator", "レコード作成者", "9", 1, required="both", code_table="record_creator")


def _rp_number() -> FieldSpec:
    return _f(1, "rp_number", "RP番号", "9", 3, required="both")


def _rp_text_fields(label: str, bytes_: int) -> tuple[FieldSpec, ...]:
    """RP番号 + 内容 + レコード作成者 のレイアウト。"""
    return (_rp_number(), _f(2, "text", label, "N", bytes_, required="both"), _record_creator(3))


def _text_fields(label: str, bytes_: int) -> tuple[FieldSpec, ...]:
    """内容 + レコード作成者 のレイアウト。"""
    return (_f(1, "text", label, "N", bytes_, required="both"), _record_creator(2))


@dataclass(frozen=True)
class VersionRecordSpec:
    label: str = "バージョンレコード"
    fields: tuple[FieldSpec, ...] = field(
        default_factory=lambda: (
            _f(0, "version", "バージョン情報", "X", 9, required="both"),
            _f(1, "output_category", "出力区分", "9", 1, required="both", code_table="output_category"),
        )
    )


#: 表3-9 バージョンレコード
VERSION_RECORD_SPEC = VersionRecordSpec()

#: 表3-10〜表3-32 各種レコードレイアウト
RECORD_SPECS: tuple[RecordSpec, ...] = (
    RecordSpec(  # 表3-10
        record_no=RecordNo.PATIENT,
        kind=RecordKind.PATIENT,
        label="患者情報レコード",
        repetition="不可",
        fields=(
            _f(1, "name", "患者氏名", "N", 40, required="both"),
            _f(2, "sex", "患者性別", "9", 1, required="both", code_table="sex"),
            _f(3, "birth_date", "患者生年月日", "X", 8, required="both", is_date=True),
            _f(4, "postal_code", "患者郵便番号", "X", 8),
            _f(5, "address", "患者住所", "N", 800),
            _f(6, "phone", "患者電話番号", "X", 13),
            _f(7, "emergency_contact", "緊急連絡先", "N", 800),
            _f(8, "blood_type", "血液型", "N", 20),
            _f(9, "weight", "体重", "X", 7, note="kgで記録。整数3桁+小数点+小数3桁"),
            _f(10, "kana_name", "患者氏名カナ", "N", 40),
        ),
    ),
    RecordSpec(  # 表3-11
        record_no=RecordNo.PATIENT_REMARK,
        kind=RecordKind.PATIENT_REMARK,
        label="患者特記レコード",
        repetition="可",
        fields=(
            _f(1, "remark_type", "患者特記種別", "9", 1, required="both", code_table="patient_remark_type"),
            _f(2, "text", "患者特記内容", "N", 120, required="both"),
            _record_creator(3),
        ),
    ),
    RecordSpec(  # 表3-12
        record_no=RecordNo.OTC_DRUG,
        kind=RecordKind.OTC_DRUG,
        label="要指導医薬品・一般用医薬品服用レコード",
        repetition="可",
        fields=(
            _f(1, "name", "薬品名称", "N", 120, required="both"),
            _f(2, "start_date", "服用開始年月日", "X", 8, is_date=True),
            _f(3, "end_date", "服用終了年月日", "X", 8, is_date=True),
            _record_creator(4),
            _f(
                5,
                "sequence",
                "要指導医薬品・一般用医薬品レコード通番",
                "9",
                3,
                note="成分レコード(31)を記録する場合は必須",
            ),
            _f(6, "jan_code", "ＪＡＮコード", "9", 13),
        ),
    ),
    RecordSpec(  # 表3-13
        record_no=RecordNo.OTC_DRUG_INGREDIENT,
        kind=RecordKind.OTC_DRUG_INGREDIENT,
        label="要指導医薬品・一般用医薬品成分レコード",
        repetition="可",
        fields=(
            _f(1, "otc_drug_sequence", "要指導医薬品・一般用医薬品レコード通番", "9", 3, required="both"),
            _f(2, "name", "成分名", "N", 256, required="both"),
            _f(3, "code_type", "コード種別", "9", 1, required="both", code_table="ingredient_code_type"),
            _f(4, "code", "成分コード", "X", 20, note="コード種別が「1:コードなし」の場合は省略する"),
            _record_creator(5),
        ),
    ),
    RecordSpec(  # 表3-14
        record_no=RecordNo.NOTEBOOK_MEMO,
        kind=RecordKind.NOTEBOOK_MEMO,
        label="手帳メモレコード",
        repetition="可",
        fields=(
            _f(1, "text", "手帳メモ情報", "N", 400, required="both"),
            _f(2, "input_date", "メモ入力年月日", "X", 8, is_date=True),
            _record_creator(3),
        ),
    ),
    RecordSpec(  # 表3-15
        record_no=RecordNo.DISPENSING_DATE,
        kind=RecordKind.DISPENSING_DATE,
        label="調剤等年月日レコード",
        repetition="１調剤情報に１レコード",
        note="1回の来院・来局を表す調剤情報グループの開始レコード。",
        fields=(
            _f(1, "date", "調剤等年月日", "X", 8, required="both", is_date=True),
            _record_creator(2),
        ),
    ),
    RecordSpec(  # 表3-16
        record_no=RecordNo.DISPENSING_INSTITUTION,
        kind=RecordKind.DISPENSING_INSTITUTION,
        label="調剤－医療機関等レコード",
        repetition="１調剤情報に１レコード",
        fields=(
            _f(1, "name", "医療機関等名称", "N", 120, required="both"),
            _f(2, "prefecture_code", "医療機関等都道府県", "X", 2, required="to_patient", code_table="prefecture"),
            _f(3, "score_table_code", "医療機関等点数表", "X", 1, required="to_patient", code_table="score_table"),
            _f(
                4,
                "institution_code",
                "医療機関等コード",
                "X",
                7,
                required="to_patient",
                note="遡及指定申請中の場合は省略可。0から始まる場合も7桁固定で記録する",
            ),
            _f(5, "postal_code", "医療機関等郵便番号", "X", 8),
            _f(6, "address", "医療機関等住所", "N", 800),
            _f(7, "phone", "医療機関等電話番号", "X", 13),
            _record_creator(8),
        ),
    ),
    RecordSpec(  # 表3-17
        record_no=RecordNo.DISPENSING_STAFF,
        kind=RecordKind.DISPENSING_STAFF,
        label="調剤－医師・薬剤師レコード",
        repetition="１調剤情報に１レコード",
        fields=(
            _f(1, "name", "医師・薬剤師氏名", "N", 40, required="both"),
            _f(2, "contact", "医師・薬剤師連絡先", "N", 800),
            _record_creator(3),
        ),
    ),
    RecordSpec(  # 表3-18
        record_no=RecordNo.PRESCRIBING_INSTITUTION,
        kind=RecordKind.PRESCRIBING_INSTITUTION,
        label="処方－医療機関レコード",
        repetition="１調剤情報に１レコード",
        note="薬局で調剤を行った場合にのみ出力する。",
        fields=(
            _f(1, "name", "医療機関名称", "N", 120, required="both"),
            _f(2, "prefecture_code", "医療機関都道府県", "X", 2, required="to_patient", code_table="prefecture"),
            _f(3, "score_table_code", "医療機関点数表", "X", 1, required="to_patient", code_table="score_table"),
            _f(4, "institution_code", "医療機関コード", "X", 7, required="to_patient"),
            _record_creator(5),
        ),
    ),
    RecordSpec(  # 表3-19
        record_no=RecordNo.PRESCRIBING_DOCTOR,
        kind=RecordKind.PRESCRIBING_DOCTOR,
        label="処方－医師レコード",
        repetition="可",
        note=("当レコード以降、次の処方－医師レコードが出現するまでのRP情報は、この医師により処方されたものとみなす。"),
        fields=(
            _f(1, "name", "医師氏名", "N", 40, required="both"),
            _f(2, "department_name", "診療科名", "N", 80),
            _record_creator(3),
        ),
    ),
    RecordSpec(  # 表3-20
        record_no=RecordNo.DRUG,
        kind=RecordKind.DRUG,
        label="薬品レコード",
        repetition="１ＲＰに複数レコード出力可",
        rp_scoped=True,
        fields=(
            _rp_number(),
            _f(2, "name", "薬品名称", "N", 120, required="both"),
            _f(
                3,
                "dose",
                "用量",
                "X",
                12,
                required="to_patient",
                note="内服:1日量、内滴:全量、屯服:1回量、外用:全量、注射:全量、浸煎薬・湯薬:1日量、材料:全量",
            ),
            _f(4, "unit_name", "単位名", "N", 12, required="to_patient"),
            _f(5, "code_type", "薬品コード種別", "9", 1, required="to_patient", code_table="drug_code_type"),
            _f(
                6,
                "code",
                "薬品コード",
                "X",
                13,
                required="conditional",
                note="薬品コード種別が「1:コードなし」の場合は省略する",
            ),
            _record_creator(7),
            _f(8, "general_name", "一般名", "N", 120),
            _f(9, "general_name_code_type", "一般名コード種別", "9", 1, code_table="general_name_code_type"),
            _f(
                10,
                "general_name_code",
                "一般名コード",
                "X",
                12,
                note="一般名コード種別が「1:コードなし」の場合は省略する",
            ),
        ),
    ),
    RecordSpec(  # 表3-21
        record_no=RecordNo.DRUG_SUPPLEMENT,
        kind=RecordKind.DRUG_SUPPLEMENT,
        label="薬品補足レコード",
        repetition="１薬品に複数レコード出力可",
        rp_scoped=True,
        note="直前の薬品レコード(201)を補足する。",
        fields=_rp_text_fields("薬品補足情報", 100),
    ),
    RecordSpec(  # 表3-22
        record_no=RecordNo.DRUG_CAUTION,
        kind=RecordKind.DRUG_CAUTION,
        label="薬品服用注意レコード",
        repetition="１薬品に複数レコード出力可",
        rp_scoped=True,
        note="直前の薬品レコード(201)に対する注意事項。",
        fields=_rp_text_fields("内容", 400),
    ),
    RecordSpec(  # 表3-23
        record_no=RecordNo.USAGE,
        kind=RecordKind.USAGE,
        label="用法レコード",
        repetition="１ＲＰに１レコード",
        rp_scoped=True,
        fields=(
            _rp_number(),
            _f(
                2,
                "name",
                "用法名称",
                "N",
                100,
                required="conditional",
                note=(
                    "薬局が出力する場合、剤形コードが「材料」「その他」以外は必須。医療機関では出力困難な場合は省略可"
                ),
            ),
            _f(
                3,
                "dispensing_quantity",
                "調剤数量",
                "9",
                3,
                required="to_patient",
                note="内服:投与日数、内滴:1固定、屯服:投与回数、外用・注射:1固定、浸煎薬・湯薬:投与日数",
            ),
            _f(
                4,
                "dispensing_unit",
                "調剤単位",
                "N",
                100,
                required="to_patient",
                note="内服:日分、内滴:調剤、屯服:回分、注射・外用:調剤、浸煎・湯薬:日分、材料・その他:調剤",
            ),
            _f(5, "dosage_form_code", "剤形コード", "X", 2, required="to_patient", code_table="dosage_form"),
            _f(6, "code_type", "用法コード種別", "9", 1, required="to_patient", code_table="usage_code_type"),
            _f(
                7,
                "code",
                "用法コード",
                "X",
                16,
                required="conditional",
                note="用法コード種別が「1:コードなし」の場合は省略する",
            ),
            _record_creator(8),
        ),
    ),
    RecordSpec(  # 表3-24
        record_no=RecordNo.USAGE_SUPPLEMENT,
        kind=RecordKind.USAGE_SUPPLEMENT,
        label="用法補足レコード",
        repetition="１用法に複数レコード出力可",
        rp_scoped=True,
        fields=_rp_text_fields("用法補足情報", 100),
    ),
    RecordSpec(  # 表3-25
        record_no=RecordNo.PRESCRIPTION_CAUTION,
        kind=RecordKind.PRESCRIPTION_CAUTION,
        label="処方服用注意レコード",
        repetition="１ＲＰに複数レコード出力可",
        rp_scoped=True,
        fields=_rp_text_fields("内容", 400),
    ),
    RecordSpec(  # 表3-26
        record_no=RecordNo.CAUTION,
        kind=RecordKind.CAUTION,
        label="服用注意レコード",
        repetition="可",
        note="1回の来院・来局の投薬全体に対する服用上の注意。",
        fields=_text_fields("内容", 400),
    ),
    RecordSpec(  # 表3-27
        record_no=RecordNo.PROVIDED_INFO,
        kind=RecordKind.PROVIDED_INFO,
        label="医療機関等提供情報レコード",
        repetition="可",
        fields=(
            _f(1, "text", "内容", "N", 400, required="both"),
            _f(2, "info_type", "提供情報種別", "9", 2, required="both", code_table="provided_info_type"),
            _record_creator(3),
        ),
    ),
    RecordSpec(  # 表3-28
        record_no=RecordNo.REMAINING_DRUG_CHECK,
        kind=RecordKind.REMAINING_DRUG_CHECK,
        label="残薬確認レコード",
        repetition="可",
        fields=_text_fields("残薬内容", 400),
    ),
    RecordSpec(  # 表3-29
        record_no=RecordNo.REMARK,
        kind=RecordKind.REMARK,
        label="備考レコード",
        repetition="可",
        fields=_text_fields("備考情報", 400),
    ),
    RecordSpec(  # 表3-30
        record_no=RecordNo.PATIENT_ENTRY,
        kind=RecordKind.PATIENT_ENTRY,
        label="患者等記入レコード",
        repetition="可",
        fields=(
            _f(1, "text", "患者等記入情報", "N", 400, required="both"),
            _f(2, "input_date", "入力年月日", "X", 8, is_date=True),
        ),
    ),
    RecordSpec(  # 表3-31
        record_no=RecordNo.FAMILY_PHARMACIST,
        kind=RecordKind.FAMILY_PHARMACIST,
        label="かかりつけ薬剤師レコード",
        repetition="可",
        fields=(
            _f(1, "name", "かかりつけ薬剤師氏名", "N", 40, required="both"),
            _f(2, "pharmacy_name", "勤務先薬局名称", "N", 120, required="both"),
            _f(3, "contact", "連絡先", "N", 800, required="both"),
            _f(4, "start_date", "担当開始日", "X", 8, is_date=True),
            _f(5, "end_date", "担当終了日", "X", 8, is_date=True),
            _record_creator(6),
        ),
    ),
    RecordSpec(  # 表3-32
        record_no=RecordNo.SPLIT_CONTROL,
        kind=RecordKind.SPLIT_CONTROL,
        label="分割制御レコード",
        repetition="不可",
        note="データを分割した場合のみ、分割された各データの末尾に出力する。",
        fields=(
            _f(1, "data_id", "データ固有ID", "9", 14, required="both"),
            _f(2, "total_count", "分割数", "9", 3, required="both"),
            _f(3, "sequence", "データ連番", "9", 3, required="both", note="1～999"),
        ),
    ),
)

_SPEC_BY_RECORD_NO = {spec.record_no: spec for spec in RECORD_SPECS}
_SPEC_BY_KIND = {spec.kind: spec for spec in RECORD_SPECS}


def find_record_spec(record_no: str) -> RecordSpec | None:
    """レコード番号からレコード定義を引く。"""
    return _SPEC_BY_RECORD_NO.get(record_no)


def record_spec_of(kind: str) -> RecordSpec:
    """レコード種別からレコード定義を引く。"""
    spec = _SPEC_BY_KIND.get(kind)
    if spec is None:
        raise KeyError(f"レコード定義が見つかりません: {kind}")
    return spec


def direction_of(output_category: str | None) -> Direction | None:
    """出力区分(1/2)から情報の提供方向を返す。"""
    if output_category == "1":
        return "to_patient"
    if output_category == "2":
        return "to_provider"
    return None
