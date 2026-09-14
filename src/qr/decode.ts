import jsQR from "jsqr";
import { PNG } from "pngjs";
import { QrCodeError, type Issue } from "../issues.js";
import { parse, type ParseOptions, type ParseResult } from "../parse.js";
import { decodeText, DEFAULT_TEXT_ENCODING, type TextEncodingName } from "./charset.js";
import { mergeSplitParts } from "./split.js";

export interface ImageDataLike {
  readonly data: Uint8ClampedArray | Uint8Array | readonly number[];
  readonly width: number;
  readonly height: number;
}

export interface DecodeOptions {
  /** QRコードに格納されている文字コード(既定: Shift_JIS) */
  readonly encoding?: TextEncodingName;
}

/**
 * RGBA画素データからQRコードを読み取り、格納されているテキストを返す。
 *
 * ブラウザでは `CanvasRenderingContext2D#getImageData()` の戻り値をそのまま渡せます。
 */
export const decodeQrFromImageData = (image: ImageDataLike, options: DecodeOptions = {}): string => {
  const pixels =
    image.data instanceof Uint8ClampedArray ? image.data : new Uint8ClampedArray(image.data as ArrayLike<number>);

  const expected = image.width * image.height * 4;
  if (pixels.length !== expected) {
    throw new QrCodeError(
      `画素データの長さが width×height×4 と一致しません(期待値 ${expected}、実際 ${pixels.length})。RGBA形式である必要があります。`,
    );
  }

  const result = jsQR(pixels, image.width, image.height);
  if (result === null) throw new QrCodeError("画像からQRコードを検出できませんでした。");

  return decodeText(result.binaryData, options.encoding ?? DEFAULT_TEXT_ENCODING);
};

/** PNG画像(Buffer)からQRコードを読み取り、格納されているテキストを返す。 */
export const decodeQrFromPng = (png: Buffer | Uint8Array, options: DecodeOptions = {}): string => {
  let image: PNG;
  try {
    image = PNG.sync.read(Buffer.from(png));
  } catch (error) {
    throw new QrCodeError(`PNG画像を読み込めませんでした: ${(error as Error).message}`, error);
  }
  return decodeQrFromImageData({ data: image.data, width: image.width, height: image.height }, options);
};

/**
 * QRコードから読み取ったテキスト(複数シンボル可)を構造化データへ変換する。
 * 分割レコード(911)がある場合は連番順に結合してから解析します。
 */
export interface ReadResult extends ParseResult {
  /** 複数シンボルの結合時に検出した問題 */
  readonly mergeIssues: readonly Issue[];
  /** 分割制御レコード(911)が示す分割数。分割されていなければ 1 */
  readonly totalCount: number;
  /** まだ読み取れていないデータ連番。空なら揃っている */
  readonly missingSequences: readonly number[];
  /**
   * 分割されたシンボルが揃っているか。
   *
   * シンボルが足りなければ `ok` も false になりますが、`ok` は解析エラーでも
   * false になります。「あと1枚読み取ってください」と「このデータは読めません」
   * を区別したい場合はこちらを見てください。
   */
  readonly complete: boolean;
}

export const readNotebookFromTexts = (texts: readonly string[], options: ParseOptions = {}): ReadResult => {
  if (texts.length === 0) throw new QrCodeError("読み取り対象のテキストが1件もありません。");
  // 1件でも結合を通します。分割された2枚のうち1枚だけを読んだ場合、そのテキスト
  // 単体は仕様どおりに解析できてしまうため、素通しすると「半分の薬しか無いお薬
  // 手帳」が何の警告も無く返ります。分割制御レコードは1枚目にも入っているので、
  // 足りないことは1枚でも分かります。
  const merged = mergeSplitParts(texts);
  const parsed = parse(merged.text, options);
  // 結合時の問題も error として上げている以上、`ok` に効かないのはおかしい。
  const mergeFailed = merged.issues.some((issue) => issue.level === "error");
  return {
    ...parsed,
    ok: parsed.ok && !mergeFailed,
    mergeIssues: merged.issues,
    totalCount: merged.totalCount,
    missingSequences: merged.missingSequences,
    complete: merged.complete,
  };
};

/** PNG画像(複数可)からお薬手帳データを読み取り、構造化データへ変換する。 */
export const readNotebookFromPngs = (
  pngs: readonly (Buffer | Uint8Array)[],
  options: ParseOptions & DecodeOptions = {},
): ReadResult =>
  readNotebookFromTexts(
    pngs.map((png) => decodeQrFromPng(png, options)),
    options,
  );

/** RGBA画素データ(複数可)からお薬手帳データを読み取り、構造化データへ変換する。 */
export const readNotebookFromImageData = (
  images: readonly ImageDataLike[],
  options: ParseOptions & DecodeOptions = {},
): ReadResult =>
  readNotebookFromTexts(
    images.map((image) => decodeQrFromImageData(image, options)),
    options,
  );
