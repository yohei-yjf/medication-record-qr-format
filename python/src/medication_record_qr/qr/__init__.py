"""QRコードの生成と読み取り。"""

from .charset import DEFAULT_ENCODING, byte_length, decode_text, encode_text, unencodable_characters
from .decode import (
    ReadResult,
    decode_qr_from_image,
    decode_qr_from_png,
    read_notebook_from_images,
    read_notebook_from_pngs,
    read_notebook_from_texts,
)
from .encode import (
    encode_notebook_to_data_uris,
    encode_notebook_to_pngs,
    encode_notebook_to_svgs,
    encode_text_to_data_uri,
    encode_text_to_png,
    encode_text_to_svg,
    make_qr,
    to_qr_text,
    to_qr_texts,
)
from .split import DEFAULT_MAX_BYTES_PER_SYMBOL, MergeResult, merge_split_parts, split_for_qr

__all__ = [
    "DEFAULT_ENCODING",
    "DEFAULT_MAX_BYTES_PER_SYMBOL",
    "MergeResult",
    "ReadResult",
    "byte_length",
    "decode_qr_from_image",
    "decode_qr_from_png",
    "decode_text",
    "encode_notebook_to_data_uris",
    "encode_notebook_to_pngs",
    "encode_notebook_to_svgs",
    "encode_text",
    "encode_text_to_data_uri",
    "encode_text_to_png",
    "encode_text_to_svg",
    "make_qr",
    "merge_split_parts",
    "read_notebook_from_images",
    "read_notebook_from_pngs",
    "read_notebook_from_texts",
    "split_for_qr",
    "to_qr_text",
    "to_qr_texts",
    "unencodable_characters",
]
