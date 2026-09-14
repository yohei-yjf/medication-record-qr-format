import { describe, expect, it } from "vitest";
import { SerializeError, parse, serialize, toRecordLines, type MedicationNotebook } from "../src/index.js";
import { EXAMPLE_FIXTURES, readFixture } from "./helpers.js";

/** 例8は出力データ例の項目数がレコードレイアウトと一致しないため、テキスト完全一致の対象から外す */
const ROUND_TRIP_EXAMPLES = EXAMPLE_FIXTURES.filter((name) => name !== "example-08.txt");

describe("構造化データ -> テキスト", () => {
  it.each(ROUND_TRIP_EXAMPLES)("%s は解析して再出力すると元のテキストと完全に一致する", (name) => {
    const text = readFixture(name);
    expect(serialize(parse(text).notebook)).toBe(text);
  });

  it.each(EXAMPLE_FIXTURES)("%s は再解析しても同じ構造化データになる", (name) => {
    const notebook = parse(readFixture(name)).notebook;
    expect(parse(serialize(notebook)).notebook).toEqual(notebook);
  });

  it("先頭にバージョンレコードを出力する", () => {
    const notebook = parse(readFixture("example-01.txt")).notebook;
    expect(toRecordLines(notebook)[0]).toBe("JAHISTC08,1");
  });

  it("分割制御レコードは末尾に出力する(仕様書 表3-6)", () => {
    const lines = toRecordLines(parse(readFixture("split-part-1.txt")).notebook);
    expect(lines[0]).toBe("JAHISTC08,1");
    expect(lines[lines.length - 1]).toBe("911,12345678901234,2,1");
  });

  it("バージョン情報を上書きできる", () => {
    const notebook = parse(readFixture("example-01.txt")).notebook;
    expect(serialize(notebook, { version: "JAHISTC07" }).startsWith("JAHISTC07,1")).toBe(true);
  });

  it("末尾の空項目は既定で出力し、オプションで省略できる", () => {
    const notebook = parse(readFixture("example-01.txt")).notebook;
    expect(toRecordLines(notebook)[1]).toBe("1,鈴木 太郎,1,S330303,,,,,,,");
    expect(toRecordLines(notebook, { omitTrailingEmptyFields: true })[1]).toBe("1,鈴木 太郎,1,S330303");
  });

  it("末尾の空項目を省略しても解析結果は変わらない", () => {
    const notebook = parse(readFixture("example-04.txt")).notebook;
    const compact = serialize(notebook, { omitTrailingEmptyFields: true });
    expect(compact.length).toBeLessThan(serialize(notebook).length);
    expect(parse(compact).notebook).toEqual(notebook);
  });

  it("レコード終端を指定できる", () => {
    const notebook = parse(readFixture("example-01.txt")).notebook;
    expect(serialize(notebook, { newline: "\n" }).includes("\r")).toBe(false);
  });

  it("項目値に半角カンマ・改行が含まれる場合は SerializeError になる", () => {
    const notebook = parse(readFixture("example-01.txt")).notebook;

    notebook.patient!.name = "鈴木,太郎";
    expect(() => serialize(notebook)).toThrow(SerializeError);
    expect(() => serialize(notebook)).toThrow(/全角カンマに置き換える/);

    notebook.patient!.name = "鈴木\n太郎";
    expect(() => serialize(notebook)).toThrow(SerializeError);
  });

  it("未知のレコードもそのまま再出力する", () => {
    const text = "JAHISTC08,1\r\n1,鈴木 太郎,1,S330303,,,,,,,\r\n999,将来の拡張,X";
    expect(serialize(parse(text).notebook)).toBe(text);
  });

  it("構造化データを組み立ててお薬手帳データを出力できる", () => {
    const notebook: MedicationNotebook = {
      version: "JAHISTC08",
      outputCategory: "1",
      patient: { name: "鈴木 太郎", sex: "1", birthDate: "S330303" },
      patientRemarks: [],
      otcDrugs: [],
      notebookMemos: [],
      familyPharmacists: [],
      unknownRecords: [],
      dispensings: [
        {
          date: "R020410",
          recordCreator: "1",
          institution: {
            name: "株式会社 工業会薬局 駅前店",
            prefectureCode: "13",
            scoreTableCode: "4",
            institutionCode: "1234567",
            recordCreator: "1",
          },
          prescribingInstitution: {
            name: "医療法人 工業会病院",
            prefectureCode: "13",
            scoreTableCode: "1",
            institutionCode: "1234567",
            recordCreator: "1",
          },
          doctorGroups: [
            {
              rps: [
                {
                  rpNumber: "1",
                  drugs: [
                    {
                      name: "ｺﾘｵﾊﾟﾝｶﾌﾟｾﾙ5mg",
                      dose: "4",
                      unitName: "Ｃ",
                      codeType: "2",
                      code: "620004992",
                      recordCreator: "1",
                      supplements: [],
                      cautions: [],
                    },
                    {
                      name: "ﾌｪﾛﾍﾞﾘﾝ配合錠",
                      dose: "4",
                      unitName: "錠",
                      codeType: "2",
                      code: "620425801",
                      recordCreator: "1",
                      supplements: [],
                      cautions: [],
                    },
                  ],
                  usage: {
                    name: "【分２ 朝夕食後服用】",
                    dispensingQuantity: "5",
                    dispensingUnit: "日分",
                    dosageFormCode: "1",
                    codeType: "1",
                    recordCreator: "1",
                  },
                  usageSupplements: [],
                  prescriptionCautions: [],
                  orphanDrugNotes: [],
                },
              ],
            },
          ],
          cautions: [],
          providedInfos: [],
          remainingDrugChecks: [],
          remarks: [],
          patientEntries: [],
        },
      ],
    };

    expect(serialize(notebook)).toBe(
      [
        "JAHISTC08,1",
        "1,鈴木 太郎,1,S330303,,,,,,,",
        "5,R020410,1",
        "11,株式会社 工業会薬局 駅前店,13,4,1234567,,,,1",
        "51,医療法人 工業会病院,13,1,1234567,1",
        "201,1,ｺﾘｵﾊﾟﾝｶﾌﾟｾﾙ5mg,4,Ｃ,2,620004992,1,,,",
        "201,1,ﾌｪﾛﾍﾞﾘﾝ配合錠,4,錠,2,620425801,1,,,",
        "301,1,【分２ 朝夕食後服用】,5,日分,1,1,,1",
      ].join("\r\n"),
    );
    expect(parse(serialize(notebook)).issues).toEqual([]);
  });
});
