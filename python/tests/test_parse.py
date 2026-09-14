"""仕様書「付録１ お薬手帳イメージと出力データ例」の出力データ例を解析する。

例7・例11(かかりつけ薬剤師レコードの「連絡先」)と例8(医療機関等提供情報レコードの項目数)は、
出力データ例がレコードレイアウト(表3-31 / 表3-27)と一致していないため、
検証でエラー・警告が出ることを期待値としている(SPEC-NOTES.md 参照)。
"""

from __future__ import annotations

import pytest

from medication_record_qr import IssueCode, ParseError, collect_drugs, collect_rps, parse, parse_or_raise

from .conftest import CLEAN_EXAMPLES, EXAMPLE_FIXTURES, read_fixture


class TestAppendixExamples:
    @pytest.mark.parametrize("name", CLEAN_EXAMPLES)
    def test_parses_without_issues(self, name: str) -> None:
        result = parse(read_fixture(name))
        assert result.issues == []
        assert result.ok is True

    @pytest.mark.parametrize("name", EXAMPLE_FIXTURES)
    def test_reads_version_record(self, name: str) -> None:
        notebook = parse(read_fixture(name)).notebook
        assert notebook.version == "JAHISTC08"
        assert notebook.spec_versions is not None
        assert "2.6" in notebook.spec_versions
        assert notebook.output_category in {"1", "2"}


class TestExample01:
    """例1: 薬局で出力(内服薬のみ)。"""

    notebook = parse(read_fixture("example-01.txt")).notebook

    def test_patient_with_japanese_era_birth_date(self) -> None:
        patient = self.notebook.patient
        assert patient is not None
        assert patient.name == "鈴木 太郎"
        assert patient.sex == "1"
        assert patient.birth_date == "S330303"
        assert patient.kana_name is None

    def test_dispensing_group(self) -> None:
        assert len(self.notebook.dispensings) == 1
        dispensing = self.notebook.dispensings[0]
        assert dispensing.date == "R020410"
        assert dispensing.institution is not None
        assert dispensing.institution.name == "株式会社 工業会薬局 駅前店"
        assert dispensing.institution.prefecture_code == "13"
        assert dispensing.institution.score_table_code == "4"
        assert dispensing.institution.institution_code == "1234567"
        assert dispensing.prescribing_institution is not None
        assert dispensing.prescribing_institution.name == "医療法人 工業会病院"
        assert dispensing.prescribing_institution.score_table_code == "1"

    def test_rps(self) -> None:
        rps = [context.rp for context in collect_rps(self.notebook)]
        assert [rp.rp_number for rp in rps] == ["1", "2"]

        assert [drug.name for drug in rps[0].drugs] == ["ｺﾘｵﾊﾟﾝｶﾌﾟｾﾙ5mg", "ﾌｪﾛﾍﾞﾘﾝ配合錠"]
        first_drug = rps[0].drugs[0]
        assert (first_drug.dose, first_drug.unit_name) == ("4", "Ｃ")
        assert (first_drug.code_type, first_drug.code) == ("2", "620004992")

        usage = rps[0].usage
        assert usage is not None
        assert usage.name == "【分２ 朝夕食後服用】"
        assert (usage.dispensing_quantity, usage.dispensing_unit) == ("5", "日分")
        assert usage.dosage_form_code == "1"

        assert len(rps[1].drugs) == 3
        assert rps[1].usage is not None
        assert rps[1].usage.name == "【分３ 毎食後服用】"

    def test_single_doctor_group_without_doctor(self) -> None:
        groups = self.notebook.dispensings[0].doctor_groups
        assert len(groups) == 1
        assert groups[0].doctor is None


class TestExample02:
    """例2: 薬局で出力(内服薬以外を含む)。"""

    notebook = parse(read_fixture("example-02.txt")).notebook

    def test_dosage_form_codes(self) -> None:
        usages = [context.rp.usage for context in collect_rps(self.notebook)]
        assert [usage.dosage_form_code for usage in usages if usage] == ["1", "1", "5", "4", "9", "10"]
        # 材料・その他は用法名称が無くてもよい
        assert usages[4] is not None and usages[4].name is None
        assert usages[5] is not None and usages[5].name is None

    def test_drug_without_code(self) -> None:
        container = next(item.drug for item in collect_drugs(self.notebook) if item.drug.name == "容器")
        assert container.code_type == "1"
        assert container.code is None


