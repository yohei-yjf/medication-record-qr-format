import { SerializeError } from "../issues.js";
import type { RawRecord } from "../types.js";

/** レコード終端(CR+LF) */
export const RECORD_SEPARATOR = "\r\n";
/** 項目区切り文字 */
export const FIELD_SEPARATOR = ",";
/** ファイル終端(EOF, 0x1A) */
export const EOF_CHARACTER = "\x1a";

/**
 * お薬手帳データのテキストを1行=1レコードに分解する。
 *
 * - 改行は CR+LF / LF / CR のいずれも受け付ける。
 * - 先頭のBOMおよび末尾のファイル終端(EOF, 0x1A)は取り除く。
 * - 空行は読み飛ばす(行番号は元のテキストに対する1始まりの値を保持する)。
 * - 仕様上、項目値に半角カンマ・改行は含められないため引用符処理は行わない。
 */
export const parseRawRecords = (text: string): RawRecord[] => {
  const normalized = text.replace(/^﻿/, "").replace(/\x1a+$/, "");
  const records: RawRecord[] = [];

  normalized.split(/\r\n|\n|\r/).forEach((line, index) => {
    if (line.trim() === "") return;
    const fields = line.split(FIELD_SEPARATOR);
    records.push({ line: index + 1, recordNo: (fields[0] ?? "").trim(), fields, raw: line });
  });

  return records;
};

export interface FormatRecordOptions {
  /**
   * 末尾の空項目を省略する(既定: false)。
   * 仕様書の出力サンプルは末尾の項目まで区切り文字を出力しているため、既定では省略しない。
   * QRコードの容量を節約したい場合に true を指定する。
   */
  readonly omitTrailingEmptyFields?: boolean;
}

const assertFieldValue = (recordNo: string, value: string): void => {
  if (value.includes(FIELD_SEPARATOR)) {
    throw new SerializeError(
      `項目値に半角カンマを含めることはできません(レコード ${recordNo}): ${JSON.stringify(value)}。` +
        "仕様では、薬品名称等で半角カンマを使用している場合は全角カンマに置き換えることとされています。",
      { recordNo, value },
    );
  }
  if (/[\r\n]/.test(value)) {
    throw new SerializeError(`項目値に改行を含めることはできません(レコード ${recordNo}): ${JSON.stringify(value)}`, {
      recordNo,
      value,
    });
  }
};

/** レコード番号と項目値から1レコード分の行文字列を生成する。 */
export const formatRecord = (
  recordNo: string,
  values: readonly (string | undefined)[],
  options: FormatRecordOptions = {},
): string => {
  const fields = values.map((value) => value ?? "");
  for (const value of fields) assertFieldValue(recordNo, value);

  if (options.omitTrailingEmptyFields === true) {
    while (fields.length > 0 && fields[fields.length - 1] === "") fields.pop();
  }

  return [recordNo, ...fields].join(FIELD_SEPARATOR);
};

/** 項目値を取得する(未指定・空文字は undefined を返す)。 */
export const fieldAt = (record: RawRecord, index: number): string | undefined => {
  const value = record.fields[index];
  if (value === undefined) return undefined;
  const trimmed = value.trim();
  return trimmed === "" ? undefined : trimmed;
};
