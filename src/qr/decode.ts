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
}

export const readNotebookFromTexts = (texts: readonly string[], options: ParseOptions = {}): ReadResult => {
  if (texts.length === 0) throw new QrCodeError("読み取り対象のテキストが1件もありません。");
  const merged = texts.length === 1 ? { text: texts[0]!, issues: [] } : mergeSplitParts(texts);
  return { ...parse(merged.text, options), mergeIssues: merged.issues };
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
