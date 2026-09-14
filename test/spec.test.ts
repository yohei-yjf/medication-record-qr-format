import { describe, expect, it } from "vitest";
import {
  CODE_TABLES,
  FORMAT_VERSIONS,
  RECORD_KIND,
  RECORD_NO,
  RECORD_SPECS,
  TARGET_SPEC_VERSION,
  describeCode,
  findRecordSpec,
  isRequiredFor,
  isValidDate,
  isVersionRecord,
  recordSpecOf,
  specVersionsOf,
  versionNumberOf,
} from "../src/index.js";

describe("レコードレイアウト定義(仕様書 3.2.8)", () => {
  it("レコード番号・レコード種別が重複していない", () => {
    expect(new Set(RECORD_SPECS.map((spec) => spec.recordNo)).size).toBe(RECORD_SPECS.length);
    expect(new Set(RECORD_SPECS.map((spec) => spec.kind)).size).toBe(RECORD_SPECS.length);
  });

  it("項目位置が1から始まる連番になっている", () => {
    for (const spec of RECORD_SPECS) {
      expect(spec.fields.map((field) => field.index), spec.label).toEqual(spec.fields.map((_, i) => i + 1));
    }
  });

  it("同一レコード内で項目キーが重複していない", () => {
    for (const spec of RECORD_SPECS) {
      const keys = spec.fields.map((field) => field.key);
      expect(new Set(keys).size, spec.label).toBe(keys.length);
    }
  });

  it("コード表を参照する項目は実在するコード表を指している", () => {
    for (const spec of RECORD_SPECS) {
      for (const field of spec.fields) {
        if (field.codeTable === undefined) continue;
        expect(CODE_TABLES[field.codeTable], `${spec.label}/${field.label}`).toBeDefined();
      }
    }
  });

  it("全てのレコード種別に定義がある(バージョンレコードを除く)", () => {
    for (const kind of Object.values(RECORD_KIND)) {
      if (kind === RECORD_KIND.version) continue;
      expect(recordSpecOf(kind), kind).toBeDefined();
    }
  });

  it("主要なレコードの項目が仕様書のレイアウトと一致する", () => {
    // 表3-10 患者情報レコード
    expect(findRecordSpec(RECORD_NO.patient)!.fields.map((f) => [f.label, f.type, f.bytes])).toEqual([
      ["患者氏名", "N", 40],
      ["患者性別", "9", 1],
      ["患者生年月日", "X", 8],
      ["患者郵便番号", "X", 8],
      ["患者住所", "N", 800],
      ["患者電話番号", "X", 13],
      ["緊急連絡先", "N", 800],
      ["血液型", "N", 20],
      ["体重", "X", 7],
      ["患者氏名カナ", "N", 40],
    ]);

    // 表3-20 薬品レコード
    expect(findRecordSpec(RECORD_NO.drug)!.fields.map((f) => [f.label, f.type, f.bytes])).toEqual([
      ["RP番号", "9", 3],
      ["薬品名称", "N", 120],
      ["用量", "X", 12],
      ["単位名", "N", 12],
      ["薬品コード種別", "9", 1],
      ["薬品コード", "X", 13],
      ["レコード作成者", "9", 1],
      ["一般名", "N", 120],
      ["一般名コード種別", "9", 1],
      ["一般名コード", "X", 12],
    ]);

    // 表3-32 分割制御レコード
    expect(findRecordSpec(RECORD_NO.splitControl)!.fields.map((f) => [f.label, f.type, f.bytes])).toEqual([
      ["データ固有ID", "9", 14],
      ["分割数", "9", 3],
      ["データ連番", "9", 3],
    ]);
  });

  it("必須区分は情報の提供方向によって変わる", () => {
    const institution = findRecordSpec(RECORD_NO.dispensingInstitution)!;
    const prefecture = institution.fields.find((field) => field.key === "prefectureCode")!;

    // 医療機関等都道府県は「医療機関等⇒患者等」でのみ必須
    expect(isRequiredFor(prefecture, "toPatient")).toBe(true);
    expect(isRequiredFor(prefecture, "toProvider")).toBe(false);

    const name = institution.fields.find((field) => field.key === "name")!;
    expect(isRequiredFor(name, "toPatient")).toBe(true);
    expect(isRequiredFor(name, "toProvider")).toBe(true);
  });
});

