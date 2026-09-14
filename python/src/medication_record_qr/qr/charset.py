"""QRコードに格納する文字コード(仕様書 3.2.3 ASCIIコード)。"""

from __future__ import annotations

from ..issues import QrCodeError

#: 既定の文字コード。
#:
#: 仕様書は Shift_JIS(JIS X 0201-1976 の8単位符号および JIS X 0208-1983 附属書1)を前提としている。
#: Python の ``shift_jis`` コーデックは波ダッシュや全角チルダの扱いが実装間で揺れるため、
#: 実際の医療システムで使われている Windows-31J (``cp932``) を既定とする。
DEFAULT_ENCODING = "cp932"


def encode_text(text: str, encoding: str = DEFAULT_ENCODING) -> bytes:
    """テキストを指定の文字コードのバイト列へ変換する。"""
    return text.encode(encoding)


def decode_text(
    data: bytes | bytearray | memoryview,
    encoding: str = DEFAULT_ENCODING,
    errors: str = "strict",
) -> str:
    """バイト列を指定の文字コードでテキストへ変換する。

    指定の文字コードとして解釈できない場合は :class:`QrCodeError` を送出する。
    読み取れる範囲だけでも取り出したい場合は ``errors="replace"`` を指定する。
    """
    try:
        return bytes(data).decode(encoding, errors)
    except UnicodeDecodeError as exc:
        raise QrCodeError(
            f"QRコードのデータを {encoding} として解釈できませんでした。文字コードの指定を確認してください: {exc}"
        ) from exc


def byte_length(text: str, encoding: str = DEFAULT_ENCODING) -> int:
    """指定の文字コードでのバイト長を返す。"""
    return len(text.encode(encoding, errors="replace"))


def unencodable_characters(text: str, encoding: str = DEFAULT_ENCODING) -> list[str]:
    """指定の文字コードで表現できない文字を列挙する(外字の検出に使う)。"""
    result: list[str] = []
    for character in text:
        try:
            character.encode(encoding)
        except UnicodeEncodeError:
            if character not in result:
                result.append(character)
    return result