class TestExample03:
    """例3: 薬品補足・用法補足を含む。"""

    notebook = parse(read_fixture("example-03.txt")).notebook

    def test_drug_supplements_attach_to_preceding_drug(self) -> None:
        rp = next(iter(collect_rps(self.notebook))).rp
        assert [note.text for note in rp.drugs[0].supplements] == ["朝：３Ｃ、昼：２Ｃ、夕：１Ｃ"]
        assert [note.text for note in rp.drugs[1].supplements] == ["朝：１錠、昼：３錠、夕：２錠"]
        assert rp.orphan_drug_notes == []

    def test_usage_supplements_attach_to_rp(self) -> None:
        rp = next(iter(collect_rps(self.notebook))).rp
        assert [note.text for note in rp.usage_supplements] == ["一包化"]

    def test_dispensing_staff_and_doctor_are_distinct(self) -> None:
        dispensing = self.notebook.dispensings[0]
        assert dispensing.staff is not None and dispensing.staff.name == "薬剤師 太郎"
        doctor = dispensing.doctor_groups[0].doctor
        assert doctor is not None and doctor.name == "工業会 次郎"


class TestExample04:
    """例4: 複数診療科での出力。"""

    notebook = parse(read_fixture("example-04.txt")).notebook

    def test_rps_are_grouped_by_doctor(self) -> None:
        groups = self.notebook.dispensings[0].doctor_groups
        assert len(groups) == 2
        assert [group.doctor.name for group in groups if group.doctor] == ["工業会 次郎", "佐藤 三郎"]
        assert [group.doctor.department_name for group in groups if group.doctor] == ["内科", "皮膚科"]
        assert [rp.rp_number for rp in groups[0].rps] == ["1", "2", "3", "4", "5"]
        assert [rp.rp_number for rp in groups[1].rps] == ["6", "7"]

    def test_dispensing_level_notes(self) -> None:
        dispensing = self.notebook.dispensings[0]
        assert dispensing.remaining_drug_checks[0].text == "服用忘れによりｺﾘｵﾊﾟﾝｶﾌﾟｾﾙ12錠残薬あり"
        assert dispensing.remarks[0].text == "正しい飲み方は薬袋等をご覧下さい。"


class TestExample05And06:
    """例5・例6: 医療機関で出力。"""

    def test_rps_without_prescribing_institution(self) -> None:
        result = parse(read_fixture("example-05.txt"))
        assert result.issues == []
        assert result.notebook.dispensings[0].prescribing_institution is None
        assert len(list(collect_rps(result.notebook))) == 2

    def test_usage_name_may_be_omitted_by_medical_institution(self) -> None:
        result = parse(read_fixture("example-06.txt"))
        assert result.issues == []
        assert all(
            context.rp.usage is not None and context.rp.usage.name is None for context in collect_rps(result.notebook)
        )

    def test_usage_name_is_required_for_pharmacy_output(self) -> None:
        # 表3-23の条件付き必須: 処方－医療機関レコードがある(=薬局で調剤した)場合は用法名称が必須
        text = read_fixture("example-06.txt").replace(
            "11,医療法人 工業会病院,13,1,1234567,,,,1",
            "11,株式会社 工業会薬局 駅前店,13,4,1234567,,,,1\r\n51,医療法人 工業会病院,13,1,1234567,1",
        )
        result = parse(text)
        assert result.ok is False
        assert any("「用法名称」が未設定" in issue.message for issue in result.issues)


class TestExample07:
    """例7: 患者特記・服用注意・かかりつけ薬剤師。"""

    result = parse(read_fixture("example-07.txt"))

    def test_patient_all_fields(self) -> None:
        patient = self.result.notebook.patient
        assert patient is not None
        assert patient.postal_code == "105-0004"
        assert patient.address == "東京都港区新橋○丁目"
        assert patient.phone == "03-0000-0000"
        assert patient.emergency_contact == "090-0000-0000"
        assert patient.blood_type == "Ｂ＋"
        assert patient.weight == "63.7"

    def test_patient_remarks(self) -> None:
        remarks = self.result.notebook.patient_remarks
        assert [(remark.remark_type, remark.text) for remark in remarks] == [
            ("1", "乳製品"),
            ("2", "セフェム系（発熱）"),
            ("3", "狭心症（2011年～）"),
            ("9", "嚥下困難"),
        ]

    def test_caution_records_are_distinguished(self) -> None:
        rp = next(iter(collect_rps(self.result.notebook))).rp
        assert "グレープフルーツジュース" in (rp.drugs[0].cautions[0].text or "")
        assert "めまい等が現れることがある" in (rp.prescription_cautions[0].text or "")
        dispensing = self.result.notebook.dispensings[0]
        assert dispensing.cautions[0].text == "他の薬を併用する際は、相談してください。"

    def test_contact_is_reported_as_missing(self) -> None:
        pharmacist = self.result.notebook.family_pharmacists[0]
        assert pharmacist.name == "薬剤師 太郎"
        assert pharmacist.pharmacy_name == "工業会薬局 駅前店"
        assert pharmacist.contact is None

        issue = next(item for item in self.result.issues if item.code == IssueCode.MISSING_REQUIRED_FIELD)
        assert issue.record_no == "701"
        assert issue.field_key == "contact"


