/**
 * JAHIS電子版お薬手帳データフォーマット(JAHIS TC)ライブラリ。
 *
 * - QRコード/テキスト -> 構造化データ: `parse` / `readNotebookFromPngs` / `readNotebookFromImageData`
 * - 構造化データ -> テキスト/QRコード: `serialize` / `encodeNotebookToPngs` / `encodeNotebookToSvgs`
 */
export * from "./types.js";
export * from "./issues.js";
export { parse, parseOrThrow, type ParseOptions, type ParseResult } from "./parse.js";
export { serialize, toRecordLines, type SerializeOptions } from "./serialize.js";
export { isValidDate, validateRecord, type ValidationOptions } from "./validate.js";

export {
  RECORD_KIND,
  RECORD_NO,
  RECORD_SPECS,
  VERSION_RECORD_SPEC,
  directionOf,
  findRecordSpec,
  isRequiredFor,
  recordSpecOf,
  type Direction,
  type FieldSpec,
  type FieldType,
  type RecordKind,
  type RecordNo,
  type RecordSpec,
  type RequiredKind,
} from "./spec/records.js";
export {
  CODE_TABLES,
  describeCode,
  isValidCode,
  type CodeTable,
  type CodeTableName,
} from "./spec/codes.js";
export {
  DEFAULT_VERSION,
  FORMAT_VERSIONS,
  TARGET_SPEC_VERSION,
  findFormatVersion,
  isVersionRecord,
  specVersionsOf,
  versionNumberOf,
  type FormatVersionInfo,
} from "./spec/version.js";

export {
  EOF_CHARACTER,
  FIELD_SEPARATOR,
  RECORD_SEPARATOR,
  formatRecord,
  parseRawRecords,
  type FormatRecordOptions,
} from "./text/records.js";

export {
  DEFAULT_TEXT_ENCODING,
  byteLength,
  decodeText,
  encodeText,
  type TextEncodingName,
} from "./qr/charset.js";
export { collectDrugs, collectRps, type RpContext } from "./types.js";
export {
  DEFAULT_MAX_BYTES_PER_SYMBOL,
  mergeSplitParts,
  splitForQr,
  type MergeResult,
  type SplitOptions,
} from "./qr/split.js";
export {
  encodeNotebookToDataUrls,
  encodeNotebookToPngs,
  encodeNotebookToSvgs,
  encodeTextToDataUrl,
  encodeTextToPng,
  encodeTextToSvg,
  toQrText,
  toQrTexts,
  type EncodeOptions,
  type QrImageOptions,
} from "./qr/encode.js";
export {
  decodeQrFromImageData,
  decodeQrFromPng,
  readNotebookFromImageData,
  readNotebookFromPngs,
  readNotebookFromTexts,
  type DecodeOptions,
  type ImageDataLike,
  type ReadResult,
} from "./qr/decode.js";
