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
    #: 分割制御レコード(911)が示す分割数。分割されていなければ 1
    total_count: int = 1
    #: まだ読み取れていないデータ連番。空なら揃っている
    missing_sequences: tuple[int, ...] = ()

    @property
    def complete(self) -> bool:
        """分割されたシンボルが揃っているか。

        シンボルが足りなければ ``ok`` も False になるが、``ok`` は解析エラーでも
        False になる。「あと1枚読み取ってください」と「このデータは読めません」
        を区別したい利用側のために、揃っているかどうかだけを見る。
        """
        return not self.missing_sequences


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


def decode_all_qr_from_image(image: Any, *, encoding: str = DEFAULT_ENCODING, errors: str = "strict") -> list[str]:
    """画像からQRコードを**すべて**読み取り、格納されているテキストを順に返す。

    分割されたデータは薬剤情報提供書の1枚に並べて印刷されることが多く、その
    ときは写真1枚に複数のシンボルが写る。1つだけ読んで返すと、利用者には
    「撮ったのに半分しか入らない」としか見えない。
    """
    zxingcpp, _ = _require_decoder()

    try:
        results = zxingcpp.read_barcodes(image)
    except Exception as exc:  # pragma: no cover - zxing 側のエラーを包む
        raise QrCodeError(f"QRコードの読み取りに失敗しました: {exc}") from exc

    if not results:
        raise QrCodeError("画像からQRコードを検出できませんでした。")

    return [decode_text(bytes(result.bytes), encoding, errors) for result in results]


def decode_qr_from_image(image: Any, *, encoding: str = DEFAULT_ENCODING, errors: str = "strict") -> str:
    """画像(PIL Image / numpy 配列)からQRコードを読み取り、格納されているテキストを返す。

    複数写っている場合は最初の1つを返す。すべて必要なら
    :func:`decode_all_qr_from_image` を使う。
    """
    return decode_all_qr_from_image(image, encoding=encoding, errors=errors)[0]


def _open_png(png: bytes) -> Any:
    _, Image = _require_decoder()
    try:
        return Image.open(io.BytesIO(png)).convert("L")
    except Exception as exc:
        raise QrCodeError(f"画像を読み込めませんでした: {exc}") from exc


def decode_all_qr_from_png(png: bytes, *, encoding: str = DEFAULT_ENCODING, errors: str = "strict") -> list[str]:
    """PNG画像(バイト列)からQRコードをすべて読み取る。"""
    return decode_all_qr_from_image(_open_png(png), encoding=encoding, errors=errors)


def decode_qr_from_png(png: bytes, *, encoding: str = DEFAULT_ENCODING, errors: str = "strict") -> str:
    """PNG画像(バイト列)からQRコードを読み取り、格納されているテキストを返す。"""
    return decode_all_qr_from_png(png, encoding=encoding, errors=errors)[0]


def read_notebook_from_texts(texts: Sequence[str], **parse_options: Any) -> ReadResult:
    """QRコードから読み取ったテキスト(複数シンボル可)を構造化データへ変換する。

    分割制御レコード(911)がある場合は、データ連番順に結合してから解析する。
    """
    if not texts:
        raise QrCodeError("読み取り対象のテキストが1件もありません。")

    # 1件でも結合を通す。分割された2枚のうち1枚だけを読んだ場合、そのテキスト
    # 単体は仕様どおりに解析できてしまうので、素通しすると「半分の薬しか無い
    # お薬手帳」が何の警告も無く返る。分割制御レコードは1枚目にも入っている
    # のだから、足りないことは1枚でも分かる。
    merged = merge_split_parts(texts)

    result = parse(merged.text, **parse_options)
    # 結合時の問題も error として上げている以上、`ok` に効かないのはおかしい。
    # シンボルが足りない結果を `ok` のまま返すと、`ok` だけを見る利用側が
    # 欠けたデータをそのまま取り込んでしまう。
    merge_failed = any(issue.level == "error" for issue in merged.issues)
    return ReadResult(
        ok=result.ok and not merge_failed,
        notebook=result.notebook,
        issues=result.issues,
        records=result.records,
        merge_issues=merged.issues,
        total_count=merged.total_count,
        missing_sequences=merged.missing_sequences,
    )


def read_notebook_from_pngs(
    pngs: Sequence[bytes],
    *,
    encoding: str = DEFAULT_ENCODING,
    **parse_options: Any,
) -> ReadResult:
    """PNG画像(複数可)からお薬手帳データを読み取り、構造化データへ変換する。

    1枚の画像に複数のシンボルが写っていればすべて読み取る。
    """
    texts = [text for png in pngs for text in decode_all_qr_from_png(png, encoding=encoding)]
    return read_notebook_from_texts(texts, **parse_options)


def read_notebook_from_images(
    images: Sequence[Any],
    *,
    encoding: str = DEFAULT_ENCODING,
    **parse_options: Any,
) -> ReadResult:
    """画像(複数可)からお薬手帳データを読み取り、構造化データへ変換する。

    1枚の画像に複数のシンボルが写っていればすべて読み取る。
    """
    texts = [text for image in images for text in decode_all_qr_from_image(image, encoding=encoding)]
    return read_notebook_from_texts(texts, **parse_options)


__all__ = [
    "Direction",
    "MedicationNotebook",
    "RawRecord",
    "ReadResult",
    "decode_all_qr_from_image",
    "decode_all_qr_from_png",
    "decode_qr_from_image",
    "decode_qr_from_png",
    "read_notebook_from_images",
    "read_notebook_from_pngs",
    "read_notebook_from_texts",
]
