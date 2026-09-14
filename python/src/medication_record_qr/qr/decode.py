"""QRコードを読み取ってお薬手帳データへ変換する。

QRコードの読み取りには `zxing-cpp <https://pypi.org/project/zxing-cpp/>`_ と
`Pillow <https://pypi.org/project/pillow/>`_ を使用する
(``pip install "medication-record-qr-format[decode]"``)。
"""

from __future__ import annotations

import io
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from ..issues import Issue, QrCodeError
from ..models import MedicationNotebook, RawRecord
from ..parser import ParseResult, parse
from ..spec.records import Direction
from .charset import DEFAULT_ENCODING, decode_text
from .split import merge_split_parts


@dataclass(frozen=True)
class ReadResult(ParseResult):
    """QRコードの読み取り結果。"""

    #: 複数シンボルの結合時に検出した問題
    merge_issues: list[Issue] = field(default_factory=list)


def _require_decoder() -> tuple[Any, Any]:
    try:
        import zxingcpp
        from PIL import Image
    except ImportError as error:  # pragma: no cover - 依存が無い環境向け
        raise QrCodeError(
            "QRコードの読み取りには zxing-cpp と Pillow が必要です。"
            'pip install "medication-record-qr-format[decode]" でインストールしてください。'
        ) from error
    return zxingcpp, Image


def decode_qr_from_image(image: Any, *, encoding: str = DEFAULT_ENCODING, errors: str = "strict") -> str:
    """画像(PIL Image / numpy 配列)からQRコードを読み取り、格納されているテキストを返す。"""
    zxingcpp, _ = _require_decoder()

    try:
        result = zxingcpp.read_barcode(image)
    except Exception as exc:  # pragma: no cover - zxing 側のエラーを包む
        raise QrCodeError(f"QRコードの読み取りに失敗しました: {exc}") from exc

    if result is None:
        raise QrCodeError("画像からQRコードを検出できませんでした。")

    return decode_text(bytes(result.bytes), encoding, errors)


def decode_qr_from_png(png: bytes, *, encoding: str = DEFAULT_ENCODING, errors: str = "strict") -> str:
    """PNG画像(バイト列)からQRコードを読み取り、格納されているテキストを返す。"""
    _, Image = _require_decoder()

    try:
        image = Image.open(io.BytesIO(png)).convert("L")
    except Exception as exc:
        raise QrCodeError(f"画像を読み込めませんでした: {exc}") from exc

    return decode_qr_from_image(image, encoding=encoding, errors=errors)


def read_notebook_from_texts(texts: Sequence[str], **parse_options: Any) -> ReadResult:
    """QRコードから読み取ったテキスト(複数シンボル可)を構造化データへ変換する。

    分割制御レコード(911)がある場合は、データ連番順に結合してから解析する。
    """
    if not texts:
        raise QrCodeError("読み取り対象のテキストが1件もありません。")

    if len(texts) == 1:
        text, merge_issues = texts[0], []
    else:
        merged = merge_split_parts(texts)
        text, merge_issues = merged.text, merged.issues

    result = parse(text, **parse_options)
    return ReadResult(
        ok=result.ok,
        notebook=result.notebook,
        issues=result.issues,
        records=result.records,
        merge_issues=merge_issues,
    )


def read_notebook_from_pngs(
    pngs: Sequence[bytes],
    *,
    encoding: str = DEFAULT_ENCODING,
    **parse_options: Any,
) -> ReadResult:
    """PNG画像(複数可)からお薬手帳データを読み取り、構造化データへ変換する。"""
    return read_notebook_from_texts([decode_qr_from_png(png, encoding=encoding) for png in pngs], **parse_options)


def read_notebook_from_images(
    images: Sequence[Any],
    *,
    encoding: str = DEFAULT_ENCODING,
    **parse_options: Any,
) -> ReadResult:
    """画像(複数可)からお薬手帳データを読み取り、構造化データへ変換する。"""
    return read_notebook_from_texts(
        [decode_qr_from_image(image, encoding=encoding) for image in images], **parse_options
    )


__all__ = [
    "Direction",
    "MedicationNotebook",
    "RawRecord",
    "ReadResult",
    "decode_qr_from_image",
    "decode_qr_from_png",
    "read_notebook_from_images",
    "read_notebook_from_pngs",
    "read_notebook_from_texts",
]
