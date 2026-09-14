"""QRコードの生成・読み取りと、複数シンボルへの分割・結合を確認する。"""

from __future__ import annotations

import pytest

from medication_record_qr import (
    QrCodeError,
    byte_length,
    decode_qr_from_png,
    encode_notebook_to_data_uris,
    encode_notebook_to_pngs,
    encode_notebook_to_svgs,
    encode_text_to_png,
    merge_split_parts,
    parse,
    read_notebook_from_pngs,
    serialize,
    split_for_qr,
    to_qr_texts,
    unencodable_characters,
)

from .conftest import EXAMPLE_FIXTURES, read_fixture

pytest.importorskip("segno", reason="QRコードの生成には segno が必要です")
pytest.importorskip("zxingcpp", reason="QRコードの読み取りには zxing-cpp が必要です")
pytest.importorskip("PIL", reason="QRコードの読み取りには Pillow が必要です")


def notebook_of(name: str):  # type: ignore[no-untyped-def]
    return parse(read_fixture(name)).notebook


class TestQrRoundTrip:
    @pytest.mark.parametrize("name", EXAMPLE_FIXTURES)
    def test_every_example_survives_a_qr_round_trip(self, name: str) -> None:
        text = read_fixture(name)
        assert decode_qr_from_png(encode_text_to_png(text)) == text

    def test_notebook_round_trip(self) -> None:
        notebook = notebook_of("example-11.txt")
        pngs = encode_notebook_to_pngs(notebook)
        assert len(pngs) == 1

        result = read_notebook_from_pngs(pngs)
        assert result.merge_issues == []
        assert result.notebook == notebook

    def test_shift_jis_is_used_by_default(self) -> None:
        text = read_fixture("example-01.txt")
        assert byte_length("あ", "cp932") == 2
        assert byte_length("あ", "utf-8") == 3

        png = encode_text_to_png(text)
        assert decode_qr_from_png(png, encoding="cp932") == text

        # 文字コードを取り違えるとエラーになる
        with pytest.raises(QrCodeError, match="文字コードの指定"):
            decode_qr_from_png(png, encoding="utf-8")

        # errors="replace" を指定すれば読み取れる範囲だけ取り出せる(内容は壊れる)
        assert decode_qr_from_png(png, encoding="utf-8", errors="replace") != text

    def test_utf8_round_trip(self) -> None:
        text = read_fixture("example-01.txt")
        png = encode_text_to_png(text, encoding="utf-8")
        assert decode_qr_from_png(png, encoding="utf-8") == text

    def test_half_width_kana_survives(self) -> None:
        text = read_fixture("example-02.txt")
        assert "ｺﾘｵﾊﾟﾝｶﾌﾟｾﾙ5mg" in text
        assert decode_qr_from_png(encode_text_to_png(text)) == text

    def test_full_width_plus_and_tilde_survive(self) -> None:
        # Python 標準の shift_jis コーデックでは表現できない文字を含む
        text = read_fixture("example-07.txt")
        assert "Ｂ＋" in text
        assert "～" in text
        assert decode_qr_from_png(encode_text_to_png(text)) == text

    def test_svg_and_data_uri(self) -> None:
        notebook = notebook_of("example-01.txt")
        assert encode_notebook_to_svgs(notebook)[0].lstrip().startswith("<?xml")
        assert encode_notebook_to_data_uris(notebook)[0].startswith("data:image/png;base64,")

    def test_error_correction_level_and_symbol_version(self) -> None:
        text = read_fixture("example-01.txt")
        low = encode_text_to_png(text, error="l")
        high = encode_text_to_png(text, error="h")
        assert decode_qr_from_png(low) == text
        assert decode_qr_from_png(high) == text
        assert len(high) > len(low)

        fixed = encode_text_to_png(text, symbol_version=20)
        assert decode_qr_from_png(fixed) == text

    def test_image_and_text_options_can_be_mixed(self) -> None:
        notebook = notebook_of("example-04.txt")
        pngs = encode_notebook_to_pngs(
            notebook,
            scale=6,
            border=2,
            error="h",
            omit_trailing_empty_fields=True,
            max_bytes_per_symbol=1800,
        )
        assert len(pngs) == 1
        assert decode_qr_from_png(pngs[0]) == serialize(notebook, omit_trailing_empty_fields=True)

        assert encode_notebook_to_data_uris(notebook, scale=2)[0].startswith("data:image/png;base64,")

    def test_image_without_qr_code_raises(self) -> None:
        with pytest.raises(QrCodeError):
            decode_qr_from_png(b"not a png")

    def test_unencodable_characters_are_reported(self) -> None:
        assert unencodable_characters("鈴木 太郎") == []
        assert unencodable_characters("𠮟る") == ["𠮟"]


