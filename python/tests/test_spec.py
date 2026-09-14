"""レコード定義表・コード表・バージョン情報が仕様書と一致していることを確認する。"""

from __future__ import annotations

import pytest

from medication_record_qr import (
    CODE_TABLES,
    FORMAT_VERSIONS,
    RECORD_SPECS,
    TARGET_SPEC_VERSION,
    RecordKind,
    RecordNo,
    describe_code,
    find_record_spec,
    is_valid_date,
    is_version_record,
    record_spec_of,
    spec_versions_of,
    version_number_of,
)


class TestRecordLayouts:
    """仕様書 3.2.8 各種レコードレイアウト。"""

    def test_record_numbers_and_kinds_are_unique(self) -> None:
        assert len({spec.record_no for spec in RECORD_SPECS}) == len(RECORD_SPECS)
        assert len({spec.kind for spec in RECORD_SPECS}) == len(RECORD_SPECS)

    def test_field_indexes_are_sequential(self) -> None:
        for spec in RECORD_SPECS:
            assert [item.index for item in spec.fields] == list(range(1, len(spec.fields) + 1)), spec.label

    def test_field_keys_are_unique_within_record(self) -> None:
        for spec in RECORD_SPECS:
            keys = [item.key for item in spec.fields]
            assert len(set(keys)) == len(keys), spec.label

    def test_code_table_references_exist(self) -> None:
        for spec in RECORD_SPECS:
            for item in spec.fields:
                if item.code_table is not None:
                    assert item.code_table in CODE_TABLES, f"{spec.label}/{item.label}"

    def test_every_record_kind_has_a_spec(self) -> None:
        kinds = [
            value
            for name, value in vars(RecordKind).items()
            if not name.startswith("_") and value != RecordKind.VERSION
        ]
        for kind in kinds:
            assert record_spec_of(kind) is not None

    def test_patient_record_matches_table_3_10(self) -> None:
        spec = find_record_spec(RecordNo.PATIENT)
        assert spec is not None
        assert [(item.label, item.type, item.bytes) for item in spec.fields] == [
            ("患者氏名", "N", 40),
            ("患者性別", "9", 1),
            ("患者生年月日", "X", 8),
            ("患者郵便番号", "X", 8),
            ("患者住所", "N", 800),
            ("患者電話番号", "X", 13),
            ("緊急連絡先", "N", 800),
            ("血液型", "N", 20),
            ("体重", "X", 7),
            ("患者氏名カナ", "N", 40),
        ]

    def test_drug_record_matches_table_3_20(self) -> None:
        spec = find_record_spec(RecordNo.DRUG)
        assert spec is not None
        assert [(item.label, item.type, item.bytes) for item in spec.fields] == [
            ("RP番号", "9", 3),
            ("薬品名称", "N", 120),
            ("用量", "X", 12),
            ("単位名", "N", 12),
            ("薬品コード種別", "9", 1),
            ("薬品コード", "X", 13),
            ("レコード作成者", "9", 1),
            ("一般名", "N", 120),
            ("一般名コード種別", "9", 1),
            ("一般名コード", "X", 12),
        ]

    def test_split_control_record_matches_table_3_32(self) -> None:
        spec = find_record_spec(RecordNo.SPLIT_CONTROL)
        assert spec is not None
        assert [(item.label, item.type, item.bytes) for item in spec.fields] == [
            ("データ固有ID", "9", 14),
            ("分割数", "9", 3),
            ("データ連番", "9", 3),
        ]

    def test_required_fields_depend_on_direction(self) -> None:
        spec = find_record_spec(RecordNo.DISPENSING_INSTITUTION)
        assert spec is not None

        prefecture = spec.field("prefecture_code")
        assert prefecture.is_required_for("to_patient") is True
        assert prefecture.is_required_for("to_provider") is False

        name = spec.field("name")
        assert name.is_required_for("to_patient") is True
        assert name.is_required_for("to_provider") is True

        # 提供方向が不明な場合は、両方向で必須の項目のみを必須として扱う
        assert prefecture.is_required_for(None) is False
        assert name.is_required_for(None) is True


class TestCodeTables:
    """別表 各種コード表。"""

    def test_era_codes(self) -> None:
        assert dict(CODE_TABLES["era"].values) == {
            "M": "明治",
            "T": "大正",
            "S": "昭和",
            "H": "平成",
            "R": "令和",
        }

    def test_prefecture_codes(self) -> None:
        table = CODE_TABLES["prefecture"]
        assert len(table.values) == 47
        assert describe_code(table, "01") == "北海道"
        assert describe_code(table, "13") == "東京"
        assert describe_code(table, "47") == "沖縄"
        assert describe_code(table, "48") is None

    def test_score_table_codes(self) -> None:
        assert dict(CODE_TABLES["score_table"].values) == {"1": "医科", "3": "歯科", "4": "調剤"}

    def test_dosage_form_codes(self) -> None:
        assert dict(CODE_TABLES["dosage_form"].values) == {
            "1": "内服",
            "2": "内滴",
            "3": "屯服",
            "4": "注射",
            "5": "外用",
            "6": "浸煎",
            "7": "湯",
            "9": "材料",
            "10": "その他",
        }

    def test_record_creator_and_drug_code_type(self) -> None:
        assert dict(CODE_TABLES["record_creator"].values) == {
            "1": "医療関係者",
            "2": "患者等",
            "8": "その他",
            "9": "不明",
        }
        assert dict(CODE_TABLES["drug_code_type"].values) == {
            "1": "コードなし",
            "2": "レセプト電算コード",
            "3": "厚労省コード",
            "4": "YJコード",
            "6": "HOTコード",
        }
        assert list(CODE_TABLES["provided_info_type"].values) == ["30", "31", "99"]


class TestVersion:
    """仕様書 3.1 バージョン情報。"""

    def test_target_spec_version_uses_jahistc08(self) -> None:
        versions = spec_versions_of("JAHISTC08")
        assert versions is not None
        assert TARGET_SPEC_VERSION in versions
        assert version_number_of("JAHISTC08") == 8

    def test_version_map_matches_revision_history(self) -> None:
        assert {info.version: info.spec_versions for info in FORMAT_VERSIONS} == {
            "JAHISTC01": ("1.0",),
            "JAHISTC02": ("1.1",),
            "JAHISTC03": ("2.0",),
            "JAHISTC04": ("2.1",),
            "JAHISTC05": ("2.2",),
            "JAHISTC06": ("2.3",),
            "JAHISTC07": ("2.4",),
            "JAHISTC08": ("2.5", "2.6"),
        }

    @pytest.mark.parametrize(
        ("value", "expected"),
        [("JAHISTC08", True), ("JAHISTC12", True), ("JAHISTC8", False), ("1", False)],
    )
    def test_version_record_pattern(self, value: str, expected: bool) -> None:
        assert is_version_record(value) is expected


class TestDateFormat:
    @pytest.mark.parametrize("value", ["20200410", "R020410", "S330303", "H280411", "20200229"])
    def test_valid_dates(self, value: str) -> None:
        assert is_valid_date(value) is True

    @pytest.mark.parametrize("value", ["20200431", "20250230", "X020410", "R021310", "2020041", ""])
    def test_invalid_dates(self, value: str) -> None:
        assert is_valid_date(value) is False
