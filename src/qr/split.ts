import { ISSUE_CODE, type Issue } from "../issues.js";
import { RECORD_NO } from "../spec/records.js";
import { FIELD_SEPARATOR, RECORD_SEPARATOR, parseRawRecords } from "../text/records.js";
import { byteLength, DEFAULT_TEXT_ENCODING, type TextEncodingName } from "./charset.js";

/**
 * 1シンボルあたりの既定の最大バイト数。
 *
 * QRコード(型番40・誤り訂正レベルM・8ビットバイトモード)の理論上限は2331バイトだが、
 * 携帯電話等での読み取り性能を考慮して控えめな既定値としている。
 */
export const DEFAULT_MAX_BYTES_PER_SYMBOL = 1800;

export interface SplitOptions {
  readonly maxBytesPerSymbol?: number;
  readonly encoding?: TextEncodingName;
  /** 分割制御レコード(911)のデータ固有ID(数値14桁)。未指定時は自動採番。 */
  readonly dataId?: string;
  readonly newline?: string;
}

/** データ固有ID(数値14桁)を採番する。 */
const generateDataId = (): string => {
  const now = new Date();
  const pad = (value: number, size = 2): string => String(value).padStart(size, "0");
  return (
    `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}` +
    `${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`
  );
};

/**
 * お薬手帳データのテキストを、1つのQRコードに収まる大きさへ分割する(仕様書 3.2.9(3))。
 *
 * - 分割はレコード単位で行う
 * - 分割された全てのデータの先頭にバージョンレコードを出力する
 * - 分割された全てのデータの末尾に分割制御レコード(911)を出力する
 *
 * 分割が不要な場合は、分割制御レコードを付けずに元のテキストをそのまま1件返す。
 */
export const splitForQr = (text: string, options: SplitOptions = {}): string[] => {
  const encoding = options.encoding ?? DEFAULT_TEXT_ENCODING;
  const newline = options.newline ?? RECORD_SEPARATOR;
  const maxBytes = options.maxBytesPerSymbol ?? DEFAULT_MAX_BYTES_PER_SYMBOL;

  const records = parseRawRecords(text);
  if (records.length === 0) return [];
  if (byteLength(text, encoding) <= maxBytes) return [text];

  const versionLine = records[0]!.raw;
  const bodyLines = records
    .slice(1)
    .filter((record) => record.recordNo !== RECORD_NO.splitControl)
    .map((record) => record.raw);

  const dataId = options.dataId ?? generateDataId();
  const newlineBytes = byteLength(newline, encoding);
  // 分割制御レコードは `911,<データ固有ID>,<分割数>,<データ連番>`。分割数・連番は最大3桁。
  const splitRecordBytes =
    byteLength([RECORD_NO.splitControl, dataId, "999", "999"].join(FIELD_SEPARATOR), encoding) + newlineBytes;
  const budget = maxBytes - byteLength(versionLine, encoding) - newlineBytes - splitRecordBytes;

  const chunks: string[][] = [];
  let current: string[] = [];
  let currentBytes = 0;

  for (const line of bodyLines) {
    const lineBytes = byteLength(line, encoding) + newlineBytes;
    if (lineBytes > budget) {
      throw new RangeError(
        `1レコードが1シンボルの上限(${maxBytes}バイト)に収まりません。maxBytesPerSymbol を増やしてください: ${line}`,
      );
    }
    if (current.length > 0 && currentBytes + lineBytes > budget) {
      chunks.push(current);
      current = [];
      currentBytes = 0;
    }
    current.push(line);
    currentBytes += lineBytes;
  }
  if (current.length > 0) chunks.push(current);

  return chunks.map((chunk, index) =>
    [
      versionLine,
      ...chunk,
      [RECORD_NO.splitControl, dataId, String(chunks.length), String(index + 1)].join(FIELD_SEPARATOR),
    ].join(newline),
  );
};

export interface MergeResult {
  /** 結合後のテキスト(分割制御レコードは取り除かれる) */
  readonly text: string;
  readonly dataId?: string;
  /** 分割制御レコードが示す分割数 */
  readonly totalCount: number;
  readonly issues: readonly Issue[];
}

interface SplitPart {
  readonly versionLine: string | undefined;
  readonly dataId: string | undefined;
  readonly totalCount: number | undefined;
  readonly sequence: number | undefined;
  readonly bodyLines: string[];
}

const decodePart = (text: string): SplitPart => {
  const records = parseRawRecords(text);
  const splitRecord = records.find((record) => record.recordNo === RECORD_NO.splitControl);
  const toNumber = (value: string | undefined): number | undefined => {
    if (value === undefined || value.trim() === "") return undefined;
    const parsed = Number(value);
    return Number.isNaN(parsed) ? undefined : parsed;
  };

  return {
    versionLine: records[0]?.raw,
    dataId: splitRecord?.fields[1],
    totalCount: toNumber(splitRecord?.fields[2]),
    sequence: toNumber(splitRecord?.fields[3]),
    bodyLines: records
      .filter((record, index) => index !== 0 && record.recordNo !== RECORD_NO.splitControl)
      .map((record) => record.raw),
  };
};

/**
 * 分割された複数シンボル分のテキストを1つのテキストへ復元する。
 * 分割制御レコード(911)のデータ連番順に並べ替えるため、読み取り順は問わない。
 */
export const mergeSplitParts = (parts: readonly string[], newline: string = RECORD_SEPARATOR): MergeResult => {
  const issues: Issue[] = [];
  const error = (message: string): void => {
    issues.push({ level: "error", code: ISSUE_CODE.splitMismatch, message });
  };

  const decoded = parts.map(decodePart);

  const dataIds = new Set(decoded.map((part) => part.dataId).filter((id): id is string => id !== undefined));
  if (dataIds.size > 1) {
    error(`異なるデータ固有IDのシンボルが混在しています: ${[...dataIds].join(", ")}`);
  }

  const totalCounts = new Set(
    decoded.map((part) => part.totalCount).filter((count): count is number => count !== undefined),
  );
  if (totalCounts.size > 1) {
    error(`分割数が一致していません: ${[...totalCounts].join(", ")}`);
  }

  const expectedTotal = [...totalCounts][0];
  if (expectedTotal !== undefined && expectedTotal !== parts.length) {
    error(`分割数 ${expectedTotal} に対して ${parts.length} 件のシンボルしかありません。`);
  }

  const ordered = [...decoded].sort((a, b) => (a.sequence ?? 1) - (b.sequence ?? 1));
  const seen = new Set<number>();
  for (const part of ordered) {
    if (part.sequence === undefined) continue;
    if (seen.has(part.sequence)) error(`データ連番 ${part.sequence} のシンボルが重複しています。`);
    seen.add(part.sequence);
  }

  const versionLine = ordered[0]?.versionLine;
  const lines = versionLine === undefined ? [] : [versionLine, ...ordered.flatMap((part) => part.bodyLines)];

  const result: MergeResult = {
    text: lines.join(newline),
    totalCount: expectedTotal ?? parts.length,
    issues,
  };
  const dataId = [...dataIds][0];
  return dataId === undefined ? result : { ...result, dataId };
};