describe("別表 各種コード表", () => {
  it("別表１ 年号区分コード", () => {
    expect(CODE_TABLES.era.values).toEqual({ M: "明治", T: "大正", S: "昭和", H: "平成", R: "令和" });
  });

  it("別表２ 都道府県コード", () => {
    expect(Object.keys(CODE_TABLES.prefecture.values)).toHaveLength(47);
    expect(describeCode(CODE_TABLES.prefecture, "01")).toBe("北海道");
    expect(describeCode(CODE_TABLES.prefecture, "13")).toBe("東京");
    expect(describeCode(CODE_TABLES.prefecture, "47")).toBe("沖縄");
    expect(describeCode(CODE_TABLES.prefecture, "48")).toBeUndefined();
  });

  it("別表３ 点数表コード", () => {
    expect(CODE_TABLES.scoreTable.values).toEqual({ "1": "医科", "3": "歯科", "4": "調剤" });
  });

  it("別表４ 剤形コード", () => {
    expect(CODE_TABLES.dosageForm.values).toEqual({
      "1": "内服",
      "2": "内滴",
      "3": "屯服",
      "4": "注射",
      "5": "外用",
      "6": "浸煎",
      "7": "湯",
      "9": "材料",
      "10": "その他",
    });
  });

  it("レコード作成者・薬品コード種別・提供情報種別", () => {
    expect(CODE_TABLES.recordCreator.values).toEqual({
      "1": "医療関係者",
      "2": "患者等",
      "8": "その他",
      "9": "不明",
    });
    expect(CODE_TABLES.drugCodeType.values).toEqual({
      "1": "コードなし",
      "2": "レセプト電算コード",
      "3": "厚労省コード",
      "4": "YJコード",
      "6": "HOTコード",
    });
    expect(Object.keys(CODE_TABLES.providedInfoType.values)).toEqual(["30", "31", "99"]);
  });
});

describe("バージョン情報(仕様書 3.1)", () => {
  it("Ver.2.6 のバージョン情報は JAHISTC08", () => {
    expect(specVersionsOf("JAHISTC08")).toContain(TARGET_SPEC_VERSION);
    expect(versionNumberOf("JAHISTC08")).toBe(8);
  });

  it("改訂履歴どおりのバージョン対応になっている", () => {
    const map = Object.fromEntries(FORMAT_VERSIONS.map((info) => [info.version, info.specVersions]));
    expect(map).toEqual({
      JAHISTC01: ["1.0"],
      JAHISTC02: ["1.1"],
      JAHISTC03: ["2.0"],
      JAHISTC04: ["2.1"],
      JAHISTC05: ["2.2"],
      JAHISTC06: ["2.3"],
      JAHISTC07: ["2.4"],
      JAHISTC08: ["2.5", "2.6"],
    });
  });

  it("バージョン情報は JAHISTC + 2桁数字(9桁固定)", () => {
    expect(isVersionRecord("JAHISTC08")).toBe(true);
    expect(isVersionRecord("JAHISTC12")).toBe(true);
    expect(isVersionRecord("JAHISTC8")).toBe(false);
    expect(isVersionRecord("1")).toBe(false);
  });
});

describe("年月日の書式", () => {
  it("西暦8桁 YYYYMMDD を受け付ける", () => {
    expect(isValidDate("20200410")).toBe(true);
    expect(isValidDate("20200431")).toBe(false);
    expect(isValidDate("20250230")).toBe(false);
  });

  it("和暦7桁 GYYMMDD を受け付ける", () => {
    expect(isValidDate("R020410")).toBe(true);
    expect(isValidDate("S330303")).toBe(true);
    expect(isValidDate("H280411")).toBe(true);
    expect(isValidDate("X020410")).toBe(false);
    expect(isValidDate("R021310")).toBe(false);
  });
});
