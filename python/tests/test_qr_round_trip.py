"""テキストデータ -> QRコード -> テキストデータ の往復検証。

実際にQRコードのPNG画像を生成し、それを画像として読み取った結果が
元のテキストと1文字も違わないことを確認する。
"""

from __future__ import annotations

import io

import pytest

from medication_record_qr import (
    Drug,
    MedicationNotebook,
    Rp,
    Usage,
    byte_length,
    decode_qr_from_image,
    decode_qr_from_png,
    encode_text_to_png,
    merge_split_parts,
    parse,
    serialize,
    split_for_qr,
)

from .conftest import ALL_FIXTURES, read_fixture

pytest.importorskip("segno", reason="QRコードの生成には segno が必要です")
pytest.importorskip("zxingcpp", reason="QRコードの読み取りには zxing-cpp が必要です")
pytest.importorskip("PIL", reason="QRコードの読み取りには Pillow が必要です")

import zxingcpp
from PIL import Image


def raw_bytes_of(png: bytes) -> bytes:
    """QRコードのPNG画像から、格納されているバイト列をそのまま取り出す。"""
    result = zxingcpp.read_barcode(Image.open(io.BytesIO(png)).convert("L"))
    assert result is not None, "QRコードを検出できませんでした"
    return bytes(result.bytes)


class TestTextToQrToText:
    @pytest.mark.parametrize("name", ALL_FIXTURES)
    def test_round_trip_matches_the_original_text(self, name: str) -> None:
        text = read_fixture(name)
        assert decode_qr_from_png(encode_text_to_png(text)) == text

    @pytest.mark.parametrize("name", ALL_FIXTURES)
    def test_stored_as_shift_jis_bytes(self, name: str) -> None:
        text = read_fixture(name)
        # 画像から取り出した生のバイト列が、元テキストのShift_JISバイト列と完全に一致する
        assert raw_bytes_of(encode_text_to_png(text)) == text.encode("cp932")

    @pytest.mark.parametrize("level", ["l", "m", "q", "h"])
    def test_every_error_correction_level(self, level: str) -> None:
        text = read_fixture("example-04.txt")
        assert decode_qr_from_png(encode_text_to_png(text, error=level)) == text

    @pytest.mark.parametrize(("scale", "border"), [(2, 0), (4, 4), (10, 8)])
    def test_every_image_size(self, scale: int, border: int) -> None:
        text = read_fixture("example-03.txt")
        assert decode_qr_from_png(encode_text_to_png(text, scale=scale, border=border)) == text

    def test_explicit_symbol_version(self) -> None:
        text = read_fixture("example-01.txt")
        assert decode_qr_from_png(encode_text_to_png(text, symbol_version=20)) == text

    def test_reading_from_a_pil_image(self) -> None:
        text = read_fixture("example-07.txt")
        image = Image.open(io.BytesIO(encode_text_to_png(text))).convert("L")
        assert decode_qr_from_image(image) == text

    def test_characters_that_differ_between_shift_jis_variants(self) -> None:
        # 全角英数 / 全角チルダ / 記号
        text = read_fixture("example-07.txt")
        assert "Ｂ＋" in text
        assert "～" in text
        assert "○" in text

        # 半角カナ / 鉤括弧 / 隅付き括弧
        with_kana = read_fixture("example-02.txt")
        assert "ｺﾘｵﾊﾟﾝｶﾌﾟｾﾙ5mg" in with_kana
        assert "「ﾎｴｲ」" in with_kana
        assert "【１日３～４回 うがい】" in with_kana

        for target in (text, with_kana):
            assert decode_qr_from_png(encode_text_to_png(target)) == target

    def test_text_without_trailing_empty_fields(self) -> None:
        notebook = parse(read_fixture("example-04.txt")).notebook
        compact = serialize(notebook, omit_trailing_empty_fields=True)
        assert decode_qr_from_png(encode_text_to_png(compact)) == compact

    def test_utf8(self) -> None:
        text = read_fixture("example-04.txt")
        png = encode_text_to_png(text, encoding="utf-8")
        assert decode_qr_from_png(png, encoding="utf-8") == text


def build_large_notebook(target_bytes: int) -> MedicationNotebook:
    """指定バイト数に近づくまで薬品を増やしたお薬手帳データを作る。"""
    notebook = parse(read_fixture("example-04.txt")).notebook
    rps = notebook.dispensings[0].doctor_groups[0].rps

    index = 100
    while byte_length(serialize(notebook)) < target_bytes:
        index += 1
        rps.append(
            Rp(
                rp_number=str(index),
                drugs=[
                    Drug(
                        name=f"テスト薬品{index}錠１００ｍｇ「ﾖｼﾀﾞ」",
                        dose="3",
                        unit_name="錠",
                        code_type="2",
                        code="620004992",
                        record_creator="1",
                    )
                ],
                usage=Usage(
                    name="【分３ 毎食後服用】",
                    dispensing_quantity="14",
                    dispensing_unit="日分",
                    dosage_form_code="1",
                    code_type="1",
                    record_creator="1",
                ),
            )
        )
    return notebook


class TestLargeText:
    def test_text_close_to_the_symbol_limit(self) -> None:
        text = serialize(build_large_notebook(1700))
        size = byte_length(text)
        assert 1700 < size <= 1800

        assert decode_qr_from_png(encode_text_to_png(text)) == text

    def test_split_symbols_are_read_and_merged_back(self) -> None:
        text = serialize(build_large_notebook(4000))
        parts = split_for_qr(text, max_bytes_per_symbol=1200, data_id="12345678901234")
        assert len(parts) > 2

        # 各シンボルをQRコードにして読み取る(読み取り順は入れ替える)
        decoded = [decode_qr_from_png(encode_text_to_png(part)) for part in parts]
        assert decoded == parts

        merged = merge_split_parts(list(reversed(decoded)))
        assert merged.issues == []
        assert merged.text == text
