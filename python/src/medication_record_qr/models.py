"""JAHIS電子版お薬手帳データの構造化データモデル。

各データクラスは仕様書のレコードに対応し、属性名は
:mod:`medication_record_qr.spec.records` の ``FieldSpec.key`` と一致する。
値は仕様書どおりの文字列のまま保持する(年月日は ``YYYYMMDD`` または和暦 ``GYYMMDD``)。
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field, fields
from typing import Any, NamedTuple


@dataclass(frozen=True)
class RawRecord:
    """解析前のレコード(1行 = 1レコード)。"""

    #: 1始まりの行番号
    line: int
    #: レコード番号(バージョンレコードのみ ``JAHISTC**``)
    record_no: str
    #: カンマ区切りの全項目。``fields[0]`` はレコード番号。
    fields: tuple[str, ...]
    #: 元の行文字列
    raw: str


@dataclass(frozen=True)
class UnknownRecord:
    """仕様上定義されていないレコード。"""

    record_no: str
    fields: tuple[str, ...]
    line: int


@dataclass
class Patient:
    """患者情報レコード(1)。"""

    name: str | None = None
    #: 1:男 / 2:女
    sex: str | None = None
    birth_date: str | None = None
    postal_code: str | None = None
    address: str | None = None
    phone: str | None = None
    emergency_contact: str | None = None
    blood_type: str | None = None
    #: kg
    weight: str | None = None
    kana_name: str | None = None


@dataclass
class PatientRemark:
    """患者特記レコード(2)。"""

    #: 1:アレルギー歴 / 2:副作用歴 / 3:既往歴 / 9:その他
    remark_type: str | None = None
    text: str | None = None
    record_creator: str | None = None


@dataclass
class OtcDrugIngredient:
    """要指導医薬品・一般用医薬品成分レコード(31)。"""

    name: str | None = None
    code_type: str | None = None
    code: str | None = None
    record_creator: str | None = None


@dataclass
class OtcDrug:
    """要指導医薬品・一般用医薬品服用レコード(3)。"""

    name: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    record_creator: str | None = None
    #: 成分レコード(31)との紐づけに使う通番
    sequence: str | None = None
    jan_code: str | None = None
    ingredients: list[OtcDrugIngredient] = field(default_factory=list)


@dataclass
class NotebookMemo:
    """手帳メモレコード(4)。"""

    text: str | None = None
    input_date: str | None = None
    record_creator: str | None = None


@dataclass
class DispensingInstitution:
    """調剤－医療機関等レコード(11)。"""

    name: str | None = None
    prefecture_code: str | None = None
    score_table_code: str | None = None
    institution_code: str | None = None
    postal_code: str | None = None
    address: str | None = None
    phone: str | None = None
    record_creator: str | None = None


@dataclass
class DispensingStaff:
    """調剤－医師・薬剤師レコード(15)。"""

    name: str | None = None
    contact: str | None = None
    record_creator: str | None = None


@dataclass
class PrescribingInstitution:
    """処方－医療機関レコード(51)。"""

    name: str | None = None
    prefecture_code: str | None = None
    score_table_code: str | None = None
    institution_code: str | None = None
    record_creator: str | None = None


@dataclass
class PrescribingDoctor:
    """処方－医師レコード(55)。"""

    name: str | None = None
    department_name: str | None = None
    record_creator: str | None = None


@dataclass
class TextNote:
    """内容とレコード作成者のみを持つレコード(281/291/311/391/401/421/501)。"""

    text: str | None = None
    record_creator: str | None = None


@dataclass
class ProvidedInfo:
    """医療機関等提供情報レコード(411)。"""

    text: str | None = None
    info_type: str | None = None
    record_creator: str | None = None


@dataclass
class PatientEntry:
    """患者等記入レコード(601)。"""

    text: str | None = None
    input_date: str | None = None


@dataclass
class Drug:
    """薬品レコード(201)。"""

    name: str | None = None
    #: 用量
    dose: str | None = None
    unit_name: str | None = None
    #: 1:コードなし / 2:レセプト電算 / 3:厚労省 / 4:YJ / 6:HOT
    code_type: str | None = None
    code: str | None = None
    record_creator: str | None = None
    general_name: str | None = None
    general_name_code_type: str | None = None
    general_name_code: str | None = None
    #: 薬品補足レコード(281)
    supplements: list[TextNote] = field(default_factory=list)
    #: 薬品服用注意レコード(291)
    cautions: list[TextNote] = field(default_factory=list)


@dataclass
class Usage:
    """用法レコード(301)。"""

    name: str | None = None
    dispensing_quantity: str | None = None
    dispensing_unit: str | None = None
    #: 剤形コード(別表４)
    dosage_form_code: str | None = None
    code_type: str | None = None
    code: str | None = None
    record_creator: str | None = None


@dataclass
class Rp:
    """RP(処方指示)単位の情報。"""

    #: RP番号(1～)
    rp_number: str
    drugs: list[Drug] = field(default_factory=list)
    #: 用法レコード(301)。1RPに1レコード。
    usage: Usage | None = None
    #: 用法補足レコード(311)
    usage_supplements: list[TextNote] = field(default_factory=list)
    #: 処方服用注意レコード(391)
    prescription_cautions: list[TextNote] = field(default_factory=list)
    #: 対応する薬品レコード(201)より前に出現した薬品補足(281)・薬品服用注意(291)
    orphan_drug_notes: list[TextNote] = field(default_factory=list)


@dataclass
class DoctorGroup:
    """処方－医師レコード(55)を区切りとしたRPのまとまり。

    処方－医師レコードが出力されない場合は ``doctor`` を持たない1つのグループになる。
    """

    doctor: PrescribingDoctor | None = None
    rps: list[Rp] = field(default_factory=list)


@dataclass
class Dispensing:
    """調剤等年月日レコード(5)を起点とする1回の来院・来局の情報。"""

    date: str | None = None
    record_creator: str | None = None
    #: 調剤－医療機関等レコード(11)
    institution: DispensingInstitution | None = None
    #: 調剤－医師・薬剤師レコード(15)
    staff: DispensingStaff | None = None
    #: 処方－医療機関レコード(51)。薬局で調剤を行った場合のみ出力される。
    prescribing_institution: PrescribingInstitution | None = None
    #: 処方－医師レコード(55)ごとのRPのまとまり
    doctor_groups: list[DoctorGroup] = field(default_factory=list)
    #: 服用注意レコード(401)
    cautions: list[TextNote] = field(default_factory=list)
    #: 医療機関等提供情報レコード(411)
    provided_infos: list[ProvidedInfo] = field(default_factory=list)
    #: 残薬確認レコード(421)
    remaining_drug_checks: list[TextNote] = field(default_factory=list)
    #: 備考レコード(501)
    remarks: list[TextNote] = field(default_factory=list)
    #: 患者等記入レコード(601)
    patient_entries: list[PatientEntry] = field(default_factory=list)


@dataclass
class FamilyPharmacist:
    """かかりつけ薬剤師レコード(701)。"""

    name: str | None = None
    pharmacy_name: str | None = None
    contact: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    record_creator: str | None = None


@dataclass
class SplitControl:
    """分割制御レコード(911)。"""

    data_id: str | None = None
    total_count: str | None = None
    sequence: str | None = None


@dataclass
class MedicationNotebook:
    """お薬手帳データ全体。"""

    #: バージョン情報 (例: "JAHISTC08")
    version: str
    #: バージョン情報に対応する仕様書バージョン (例: ("2.5", "2.6"))
    spec_versions: tuple[str, ...] | None = None
    #: 出力区分 (1:医療機関等⇒患者等 / 2:患者等⇒医療機関等)
    output_category: str | None = None
    patient: Patient | None = None
    patient_remarks: list[PatientRemark] = field(default_factory=list)
    otc_drugs: list[OtcDrug] = field(default_factory=list)
    notebook_memos: list[NotebookMemo] = field(default_factory=list)
    #: 調剤等年月日が新しいものから古いものの順に並ぶ
    dispensings: list[Dispensing] = field(default_factory=list)
    family_pharmacists: list[FamilyPharmacist] = field(default_factory=list)
    #: 分割制御レコード(911)
    split: SplitControl | None = None
    #: 仕様上定義されていないレコード(前方互換のため保持する)
    unknown_records: list[UnknownRecord] = field(default_factory=list)


class RpContext(NamedTuple):
    """1つのRPと、それが属する調剤・医師の組み合わせ。"""

    dispensing: Dispensing
    doctor_group: DoctorGroup
    rp: Rp


class DrugContext(NamedTuple):
    """1つの薬品と、それが属する調剤・医師・RPの組み合わせ。"""

    dispensing: Dispensing
    doctor_group: DoctorGroup
    rp: Rp
    drug: Drug


def collect_rps(notebook: MedicationNotebook) -> Iterator[RpContext]:
    """お薬手帳データに含まれる全てのRPを、調剤・医師の情報とともに列挙する。"""
    for dispensing in notebook.dispensings:
        for group in dispensing.doctor_groups:
            for rp in group.rps:
                yield RpContext(dispensing, group, rp)


def collect_drugs(notebook: MedicationNotebook) -> Iterator[DrugContext]:
    """お薬手帳データに含まれる全ての薬品を列挙する。"""
    for dispensing, group, rp in collect_rps(notebook):
        for drug in rp.drugs:
            yield DrugContext(dispensing, group, rp, drug)


def field_values(obj: Any) -> dict[str, Any]:
    """データクラスの属性を浅くdictへ変換する(レコード出力用)。"""
    return {item.name: getattr(obj, item.name) for item in fields(obj)}
