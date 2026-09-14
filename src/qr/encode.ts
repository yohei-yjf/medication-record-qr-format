import QRCode from "qrcode";
import { QrCodeError } from "../issues.js";
import { serialize, type SerializeOptions } from "../serialize.js";
import type { MedicationNotebook } from "../types.js";
import { DEFAULT_TEXT_ENCODING, encodeText, type TextEncodingName } from "./charset.js";
import { splitForQr, type SplitOptions } from "./split.js";

export interface QrImageOptions {
  /** 誤り訂正レベル(既定: "M") */
  readonly errorCorrectionLevel?: "L" | "M" | "Q" | "H";
  /** 1モジュールあたりのピクセル数(既定: 4) */
  readonly scale?: number;
  /** クワイエットゾーンのモジュール数(既定: 4) */
  readonly margin?: number;
  /** 出力画像の幅(px)。指定時は scale より優先される。 */
  readonly width?: number;
  readonly color?: { readonly dark?: string; readonly light?: string };
  /** QRコードの型番(1〜40)。未指定時は自動選択。 */
  readonly symbolVersion?: number;
}

export interface EncodeOptions extends QrImageOptions, SerializeOptions, SplitOptions {
  /** QRコードに格納する文字コード(既定: Shift_JIS) */
  readonly encoding?: TextEncodingName;
  /** 上限バイト数を超える場合に複数シンボルへ分割する(既定: true) */
  readonly split?: boolean;
}

const toQrCodeOptions = (options: QrImageOptions): QRCode.QRCodeToDataURLOptions => ({
  errorCorrectionLevel: options.errorCorrectionLevel ?? "M",
  scale: options.scale ?? 4,
  margin: options.margin ?? 4,
  ...(options.width === undefined ? {} : { width: options.width }),
  ...(options.color === undefined ? {} : { color: options.color }),
  ...(options.symbolVersion === undefined ? {} : { version: options.symbolVersion }),
});

const toSegments = (text: string, encoding: TextEncodingName): QRCode.QRCodeSegment[] => [
  { data: encodeText(text, encoding), mode: "byte" },
];

/** 構造化データをお薬手帳データのテキストへ変換する(`serialize` の別名)。 */
export const toQrText = (notebook: MedicationNotebook, options: SerializeOptions = {}): string =>
  serialize(notebook, options);

/**
 * 構造化データを、QRコードへ格納するテキストの配列へ変換する。
 * 1シンボルに収まらない場合は分割レコード(911)付きで複数に分割されます。
 */
export const toQrTexts = (notebook: MedicationNotebook, options: EncodeOptions = {}): string[] => {
  const text = serialize(notebook, options);
  if (options.split === false) return [text];
  return splitForQr(text, options);
};

const wrap = async <T>(action: () => Promise<T>): Promise<T> => {
  try {
    return await action();
  } catch (error) {
    throw new QrCodeError(`QRコードの生成に失敗しました: ${(error as Error).message}`, error);
  }
};

/** テキストをQRコードのPNG画像(Buffer)へ変換する。 */
export const encodeTextToPng = async (text: string, options: EncodeOptions = {}): Promise<Buffer> =>
  wrap(() =>
    QRCode.toBuffer(toSegments(text, options.encoding ?? DEFAULT_TEXT_ENCODING), {
      ...toQrCodeOptions(options),
      type: "png",
    } as QRCode.QRCodeToBufferOptions),
  );

/** テキストをQRコードのSVG文字列へ変換する。 */
export const encodeTextToSvg = async (text: string, options: EncodeOptions = {}): Promise<string> =>
  wrap(() =>
    QRCode.toString(toSegments(text, options.encoding ?? DEFAULT_TEXT_ENCODING), {
      ...toQrCodeOptions(options),
      type: "svg",
    } as QRCode.QRCodeToStringOptions),
  );

/** テキストをQRコードの data URL(PNG)へ変換する。 */
export const encodeTextToDataUrl = async (text: string, options: EncodeOptions = {}): Promise<string> =>
  wrap(() =>
    QRCode.toDataURL(toSegments(text, options.encoding ?? DEFAULT_TEXT_ENCODING), toQrCodeOptions(options)),
  );

/** 構造化データをQRコードのPNG画像へ変換する(分割時は複数枚)。 */
export const encodeNotebookToPngs = async (
  notebook: MedicationNotebook,
  options: EncodeOptions = {},
): Promise<Buffer[]> => Promise.all(toQrTexts(notebook, options).map((text) => encodeTextToPng(text, options)));

/** 構造化データをQRコードのSVGへ変換する(分割時は複数枚)。 */
export const encodeNotebookToSvgs = async (
  notebook: MedicationNotebook,
  options: EncodeOptions = {},
): Promise<string[]> => Promise.all(toQrTexts(notebook, options).map((text) => encodeTextToSvg(text, options)));

/** 構造化データをQRコードの data URL へ変換する(分割時は複数枚)。 */
export const encodeNotebookToDataUrls = async (
  notebook: MedicationNotebook,
  options: EncodeOptions = {},
): Promise<string[]> => Promise.all(toQrTexts(notebook, options).map((text) => encodeTextToDataUrl(text, options)));
