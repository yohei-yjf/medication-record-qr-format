import { describe, expect, it } from "vitest";
import {
  QrCodeError,
  byteLength,
  decodeQrFromPng,
  encodeNotebookToDataUrls,
  encodeNotebookToPngs,
  encodeNotebookToSvgs,
  encodeTextToPng,
  mergeSplitParts,
  parse,
  readNotebookFromPngs,
  serialize,
  splitForQr,
  toQrTexts,
  type MedicationNotebook,
} from "../src/index.js";
import { EXAMPLE_FIXTURES, readFixture } from "./helpers.js";

const notebookOf = (name: string): MedicationNotebook => parse(readFixture(name)).notebook;

describe("QRコードの生成と読み取り", () => {
  it.each(EXAMPLE_FIXTURES)("%s はQRコードにして読み戻しても一致する", async (name) => {
    const text = readFixture(name);
    const png = await encodeTextToPng(text);
    expect(decodeQrFromPng(png)).toBe(text);
  });

  it("構造化データ -> QRコード -> 構造化データ で内容が保たれる", async () => {
    const notebook = notebookOf("example-11.txt");
    const pngs = await encodeNotebookToPngs(notebook);
    expect(pngs).toHaveLength(1);

    const result = readNotebookFromPngs(pngs);
    expect(result.mergeIssues).toEqual([]);
    expect(result.notebook).toEqual(notebook);
  });

  it("既定では Shift_JIS で符号化する", async () => {
    const text = readFixture("example-01.txt");
    expect(byteLength("あ", "Shift_JIS")).toBe(2);
    expect(byteLength("あ", "UTF-8")).toBe(3);

    const png = await encodeTextToPng(text);
    expect(decodeQrFromPng(png, { encoding: "Shift_JIS" })).toBe(text);
    // 文字コードを取り違えると内容が壊れる
    expect(decodeQrFromPng(png, { encoding: "UTF-8" })).not.toBe(text);
  });

  it("UTF-8 を指定した場合も往復できる", async () => {
    const text = readFixture("example-01.txt");
    const png = await encodeTextToPng(text, { encoding: "UTF-8" });
    expect(decodeQrFromPng(png, { encoding: "UTF-8" })).toBe(text);
  });

  it("半角カナを含むデータもShift_JISで往復できる", async () => {
    const text = readFixture("example-02.txt");
    expect(text).toContain("ｺﾘｵﾊﾟﾝｶﾌﾟｾﾙ5mg");
    const png = await encodeTextToPng(text);
    expect(decodeQrFromPng(png)).toBe(text);
  });

  it("SVG と data URL を生成できる", async () => {
    const notebook = notebookOf("example-01.txt");
    const [svg] = await encodeNotebookToSvgs(notebook);
    expect(svg).toMatch(/^<svg/);

    const [dataUrl] = await encodeNotebookToDataUrls(notebook);
    expect(dataUrl).toMatch(/^data:image\/png;base64,/);
  });

  it("誤り訂正レベル・型番を指定できる", async () => {
    const text = readFixture("example-01.txt");
    const low = await encodeTextToPng(text, { errorCorrectionLevel: "L" });
    const high = await encodeTextToPng(text, { errorCorrectionLevel: "H" });
    expect(decodeQrFromPng(low)).toBe(text);
    expect(decodeQrFromPng(high)).toBe(text);
    expect(high.length).toBeGreaterThan(low.length);

    const fixed = await encodeTextToPng(text, { symbolVersion: 20 });
    expect(decodeQrFromPng(fixed)).toBe(text);
  });

  it("QRコードを検出できない画像はエラーになる", () => {
    expect(() => readNotebookFromPngs([Buffer.from("not a png")])).toThrow(QrCodeError);
  });
});

