"""構造化データ -> テキストの変換と、テキストの往復を確認する。"""

from __future__ import annotations

import pytest

from medication_record_qr import (
    Dispensing,
    DispensingInstitution,
    DoctorGroup,
    Drug,
    MedicationNotebook,
    Patient,
    PrescribingInstitution,
    Rp,
    SerializeError,
    Usage,
    parse,
    serialize,
    to_record_lines,
)

from .conftest import EXAMPLE_FIXTURES, read_fixture

#: 例8は出力データ例の項目数がレコードレイアウトと一致しないため、テキスト完全一致の対象から外す
ROUND_TRIP_EXAMPLES = [name for name in EXAMPLE_FIXTURES if name != "example-08.txt"]


class TestRoundTrip:
    @pytest.mark.parametrize("name", ROUND_TRIP_EXAMPLES)
    def test_text_round_trip_is_exact(self, name: str) -> None:
        text = read_fixture(name)
        assert serialize(parse(text).notebook) == text

    @pytest.mark.parametrize("name", EXAMPLE_FIXTURES)
    def test_structure_round_trip(self, name: str) -> None:
        notebook = parse(read_fixture(name)).notebook
        assert parse(serialize(notebook)).notebook == notebook


class TestOutputOrder:
    def test_version_record_comes_first(self) -> None:
        notebook = parse(read_fixture("example-01.txt")).notebook
        assert to_record_lines(notebook)[0] == "JAHISTC08,1"

    def test_split_control_record_comes_last(self) -> None:
        # 仕様書 表3-6 レコード出力順
        lines = to_record_lines(parse(read_fixture("split-part-1.txt")).notebook)
        assert lines[0] == "JAHISTC08,1"
        assert lines[-1] == "911,12345678901234,2,1"

    def test_version_can_be_overridden(self) -> None:
        notebook = parse(read_fixture("example-01.txt")).notebook
        assert serialize(notebook, version="JAHISTC07").startswith("JAHISTC07,1")

    def test_newline_can_be_changed(self) -> None:
        notebook = parse(read_fixture("example-01.txt")).notebook
        assert "\r" not in serialize(notebook, newline="\n")


class TestTrailingEmptyFields:
    def test_kept_by_default_and_omitted_on_request(self) -> None:
        notebook = parse(read_fixture("example-01.txt")).notebook
        assert to_record_lines(notebook)[1] == "1,鈴木 太郎,1,S330303,,,,,,,"
        assert to_record_lines(notebook, omit_trailing_empty_fields=True)[1] == "1,鈴木 太郎,1,S330303"

    def test_omitting_does_not_change_the_parsed_result(self) -> None:
        notebook = parse(read_fixture("example-04.txt")).notebook
        compact = serialize(notebook, omit_trailing_empty_fields=True)
        assert len(compact) < len(serialize(notebook))
        assert parse(compact).notebook == notebook


class TestInvalidValues:
    @pytest.mark.parametrize("name", ["鈴木,太郎", "鈴木\n太郎", "鈴木\r\n太郎"])
    def test_comma_and_newline_are_rejected(self, name: str) -> None:
        notebook = parse(read_fixture("example-01.txt")).notebook
        assert notebook.patient is not None
        notebook.patient.name = name
        with pytest.raises(SerializeError):
            serialize(notebook)

    def test_comma_error_message_mentions_the_workaround(self) -> None:
        notebook = parse(read_fixture("example-01.txt")).notebook
        assert notebook.patient is not None
        notebook.patient.name = "鈴木,太郎"
        with pytest.raises(SerializeError, match="全角カンマに置き換える"):
            serialize(notebook)


class TestUnknownRecords:
    def test_unknown_records_are_written_back(self) -> None:
        text = "JAHISTC08,1\r\n1,鈴木 太郎,1,S330303,,,,,,,\r\n999,将来の拡張,X"
        assert serialize(parse(text).notebook) == text


class TestBuildFromScratch:
    def test_notebook_built_in_code_serializes_to_the_spec_format(self) -> None:
        notebook = MedicationNotebook(
            version="JAHISTC08",
            output_category="1",
            patient=Patient(name="鈴木 太郎", sex="1", birth_date="S330303"),
            dispensings=[
                Dispensing(
                    date="R020410",
                    record_creator="1",
                    institution=DispensingInstitution(
                        name="株式会社 工業会薬局 駅前店",
                        prefecture_code="13",
                        score_table_code="4",
                        institution_code="1234567",
                        record_creator="1",
                    ),
                    prescribing_institution=PrescribingInstitution(
                        name="医療法人 工業会病院",
                        prefecture_code="13",
                        score_table_code="1",
                        institution_code="1234567",
                        record_creator="1",
                    ),
                    doctor_groups=[
                        DoctorGroup(
                            rps=[
                                Rp(
                                    rp_number="1",
                                    drugs=[
                                        Drug(
                                            name="ｺﾘｵﾊﾟﾝｶﾌﾟｾﾙ5mg",
                                            dose="4",
                                            unit_name="Ｃ",
                                            code_type="2",
                                            code="620004992",
                                            record_creator="1",
                                        ),
                                        Drug(
                                            name="ﾌｪﾛﾍﾞﾘﾝ配合錠",
                                            dose="4",
                                            unit_name="錠",
                                            code_type="2",
                                            code="620425801",
                                            record_creator="1",
                                        ),
                                    ],
                                    usage=Usage(
                                        name="【分２ 朝夕食後服用】",
                                        dispensing_quantity="5",
                                        dispensing_unit="日分",
                                        dosage_form_code="1",
                                        code_type="1",
                                        record_creator="1",
                                    ),
                                )
                            ]
                        )
                    ],
                )
            ],
        )

        assert serialize(notebook) == "\r\n".join(
            [
                "JAHISTC08,1",
                "1,鈴木 太郎,1,S330303,,,,,,,",
                "5,R020410,1",
                "11,株式会社 工業会薬局 駅前店,13,4,1234567,,,,1",
                "51,医療法人 工業会病院,13,1,1234567,1",
                "201,1,ｺﾘｵﾊﾟﾝｶﾌﾟｾﾙ5mg,4,Ｃ,2,620004992,1,,,",
                "201,1,ﾌｪﾛﾍﾞﾘﾝ配合錠,4,錠,2,620425801,1,,,",
                "301,1,【分２ 朝夕食後服用】,5,日分,1,1,,1",
            ]
        )
        assert parse(serialize(notebook)).issues == []
