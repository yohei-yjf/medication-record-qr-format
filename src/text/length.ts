import iconv from "iconv-lite";

/**
 * 仕様書の「桁数」に対応するバイト長(Shift_JIS換算。全角文字は2バイト)を返す。
 * Shift_JIS に変換できない文字を含む場合は、変換後のバイト長がそのまま返る点に注意。
 */
export const sjisByteLength = (value: string): number => iconv.encode(value, "Shift_JIS").length;

/** Shift_JIS で表現できない文字を含むかどうかを判定する。 */
export const hasUnencodableCharacter = (value: string): boolean =>
  iconv.decode(iconv.encode(value, "Shift_JIS"), "Shift_JIS") !== value;
