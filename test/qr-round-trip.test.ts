/**
 * テキストデータ -> QRコード -> テキストデータ の往復検証。
 *
 * 実際にQRコードのPNG画像を生成し、それを画像として読み取った結果が
 * 元のテキストと1文字も違わないことを確認する。
 */
import jsQR from "jsqr";
import { PNG } from "pngjs";
import { describe, expect, it } from "vitest";
import {
  byteLength,
  decodeQrFromImageData,
  decodeQrFromPng,
  encodeText,
  encodeTextToPng,
  mergeSplitParts,
  parse,
  serialize,
  splitForQr,
  type MedicationNotebook,
} from "../src/index.js";
import { ALL_FIXTURES, readFixture } from "./helpers.js";

/** QRコードのPNG画像から、格納されているバイト列をそのまま取り出す。 */
const rawBytesOf = (png: Buffer): Uint8Array => {
  const image = PNG.sync.read(png);
  const result = jsQR(new Uint8ClampedArray(image.data), image.width, image.height);
  if (result === null) throw new Error("QRコードを検出できませんでした");
  return Uint8Array.from(result.binaryData);
};

describe("テキスト -> QRコード -> テキスト", () => {
  it.each(ALL_FIXTURES)("%s をQRコードにして読み取ると元のテキストと一致する", async (name) => {
    const text = readFixture(name);
    const png = await encodeTextToPng(text);

    expect(decodeQrFromPng(png)).toBe(text);
  });

  it.each(ALL_FIXTURES)("%s はQRコードにShift_JISのバイト列として格納される", async (name) => {
    const text = readFixture(name);
    const png = await encodeTextToPng(text);

    // 画像から取り出した生のバイト列が、元テキストのShift_JISバイト列と完全に一致する
    expect(Buffer.from(rawBytesOf(png))).toEqual(Buffer.from(encodeText(text, "Shift_JIS")));
  });

  it.each(["L", "M", "Q", "H"] as const)("誤り訂正レベル %s でも往復で一致する", async (level) => {
    const text = readFixture("example-04.txt");
    const png = await encodeTextToPng(text, { errorCorrectionLevel: level });

    expect(decodeQrFromPng(png)).toBe(text);
  });

  it.each([
    { scale: 2, margin: 0 },
    { scale: 4, margin: 4 },
    { scale: 10, margin: 8 },
  ])("画像サイズ・余白を変えても往復で一致する (%o)", async (options) => {
    const text = readFixture("example-03.txt");
    const png = await encodeTextToPng(text, options);

    expect(decodeQrFromPng(png)).toBe(text);
  });

  it("型番を明示しても往復で一致する", async () => {
    const text = readFixture("example-01.txt");
    const png = await encodeTextToPng(text, { symbolVersion: 20 });

    expect(decodeQrFromPng(png)).toBe(text);
  });

  it("RGBA画素データから読み取っても一致する", async () => {
    const text = readFixture("example-07.txt");
    const image = PNG.sync.read(await encodeTextToPng(text));

    expect(decodeQrFromImageData({ data: image.data, width: image.width, height: image.height })).toBe(text);
  });

  it("Shift_JISで扱いが分かれる文字を含むテキストでも一致する", async () => {
    // 半角カナ / 全角英数 / 全角チルダ / 丸括弧・鉤括弧・隅付き括弧
    const text = readFixture("example-07.txt");
    expect(text).toContain("Ｂ＋");
    expect(text).toContain("～");
    expect(text).toContain("○");

    const withKana = readFixture("example-02.txt");
    expect(withKana).toContain("ｺﾘｵﾊﾟﾝｶﾌﾟｾﾙ5mg");
    expect(withKana).toContain("「ﾎｴｲ」");
    expect(withKana).toContain("【１日３～４回 うがい】");

    for (const target of [text, withKana]) {
      expect(decodeQrFromPng(await encodeTextToPng(target))).toBe(target);
    }
  });

  it("末尾の空項目を省略したテキストでも一致する", async () => {
    const notebook = parse(readFixture("example-04.txt")).notebook;
    const compact = serialize(notebook, { omitTrailingEmptyFields: true });

    expect(decodeQrFromPng(await encodeTextToPng(compact))).toBe(compact);
  });

  it("UTF-8で格納した場合も往復で一致する", async () => {
    const text = readFixture("example-04.txt");
    const png = await encodeTextToPng(text, { encoding: "UTF-8" });

    expect(decodeQrFromPng(png, { encoding: "UTF-8" })).toBe(text);
  });
});

describe("1シンボルの容量いっぱいのテキスト -> QRコード -> テキスト", () => {
  /** 指定バイト数に近づくまで薬品を増やしたお薬手帳データを作る。 */
  const buildLargeNotebook = (targetBytes: number): MedicationNotebook => {
    const notebook = parse(readFixture("example-04.txt")).notebook;
    const rps = notebook.dispensings[0]!.doctorGroups[0]!.rps;
    const template = rps[0]!;

    let index = 100;
    while (byteLength(serialize(notebook), "Shift_JIS") < targetBytes) {
      index += 1;
      rps.push({
        ...template,
        rpNumber: String(index),
        drugs: [
          {
            name: `テスト薬品${index}錠１００ｍｇ「ﾖｼﾀﾞ」`,
            dose: "3",
            unitName: "錠",
            codeType: "2",
            code: "620004992",
            recordCreator: "1",
            supplements: [],
            cautions: [],
          },
        ],
        usage: {
          name: "【分３ 毎食後服用】",
          dispensingQuantity: "14",
          dispensingUnit: "日分",
          dosageFormCode: "1",
          codeType: "1",
          recordCreator: "1",
        },
        usageSupplements: [],
        prescriptionCautions: [],
        orphanDrugNotes: [],
      });
    }
    return notebook;
  };

  it("既定の上限(1800バイト)に近いテキストでも往復で一致する", async () => {
    const text = serialize(buildLargeNotebook(1700));
    const bytes = byteLength(text, "Shift_JIS");
    expect(bytes).toBeGreaterThan(1700);
    expect(bytes).toBeLessThanOrEqual(1800);

    expect(decodeQrFromPng(await encodeTextToPng(text))).toBe(text);
  });

  it("分割した各シンボルを読み取って結合すると元のテキストに戻る", async () => {
    const text = serialize(buildLargeNotebook(4000));
    const parts = splitForQr(text, { maxBytesPerSymbol: 1200, dataId: "12345678901234" });
    expect(parts.length).toBeGreaterThan(2);

    // 各シンボルをQRコードにして読み取る(読み取り順は入れ替える)
    const decoded = await Promise.all(parts.map(async (part) => decodeQrFromPng(await encodeTextToPng(part))));
    expect(decoded).toEqual(parts);

    const merged = mergeSplitParts([...decoded].reverse());
    expect(merged.issues).toEqual([]);
    expect(merged.text).toBe(text);
  });
});