describe("複数シンボルへの分割(仕様書 3.2.9(3))", () => {
  it("上限に収まるデータは分割しない", () => {
    const text = readFixture("example-01.txt");
    expect(splitForQr(text)).toEqual([text]);
  });

  it("上限を超えるデータは分割制御レコード(911)付きで分割する", () => {
    const text = readFixture("example-04.txt");
    const parts = splitForQr(text, { maxBytesPerSymbol: 400, dataId: "12345678901234" });

    expect(parts.length).toBeGreaterThan(1);
    for (const [index, part] of parts.entries()) {
      expect(byteLength(part, "Shift_JIS")).toBeLessThanOrEqual(400);
      const lines = part.split("\r\n");
      // 先頭はバージョンレコード、末尾は分割制御レコード
      expect(lines[0]).toBe("JAHISTC08,1");
      expect(lines[lines.length - 1]).toBe(`911,12345678901234,${parts.length},${index + 1}`);
    }
  });

  it("分割したシンボルを結合すると元のテキストに戻る", () => {
    const text = readFixture("example-04.txt");
    const parts = splitForQr(text, { maxBytesPerSymbol: 400 });
    const merged = mergeSplitParts(parts);

    expect(merged.issues).toEqual([]);
    expect(merged.totalCount).toBe(parts.length);
    expect(merged.text).toBe(text);
  });

  it("読み取り順が入れ替わってもデータ連番順に結合する", () => {
    const text = readFixture("example-04.txt");
    const parts = splitForQr(text, { maxBytesPerSymbol: 400 });
    expect(mergeSplitParts([...parts].reverse()).text).toBe(text);
  });

  it("仕様書の分割出力例(2分割)を結合して解析できる", () => {
    const merged = mergeSplitParts([readFixture("split-part-2.txt"), readFixture("split-part-1.txt")]);
    expect(merged.issues).toEqual([]);
    expect(merged.dataId).toBe("12345678901234");
    expect(merged.totalCount).toBe(2);

    const result = parse(merged.text);
    expect(result.issues).toEqual([]);
    expect(result.notebook.dispensings[0]!.doctorGroups.map((group) => group.doctor?.name)).toEqual([
      "工業会 次郎",
      "佐藤 三郎",
    ]);
    expect(result.notebook.dispensings[0]!.doctorGroups.flatMap((group) => group.rps)).toHaveLength(7);
  });

  it("分割されたQRコードを読み取って構造化データへ戻せる", async () => {
    const notebook = notebookOf("example-11.txt");
    const pngs = await encodeNotebookToPngs(notebook, { maxBytesPerSymbol: 700 });
    expect(pngs.length).toBeGreaterThan(1);

    const result = readNotebookFromPngs(pngs);
    expect(result.mergeIssues).toEqual([]);
    expect(result.notebook).toEqual(notebook);
  });

  it("split: false を指定すると分割しない", () => {
    expect(toQrTexts(notebookOf("example-04.txt"), { split: false, maxBytesPerSymbol: 400 })).toHaveLength(1);
  });

  it("1レコードが上限を超える場合はエラーになる", () => {
    expect(() => splitForQr(readFixture("example-04.txt"), { maxBytesPerSymbol: 80 })).toThrow(RangeError);
  });

  it("データ固有IDが異なるシンボルが混在する場合はエラーを報告する", () => {
    const text = readFixture("example-04.txt");
    const first = splitForQr(text, { maxBytesPerSymbol: 400, dataId: "11111111111111" });
    const second = splitForQr(text, { maxBytesPerSymbol: 400, dataId: "22222222222222" });
    const merged = mergeSplitParts([first[0]!, second[1]!]);

    expect(merged.issues.some((issue) => issue.message.includes("データ固有ID"))).toBe(true);
  });

  it("シンボルが不足している場合・重複している場合はエラーを報告する", () => {
    const parts = splitForQr(readFixture("example-04.txt"), { maxBytesPerSymbol: 400 });
    expect(mergeSplitParts(parts.slice(0, -1)).issues.some((issue) => issue.message.includes("分割数"))).toBe(true);
    expect(
      mergeSplitParts([parts[0]!, parts[0]!, ...parts.slice(1, -1)]).issues.some((issue) =>
        issue.message.includes("重複"),
      ),
    ).toBe(true);
  });

  it("末尾の空項目を省略するとQRコードの容量を節約できる", () => {
    const notebook = notebookOf("example-04.txt");
    const normal = byteLength(serialize(notebook), "Shift_JIS");
    const compact = byteLength(serialize(notebook, { omitTrailingEmptyFields: true }), "Shift_JIS");
    expect(compact).toBeLessThan(normal);
  });
});
