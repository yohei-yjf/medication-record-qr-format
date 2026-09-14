import iconv from "iconv-lite";

/**
 * QRコードに格納する文字コード。
 * 仕様書は Shift_JIS を前提としているため既定は `"Shift_JIS"` です。
 */
export type TextEncodingName = "Shift_JIS" | "UTF-8";

export const DEFAULT_TEXT_ENCODING: TextEncodingName = "Shift_JIS";

export const encodeText = (text: string, encoding: TextEncodingName = DEFAULT_TEXT_ENCODING): Uint8Array =>
  new Uint8Array(iconv.encode(text, encoding));

export const decodeText = (
  bytes: Uint8Array | readonly number[],
  encoding: TextEncodingName = DEFAULT_TEXT_ENCODING,
): string => iconv.decode(Buffer.from(bytes as Uint8Array), encoding);

/** 指定の文字コードでのバイト長を返す。 */
export const byteLength = (text: string, encoding: TextEncodingName = DEFAULT_TEXT_ENCODING): number =>
  encodeText(text, encoding).length;