class TestExample08:
    """例8: 医薬品等を提供せずに情報提供を行う場合。"""

    result = parse(read_fixture("example-08.txt"))

    def test_provided_info(self) -> None:
        dispensing = self.result.notebook.dispensings[0]
        assert dispensing.date == "R020410"
        assert dispensing.staff is not None and dispensing.staff.name == "工業会 次郎"
        assert dispensing.provided_infos[0].text == "嚥下困難が見られるため、錠剤は粉砕して投与する。"
        assert dispensing.provided_infos[0].info_type == "31"
        assert dispensing.doctor_groups == []

    def test_field_count_mismatch_is_reported(self) -> None:
        codes = [issue.code for issue in self.result.issues]
        assert IssueCode.TOO_MANY_FIELDS in codes
        assert IssueCode.MISSING_REQUIRED_FIELD in codes


class TestExample09:
    """例9: 複数調剤日をまとめて出力。"""

    notebook = parse(read_fixture("example-09.txt")).notebook

    def test_dispensings_are_split_by_date(self) -> None:
        assert [dispensing.date for dispensing in self.notebook.dispensings] == ["R020410", "R020407"]
        staff_names = [dispensing.staff.name for dispensing in self.notebook.dispensings if dispensing.staff]
        assert staff_names == ["薬剤師 次郎", "薬剤師 太郎"]

    def test_rp_numbers_restart_per_dispensing(self) -> None:
        assert [rp.rp_number for rp in self.notebook.dispensings[0].doctor_groups[0].rps] == ["1", "2"]
        assert [rp.rp_number for rp in self.notebook.dispensings[1].doctor_groups[0].rps] == ["1", "2", "3"]


class TestExample10:
    """例10: 患者等から医療機関・薬局への提供。"""

    result = parse(read_fixture("example-10.txt"))

    def test_optional_fields_may_be_omitted(self) -> None:
        assert self.result.issues == []
        assert self.result.notebook.output_category == "2"
        institution = self.result.notebook.dispensings[0].institution
        assert institution is not None
        assert institution.name == "株式会社 工業会薬局 駅前店"
        assert institution.prefecture_code is None
        assert institution.institution_code is None

    def test_patient_entry(self) -> None:
        entry = self.result.notebook.dispensings[0].patient_entries[0]
        assert entry.text == "朝に薬を飲んだ後、めまいがあった"
        assert entry.input_date == "R020407"

    def test_same_data_is_incomplete_for_output_category_1(self) -> None:
        result = parse(read_fixture("example-10.txt").replace("JAHISTC08,2", "JAHISTC08,1"))
        assert result.ok is False
        assert any(issue.field_key == "prefecture_code" for issue in result.issues)


class TestExample11:
    """例11: 要指導医薬品・一般用医薬品と手帳メモ。"""

    notebook = parse(read_fixture("example-11.txt")).notebook

    def test_otc_ingredients_are_linked_by_sequence(self) -> None:
        assert len(self.notebook.otc_drugs) == 2

        first = self.notebook.otc_drugs[0]
        assert first.name == "ﾊﾞﾌｧﾘﾝ"
        assert (first.start_date, first.end_date) == ("R020406", "R020409")
        assert first.sequence == "1"
        assert [item.name for item in first.ingredients] == [
            "イブプロフェン",
            "アセトアミノフェン",
            "無水カフェイン",
        ]

        second = self.notebook.otc_drugs[1]
        assert len(second.ingredients) == 3
        assert second.ingredients[2].code_type == "1"
        assert second.ingredients[2].code is None

    def test_notebook_memos(self) -> None:
        memos = self.notebook.notebook_memos
        assert [(memo.text, memo.input_date, memo.record_creator) for memo in memos] == [
            ("健康診断", "R020411", "2"),
            ("インフルエンザ予防接種", "R020331", "2"),
        ]

    def test_multiple_dispensings_and_family_pharmacist(self) -> None:
        assert len(self.notebook.dispensings) == 2
        assert self.notebook.family_pharmacists[0].name == "薬剤師 次郎"


