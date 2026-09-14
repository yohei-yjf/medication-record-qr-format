"""構造化データ・テキストからQRコードを生成する。

QRコードの生成には `segno <https://pypi.org/project/segno/>`_ を使用する
(``pip install "medication-record-qr-format[encode]"``)。
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING, Any

from ..issues import QrCodeError
from ..models import MedicationNotebook
from ..serializer import serialize
from ..text import RECORD_SEPARATOR
from .charset import DEFAULT_ENCODING, encode_text
from .split import DEFAULT_MAX_BYTES_PER_SYMBOL, split_for_qr

if TYPE_CHECKING:  # pragma: no cover
    import segno

#: 誤り訂正レベル(L / M / Q / H)
ErrorCorrectionLevel = str


def _require_segno() -> Any:
    try:
        import segno
    except ImportError as error:  # pragma: no cover - 依存が無い環境向け
        raise QrCodeError(
            "QRコードの生成には segno が必要です。"
            'pip install "medication-record-qr-format[encode]" でインストールしてください。'
        ) from error
    return segno


def to_qr_text(
    notebook: MedicationNotebook,
    *,
    version: str | None = None,
    newline: str = RECORD_SEPARATOR,
    omit_trailing_empty_fields: bool = False,
) -> str:
    """構造化データをお薬手帳データのテキストへ変換する(:func:`serialize` の別名)。"""
    return serialize(
        notebook,
        version=version,
        newline=newline,
        omit_trailing_empty_fields=omit_trailing_empty_fields,
    )


def to_qr_texts(
    notebook: MedicationNotebook,
    *,
    split: bool = True,
    max_bytes_per_symbol: int = DEFAULT_MAX_BYTES_PER_SYMBOL,
    encoding: str = DEFAULT_ENCODING,
    data_id: str | None = None,
    newline: str = RECORD_SEPARATOR,
    version: str | None = None,
    omit_trailing_empty_fields: bool = False,
    **_ignored: Any,
) -> list[str]:
    """構造化データを、QRコードへ格納するテキストの配列へ変換する。

    1シンボルに収まらない場合は分割制御レコード(911)付きで複数に分割される。
    画像の生成オプション(``scale`` など)を渡しても無視されるため、
    :func:`encode_notebook_to_pngs` などからそのまま転送できる。
    """
    text = serialize(
        notebook,
        version=version,
        newline=newline,
        omit_trailing_empty_fields=omit_trailing_empty_fields,
    )
    if not split:
        return [text]
    return split_for_qr(
        text,
        max_bytes_per_symbol=max_bytes_per_symbol,
        encoding=encoding,
        data_id=data_id,
        newline=newline,
    )


def make_qr(
    text: str,
    *,
    encoding: str = DEFAULT_ENCODING,
    error: ErrorCorrectionLevel = "m",
    symbol_version: int | None = None,
) -> segno.QRCode:
    """テキストから QRコードオブジェクト(:class:`segno.QRCode`)を生成する。

    仕様書どおり8ビットバイトモードで、指定の文字コードのバイト列をそのまま格納する。
    """
    segno_module = _require_segno()
    try:
        qr: segno.QRCode = segno_module.make_qr(encode_text(text, encoding), error=error, version=symbol_version)
    except Exception as exc:  # pragma: no cover - segno 側のエラーを包む
        raise QrCodeError(f"QRコードの生成に失敗しました: {exc}") from exc
    return qr


def encode_text_to_png(
    text: str,
    *,
    encoding: str = DEFAULT_ENCODING,
    error: ErrorCorrectionLevel = "m",
    symbol_version: int | None = None,
    scale: int = 4,
    border: int = 4,
    dark: str = "#000000",
    light: str | None = "#ffffff",
) -> bytes:
    """テキストをQRコードのPNG画像(バイト列)へ変換する。"""
    qr = make_qr(text, encoding=encoding, error=error, symbol_version=symbol_version)
    buffer = io.BytesIO()
    qr.save(buffer, kind="png", scale=scale, border=border, dark=dark, light=light)
    return buffer.getvalue()


def encode_text_to_svg(
    text: str,
    *,
    encoding: str = DEFAULT_ENCODING,
    error: ErrorCorrectionLevel = "m",
    symbol_version: int | None = None,
    scale: int = 4,
    border: int = 4,
    dark: str = "#000000",
    light: str | None = None,
) -> str:
    """テキストをQRコードのSVG文字列へ変換する。"""
    qr = make_qr(text, encoding=encoding, error=error, symbol_version=symbol_version)
    buffer = io.BytesIO()
    qr.save(buffer, kind="svg", scale=scale, border=border, dark=dark, light=light)
    return buffer.getvalue().decode("utf-8")


def encode_text_to_data_uri(
    text: str,
    *,
    encoding: str = DEFAULT_ENCODING,
    error: ErrorCorrectionLevel = "m",
    symbol_version: int | None = None,
    scale: int = 4,
    border: int = 4,
) -> str:
    """テキストをQRコードの data URI(PNG)へ変換する。"""
    qr = make_qr(text, encoding=encoding, error=error, symbol_version=symbol_version)
    return str(qr.png_data_uri(scale=scale, border=border))


def encode_notebook_to_pngs(notebook: MedicationNotebook, **options: Any) -> list[bytes]:
    """構造化データをQRコードのPNG画像へ変換する(分割時は複数枚)。"""
    return [encode_text_to_png(text, **_image_options(options)) for text in to_qr_texts(notebook, **options)]


def encode_notebook_to_svgs(notebook: MedicationNotebook, **options: Any) -> list[str]:
    """構造化データをQRコードのSVGへ変換する(分割時は複数枚)。"""
    return [encode_text_to_svg(text, **_image_options(options)) for text in to_qr_texts(notebook, **options)]


def encode_notebook_to_data_uris(notebook: MedicationNotebook, **options: Any) -> list[str]:
    """構造化データをQRコードの data URI へ変換する(分割時は複数枚)。"""
    image_options = {key: value for key, value in _image_options(options).items() if key not in {"dark", "light"}}
    return [encode_text_to_data_uri(text, **image_options) for text in to_qr_texts(notebook, **options)]


#: 画像生成に渡すオプション(それ以外はテキスト生成・分割のオプションとして扱う)
_IMAGE_OPTION_KEYS = frozenset({"encoding", "error", "symbol_version", "scale", "border", "dark", "light"})


def _image_options(options: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in options.items() if key in _IMAGE_OPTION_KEYS}
