import { CODE_TABLES, isValidCode } from "./spec/codes.js";
import {
  RECORD_NO,
  isRequiredFor,
  type Direction,
  type FieldSpec,
  type RecordSpec,
} from "./spec/records.js";
import { ISSUE_CODE, IssueCollector } from "./issues.js";
import { fieldAt } from "./text/records.js";
import { sjisByteLength } from "./text/length.js";
import type { RawRecord } from "./types.js";

export interface ValidationOptions {
  /** コード表による区分値の検証を行う(既定: true) */
  readonly checkCodeTables?: boolean;
  /** バイト数・データ型の検証を行う(既定: true) */
  readonly checkFieldFormat?: boolean;
}

const WESTERN_DATE = /^(\d{4})(\d{2})(\d{2})$/;
const JAPANESE_DATE = /^([MTSHR])(\d{2})(\d{2})(\d{2})$/;
const NUMERIC = /^\d*$/;
/** 型X: 英数字、ピリオド、ハイフン */
const ALPHANUMERIC = /^[0-9A-Za-z.-]*$/;

const isValidMonthDay = (month: number, day: number): boolean => month >= 1 && month <= 12 && day >= 1 && day <= 31;

/** 西暦8桁 YYYYMMDD または和暦7桁 GYYMMDD の年月日かどうかを判定する。 */
export const isValidDate = (value: string): boolean => {
  const western = WESTERN_DATE.exec(value);
  if (western !== null) {
    const [year, month, day] = [Number(western[1]), Number(western[2]), Number(western[3])];
    if (!isValidMonthDay(month, day)) return false;
    const date = new Date(Date.UTC(year, month - 1, day));
    return date.getUTCFullYear() === year && date.getUTCMonth() === month - 1 && date.getUTCDate() === day;
  }

  const japanese = JAPANESE_DATE.exec(value);
  if (japanese !== null) return isValidMonthDay(Number(japanese[3]), Number(japanese[4]));

  return false;
};

const validateField = (
  record: RawRecord,
  spec: RecordSpec,
  field: FieldSpec,
  issues: IssueCollector,
  direction: Direction | undefined,
  options: ValidationOptions,
): void => {
  const context = { line: record.line, recordNo: spec.recordNo, fieldIndex: field.index, fieldKey: field.key };
  const value = fieldAt(record, field.index);

  if (value === undefined) {
    if (isRequiredFor(field, direction)) {
      issues.error(
        ISSUE_CODE.missingRequiredField,
        `${spec.label}(${spec.recordNo}) の必須項目「${field.label}」が未設定です。`,
        context,
      );
    }
    return;
  }

  if (options.checkFieldFormat !== false) {
    const bytes = sjisByteLength(value);
    if (bytes > field.bytes) {
      issues.warn(
        ISSUE_CODE.fieldTooLong,
        `${spec.label}(${spec.recordNo}) の「${field.label}」が仕様のバイト数 ${field.bytes} を超えています(${bytes}バイト)。`,
        context,
      );
    }

    if (field.isDate) {
      if (!isValidDate(value)) {
        issues.warn(
          ISSUE_CODE.invalidDate,
          `${spec.label}(${spec.recordNo}) の「${field.label}」は西暦8桁(YYYYMMDD)または和暦7桁(GYYMMDD)である必要があります: ${value}`,
          context,
        );
      }
    } else if (field.type === "9" && !NUMERIC.test(value)) {
      issues.warn(
        ISSUE_CODE.invalidType,
        `${spec.label}(${spec.recordNo}) の「${field.label}」は数値(型9)である必要があります: ${value}`,
        context,
      );
    } else if (field.type === "X" && !ALPHANUMERIC.test(value)) {
      issues.warn(
        ISSUE_CODE.invalidType,
        `${spec.label}(${spec.recordNo}) の「${field.label}」は英数字・ピリオド・ハイフン(型X)である必要があります: ${value}`,
        context,
      );
    }
  }

  if (options.checkCodeTables !== false && field.codeTable !== undefined) {
    const table = CODE_TABLES[field.codeTable];
    if (!isValidCode(table, value)) {
      issues.warn(
        ISSUE_CODE.invalidCode,
        `${spec.label}(${spec.recordNo}) の「${field.label}」に${table.label}として未定義のコード値が指定されています: ${value}`,
        context,
      );
    }
  }
};

/** コード種別が「1:コードなし」以外のときに、対応するコード項目が必須であることを検証する。 */
const validateCodePair = (
  record: RawRecord,
  spec: RecordSpec,
  issues: IssueCollector,
  codeTypeIndex: number,
  codeIndex: number,
): void => {
  const codeType = fieldAt(record, codeTypeIndex);
  const code = fieldAt(record, codeIndex);
  if (codeType === undefined || codeType === "1" || code !== undefined) return;

  const codeTypeField = spec.fields[codeTypeIndex - 1]!;
  const codeField = spec.fields[codeIndex - 1]!;
  issues.error(
    ISSUE_CODE.missingRequiredField,
    `${spec.label}(${spec.recordNo}) の「${codeTypeField.label}」が ${codeType} のため「${codeField.label}」は必須です。`,
    { line: record.line, recordNo: spec.recordNo, fieldIndex: codeIndex, fieldKey: codeField.key },
  );
};

/** 1レコードを仕様のレコードレイアウトに照らして検証する。 */
export const validateRecord = (
  record: RawRecord,
  spec: RecordSpec,
  issues: IssueCollector,
  direction: Direction | undefined,
  options: ValidationOptions = {},
): void => {
  const fieldCount = record.fields.length - 1;
  if (fieldCount > spec.fields.length) {
    issues.warn(
      ISSUE_CODE.tooManyFields,
      `${spec.label}(${spec.recordNo}) の項目数が仕様(${spec.fields.length})より多くなっています(${fieldCount})。`,
      { line: record.line, recordNo: spec.recordNo },
    );
  }

  for (const field of spec.fields) validateField(record, spec, field, issues, direction, options);

  switch (spec.recordNo) {
    case RECORD_NO.drug:
      validateCodePair(record, spec, issues, 5, 6);
      validateCodePair(record, spec, issues, 9, 10);
      break;
    case RECORD_NO.otcDrugIngredient:
      validateCodePair(record, spec, issues, 3, 4);
      break;
    case RECORD_NO.usage:
      validateCodePair(record, spec, issues, 6, 7);
      break;
    default:
      break;
  }
};

/**
 * 用法名称の条件付き必須を検証する。
 *
 * 仕様書 表3-23 の注記により、薬局が出力する場合(処方－医療機関レコードが出力されている場合)は
 * 剤形コードが「9:材料」「10:その他」以外であれば用法名称が必須となる。
 */
export const validateUsageName = (
  issues: IssueCollector,
  options: {
    readonly line?: number;
    readonly direction: Direction | undefined;
    readonly dispensedByPharmacy: boolean;
    readonly dosageFormCode: string | undefined;
    readonly name: string | undefined;
  },
): void => {
  if (options.name !== undefined) return;
  const exemptDosageForm = options.dosageFormCode === "9" || options.dosageFormCode === "10";
  const required = options.direction === "toProvider" || (options.dispensedByPharmacy && !exemptDosageForm);
  if (!required) return;

  issues.error(
    ISSUE_CODE.missingRequiredField,
    "用法レコード(301) の必須項目「用法名称」が未設定です。",
    { line: options.line, recordNo: RECORD_NO.usage, fieldIndex: 2, fieldKey: "name" },
  );
};