class TestErrorHandling:
    def test_empty_input(self) -> None:
        result = parse("")
        assert result.ok is False
        assert result.issues[0].code == IssueCode.EMPTY_INPUT

    def test_missing_version_record(self) -> None:
        result = parse("1,鈴木 太郎,1,S330303")
        assert result.ok is False
        assert IssueCode.MISSING_VERSION_RECORD in [issue.code for issue in result.issues]

    def test_unknown_version_is_a_warning(self) -> None:
        result = parse("JAHISTC99,1\r\n1,鈴木 太郎,1,S330303")
        assert result.ok is True
        assert IssueCode.UNKNOWN_VERSION in [issue.code for issue in result.issues]
        assert result.notebook.spec_versions is None

    def test_missing_output_category(self) -> None:
        result = parse("JAHISTC08\r\n1,鈴木 太郎,1,S330303")
        assert result.ok is False
        assert any(issue.field_key == "output_category" for issue in result.issues)

    def test_missing_required_field(self) -> None:
        result = parse("JAHISTC08,1\r\n1,鈴木 太郎")
        assert result.ok is False
        issue = next(item for item in result.issues if item.code == IssueCode.MISSING_REQUIRED_FIELD)
        assert issue.field_key == "sex"
        assert issue.line == 2

    def test_drug_code_required_when_code_type_is_not_1(self) -> None:
        result = parse(
            "\r\n".join(
                [
                    "JAHISTC08,1",
                    "1,鈴木 太郎,1,S330303",
                    "5,R020410,1",
                    "201,1,ﾉﾙﾊﾞｽｸ錠2.5mg,1,錠,2,,1,,,",
                ]
            )
        )
        assert result.ok is False
        assert any("「薬品コード」は必須" in issue.message for issue in result.issues)

    def test_invalid_code_and_date_are_warnings(self) -> None:
        result = parse("JAHISTC08,1\r\n1,鈴木 太郎,9,20250230,,,,,,,")
        assert result.ok is True
        codes = [issue.code for issue in result.issues]
        assert IssueCode.INVALID_CODE in codes
        assert IssueCode.INVALID_DATE in codes

    def test_field_too_long_is_a_warning(self) -> None:
        result = parse(f"JAHISTC08,1\r\n1,{'あ' * 21},1,S330303")
        assert IssueCode.FIELD_TOO_LONG in [issue.code for issue in result.issues]

    def test_strict_mode(self) -> None:
        text = "JAHISTC08,1\r\n1,鈴木 太郎,9,S330303,,,,,,,"
        assert parse(text).ok is True
        assert parse(text, strict=True).ok is False

    def test_validation_can_be_disabled(self) -> None:
        text = "JAHISTC08,1\r\n1,鈴木 太郎,9,20250230,,,,,,,"
        assert parse(text, validate=False).issues == []
        assert all(issue.code != IssueCode.INVALID_CODE for issue in parse(text, check_code_tables=False).issues)

    def test_unknown_records_are_preserved(self) -> None:
        result = parse("JAHISTC08,1\r\n1,鈴木 太郎,1,S330303\r\n999,将来の拡張,X")
        assert result.ok is True
        assert len(result.notebook.unknown_records) == 1
        unknown = result.notebook.unknown_records[0]
        assert (unknown.record_no, unknown.fields, unknown.line) == ("999", ("将来の拡張", "X"), 3)

    def test_records_before_dispensing_date(self) -> None:
        result = parse("JAHISTC08,1\r\n1,鈴木 太郎,1,S330303\r\n11,株式会社 工業会薬局 駅前店,13,4,1234567,,,,1")
        assert result.ok is True
        assert IssueCode.ORPHAN_RECORD in [issue.code for issue in result.issues]
        institution = result.notebook.dispensings[0].institution
        assert institution is not None and institution.name == "株式会社 工業会薬局 駅前店"

    def test_duplicate_record_keeps_the_first(self) -> None:
        result = parse(
            "\r\n".join(
                [
                    "JAHISTC08,1",
                    "1,鈴木 太郎,1,S330303",
                    "5,R020410,1",
                    "11,薬局A,13,4,1234567,,,,1",
                    "11,薬局B,13,4,7654321,,,,1",
                ]
            )
        )
        assert IssueCode.DUPLICATE_RECORD in [issue.code for issue in result.issues]
        institution = result.notebook.dispensings[0].institution
        assert institution is not None and institution.name == "薬局A"

    @pytest.mark.parametrize("newline", ["\r\n", "\n", "\r"])
    def test_accepts_any_newline(self, newline: str) -> None:
        notebook = parse(newline.join(["JAHISTC08,1", "1,鈴木 太郎,1,S330303"])).notebook
        assert notebook.patient is not None and notebook.patient.name == "鈴木 太郎"

    def test_ignores_trailing_eof_character(self) -> None:
        notebook = parse("JAHISTC08,1\r\n1,鈴木 太郎,1,S330303\r\n\x1a").notebook
        assert notebook.patient is not None and notebook.patient.name == "鈴木 太郎"

    def test_parse_or_raise(self) -> None:
        parse_or_raise(read_fixture("example-01.txt"))
        with pytest.raises(ParseError, match="解析に失敗"):
            parse_or_raise("1,鈴木 太郎")