class TestSplit:
    """仕様書 3.2.9(3) データを分割した場合の出力方法。"""

    def test_small_data_is_not_split(self) -> None:
        text = read_fixture("example-01.txt")
        assert split_for_qr(text) == [text]

    def test_split_adds_split_control_record(self) -> None:
        text = read_fixture("example-04.txt")
        parts = split_for_qr(text, max_bytes_per_symbol=400, data_id="12345678901234")

        assert len(parts) > 1
        for index, part in enumerate(parts, start=1):
            assert byte_length(part) <= 400
            lines = part.split("\r\n")
            # 先頭はバージョンレコード、末尾は分割制御レコード
            assert lines[0] == "JAHISTC08,1"
            assert lines[-1] == f"911,12345678901234,{len(parts)},{index}"

    def test_merge_restores_the_original_text(self) -> None:
        text = read_fixture("example-04.txt")
        parts = split_for_qr(text, max_bytes_per_symbol=400)
        merged = merge_split_parts(parts)

        assert merged.issues == []
        assert merged.total_count == len(parts)
        assert merged.text == text

    def test_merge_sorts_by_sequence(self) -> None:
        text = read_fixture("example-04.txt")
        parts = split_for_qr(text, max_bytes_per_symbol=400)
        assert merge_split_parts(list(reversed(parts))).text == text

    def test_spec_split_example_can_be_merged(self) -> None:
        merged = merge_split_parts([read_fixture("split-part-2.txt"), read_fixture("split-part-1.txt")])
        assert merged.issues == []
        assert merged.data_id == "12345678901234"
        assert merged.total_count == 2

        result = parse(merged.text)
        assert result.issues == []
        groups = result.notebook.dispensings[0].doctor_groups
        assert [group.doctor.name for group in groups if group.doctor] == ["工業会 次郎", "佐藤 三郎"]
        assert sum(len(group.rps) for group in groups) == 7

    def test_split_qr_codes_can_be_read_back(self) -> None:
        notebook = notebook_of("example-11.txt")
        pngs = encode_notebook_to_pngs(notebook, max_bytes_per_symbol=700)
        assert len(pngs) > 1

        result = read_notebook_from_pngs(pngs)
        assert result.merge_issues == []
        assert result.notebook == notebook

    def test_split_can_be_disabled(self) -> None:
        notebook = notebook_of("example-04.txt")
        assert len(to_qr_texts(notebook, split=False, max_bytes_per_symbol=400)) == 1

    def test_record_larger_than_the_limit_raises(self) -> None:
        with pytest.raises(ValueError):
            split_for_qr(read_fixture("example-04.txt"), max_bytes_per_symbol=80)

    def test_mixed_data_ids_are_reported(self) -> None:
        text = read_fixture("example-04.txt")
        first = split_for_qr(text, max_bytes_per_symbol=400, data_id="11111111111111")
        second = split_for_qr(text, max_bytes_per_symbol=400, data_id="22222222222222")
        merged = merge_split_parts([first[0], second[1]])

        assert any("データ固有ID" in issue.message for issue in merged.issues)

    def test_missing_and_duplicated_symbols_are_reported(self) -> None:
        parts = split_for_qr(read_fixture("example-04.txt"), max_bytes_per_symbol=400)
        missing = merge_split_parts(parts[:-1])
        assert any("分割数" in issue.message for issue in missing.issues)

        duplicated = merge_split_parts([parts[0], parts[0], *parts[1:-1]])
        assert any("重複" in issue.message for issue in duplicated.issues)

    def test_omitting_trailing_empty_fields_saves_space(self) -> None:
        notebook = notebook_of("example-04.txt")
        normal = byte_length(serialize(notebook))
        compact = byte_length(serialize(notebook, omit_trailing_empty_fields=True))
        assert compact < normal
