import { describe, expect, it } from "vitest";
import { ISSUE_CODE, collectDrugs, collectRps, parse, parseOrThrow } from "../src/index.js";
import { EXAMPLE_FIXTURES, readFixture } from "./helpers.js";

/**
 * 仕様書「付録１ お薬手帳イメージと出力データ例」の出力データ例をそのまま解析する。
 *
 * 例7・例11(かかりつけ薬剤師レコードの「連絡先」)と例8(医療機関等提供情報レコードの項目数)は、
 * 出力データ例がレコードレイアウト(表3-31 / 表3-27)と一致していないため、
 * 検証でエラー・警告が出ることを期待値としている。
 */
const CLEAN_EXAMPLES = EXAMPLE_FIXTURES.filter(
  (name) => !["example-07.txt", "example-08.txt", "example-11.txt"].includes(name),
);

describe("付録１ 出力データ例の解析", () => {
  it.each(CLEAN_EXAMPLES)("%s はエラー・警告なしで解析できる", (name) => {
    const result = parse(readFixture(name));
    expect(result.issues).toEqual([]);
    expect(result.ok).toBe(true);
  });

  it.each(EXAMPLE_FIXTURES)("%s はバージョンレコードを読み取れる", (name) => {
    const { notebook } = parse(readFixture(name));
    expect(notebook.version).toBe("JAHISTC08");
    expect(notebook.specVersions).toContain("2.6");
    expect(notebook.outputCategory).toMatch(/^[12]$/);
  });
});

describe("例1: 薬局で出力(内服薬のみ)", () => {
  const { notebook } = parse(readFixture("example-01.txt"));

  it("患者情報を和暦の生年月日とともに読み取れる", () => {
    expect(notebook.patient).toEqual({
      name: "鈴木 太郎",
      sex: "1",
      birthDate: "S330303",
      postalCode: undefined,
      address: undefined,
      phone: undefined,
      emergencyContact: undefined,
      bloodType: undefined,
      weight: undefined,
      kanaName: undefined,
    });
  });

  it("調剤情報グループを組み立てる", () => {
    expect(notebook.dispensings).toHaveLength(1);
    const dispensing = notebook.dispensings[0]!;
    expect(dispensing.date).toBe("R020410");
    expect(dispensing.institution).toMatchObject({
      name: "株式会社 工業会薬局 駅前店",
      prefectureCode: "13",
      scoreTableCode: "4",
      institutionCode: "1234567",
    });
    expect(dispensing.prescribingInstitution).toMatchObject({
      name: "医療法人 工業会病院",
      scoreTableCode: "1",
    });
  });

  it("RPごとに薬品と用法をまとめる", () => {
    const rps = collectRps(notebook).map((context) => context.rp);
    expect(rps.map((rp) => rp.rpNumber)).toEqual(["1", "2"]);

    expect(rps[0]!.drugs.map((drug) => drug.name)).toEqual(["ｺﾘｵﾊﾟﾝｶﾌﾟｾﾙ5mg", "ﾌｪﾛﾍﾞﾘﾝ配合錠"]);
    expect(rps[0]!.drugs[0]).toMatchObject({ dose: "4", unitName: "Ｃ", codeType: "2", code: "620004992" });
    expect(rps[0]!.usage).toMatchObject({
      name: "【分２ 朝夕食後服用】",
      dispensingQuantity: "5",
      dispensingUnit: "日分",
      dosageFormCode: "1",
    });

    expect(rps[1]!.drugs).toHaveLength(3);
    expect(rps[1]!.usage?.name).toBe("【分３ 毎食後服用】");
  });

  it("処方－医師レコードが無い場合は医師を持たない1グループになる", () => {
    const groups = notebook.dispensings[0]!.doctorGroups;
    expect(groups).toHaveLength(1);
    expect(groups[0]!.doctor).toBeUndefined();
  });
});

describe("例2: 薬局で出力(内服薬以外を含む)", () => {
  const { notebook } = parse(readFixture("example-02.txt"));

  it("剤形コードごとの用法を読み取れる", () => {
    const usages = collectRps(notebook).map((context) => context.rp.usage);
    expect(usages.map((usage) => usage?.dosageFormCode)).toEqual(["1", "1", "5", "4", "9", "10"]);
    // 材料・その他は用法名称が無くてもよい
    expect(usages[4]?.name).toBeUndefined();
    expect(usages[5]?.name).toBeUndefined();
  });

  it("薬品コード種別が「1:コードなし」の場合は薬品コードを持たない", () => {
    const container = collectDrugs(notebook).find((item) => item.drug.name === "容器")!;
    expect(container.drug.codeType).toBe("1");
    expect(container.drug.code).toBeUndefined();
  });
});

describe("例3: 薬品補足・用法補足を含む", () => {
  const { notebook } = parse(readFixture("example-03.txt"));

  it("薬品補足レコード(281)は直前の薬品に紐づく", () => {
    const rp = collectRps(notebook)[0]!.rp;
    expect(rp.drugs[0]!.supplements.map((note) => note.text)).toEqual(["朝：３Ｃ、昼：２Ｃ、夕：１Ｃ"]);
    expect(rp.drugs[1]!.supplements.map((note) => note.text)).toEqual(["朝：１錠、昼：３錠、夕：２錠"]);
    expect(rp.orphanDrugNotes).toEqual([]);
  });

  it("用法補足レコード(311)はRPに紐づく", () => {
    const rp = collectRps(notebook)[0]!.rp;
    expect(rp.usageSupplements.map((note) => note.text)).toEqual(["一包化"]);
  });

  it("調剤－医師・薬剤師レコード(15)と処方－医師レコード(55)を区別する", () => {
    const dispensing = notebook.dispensings[0]!;
    expect(dispensing.staff).toMatchObject({ name: "薬剤師 太郎" });
    expect(dispensing.doctorGroups[0]!.doctor).toMatchObject({ name: "工業会 次郎" });
  });
});

describe("例4: 複数診療科での出力", () => {
  const { notebook } = parse(readFixture("example-04.txt"));

  it("処方－医師レコードごとにRPをまとめる", () => {
    const groups = notebook.dispensings[0]!.doctorGroups;
    expect(groups).toHaveLength(2);
    expect(groups[0]!.doctor).toMatchObject({ name: "工業会 次郎", departmentName: "内科" });
    expect(groups[0]!.rps.map((rp) => rp.rpNumber)).toEqual(["1", "2", "3", "4", "5"]);
    expect(groups[1]!.doctor).toMatchObject({ name: "佐藤 三郎", departmentName: "皮膚科" });
    expect(groups[1]!.rps.map((rp) => rp.rpNumber)).toEqual(["6", "7"]);
  });

  it("残薬確認レコード(421)・備考レコード(501)を調剤に紐づける", () => {
    const dispensing = notebook.dispensings[0]!;
    expect(dispensing.remainingDrugChecks[0]!.text).toBe("服用忘れによりｺﾘｵﾊﾟﾝｶﾌﾟｾﾙ12錠残薬あり");
    expect(dispensing.remarks[0]!.text).toBe("正しい飲み方は薬袋等をご覧下さい。");
  });
});

describe("例5・例6: 医療機関で出力", () => {
  it("処方－医療機関レコード(51)が無くてもRPを読み取れる", () => {
    const { notebook, issues } = parse(readFixture("example-05.txt"));
    expect(issues).toEqual([]);
    expect(notebook.dispensings[0]!.prescribingInstitution).toBeUndefined();
    expect(collectRps(notebook)).toHaveLength(2);
  });

  it("用法名称は医療機関出力では省略できる", () => {
    const { notebook, issues } = parse(readFixture("example-06.txt"));
    expect(issues).toEqual([]);
    expect(collectRps(notebook).every((context) => context.rp.usage?.name === undefined)).toBe(true);
  });

  it("薬局出力で用法名称が無い場合はエラーになる(表3-23の条件付き必須)", () => {
    const text = readFixture("example-06.txt").replace(
      "11,医療法人 工業会病院,13,1,1234567,,,,1",
      "11,株式会社 工業会薬局 駅前店,13,4,1234567,,,,1\r\n51,医療法人 工業会病院,13,1,1234567,1",
    );
    const result = parse(text);
    expect(result.ok).toBe(false);
    expect(result.issues.some((issue) => issue.message.includes("「用法名称」が未設定"))).toBe(true);
  });
});

describe("例7: 患者特記・服用注意・かかりつけ薬剤師", () => {
  const result = parse(readFixture("example-07.txt"));

  it("患者情報を全項目読み取れる", () => {
    expect(result.notebook.patient).toMatchObject({
      postalCode: "105-0004",
      address: "東京都港区新橋○丁目",
      phone: "03-0000-0000",
      emergencyContact: "090-0000-0000",
      bloodType: "Ｂ＋",
      weight: "63.7",
    });
  });

  it("患者特記レコードを種別ごとに読み取れる", () => {
    expect(result.notebook.patientRemarks).toEqual([
      { remarkType: "1", text: "乳製品", recordCreator: "1" },
      { remarkType: "2", text: "セフェム系（発熱）", recordCreator: "1" },
      { remarkType: "3", text: "狭心症（2011年～）", recordCreator: "1" },
      { remarkType: "9", text: "嚥下困難", recordCreator: "1" },
    ]);
  });

  it("薬品服用注意(291)・処方服用注意(391)・服用注意(401)を区別する", () => {
    const rp = collectRps(result.notebook)[0]!.rp;
    expect(rp.drugs[0]!.cautions[0]!.text).toContain("グレープフルーツジュース");
    expect(rp.prescriptionCautions[0]!.text).toContain("めまい等が現れることがある");
    expect(result.notebook.dispensings[0]!.cautions[0]!.text).toBe("他の薬を併用する際は、相談してください。");
  });

  it("仕様書の出力データ例が表3-31と一致しないため「連絡先」が未設定と報告される", () => {
    expect(result.notebook.familyPharmacists[0]).toMatchObject({
      name: "薬剤師 太郎",
      pharmacyName: "工業会薬局 駅前店",
      contact: undefined,
    });
    const issue = result.issues.find((item) => item.code === ISSUE_CODE.missingRequiredField)!;
    expect(issue.recordNo).toBe("701");
    expect(issue.fieldKey).toBe("contact");
  });
});

describe("例8: 医薬品等を提供せずに情報提供を行う場合", () => {
  const result = parse(readFixture("example-08.txt"));

  it("提供情報を読み取れる", () => {
    const dispensing = result.notebook.dispensings[0]!;
    expect(dispensing.date).toBe("R020410");
    expect(dispensing.staff).toMatchObject({ name: "工業会 次郎" });
    expect(dispensing.providedInfos[0]).toMatchObject({
      text: "嚥下困難が見られるため、錠剤は粉砕して投与する。",
      infoType: "31",
    });
    expect(dispensing.doctorGroups).toEqual([]);
  });

  it("出力データ例の項目数が表3-27と一致しないため警告・エラーを報告する", () => {
    const codes = result.issues.map((issue) => issue.code);
    expect(codes).toContain(ISSUE_CODE.tooManyFields);
    expect(codes).toContain(ISSUE_CODE.missingRequiredField);
  });
});

describe("例9: 複数調剤日をまとめて出力", () => {
  const { notebook } = parse(readFixture("example-09.txt"));

  it("調剤等年月日ごとに調剤情報グループを分ける", () => {
    expect(notebook.dispensings.map((dispensing) => dispensing.date)).toEqual(["R020410", "R020407"]);
    expect(notebook.dispensings.map((dispensing) => dispensing.staff?.name)).toEqual(["薬剤師 次郎", "薬剤師 太郎"]);
  });

  it("RP番号は調剤情報グループごとに1から振り直される", () => {
    expect(notebook.dispensings[0]!.doctorGroups[0]!.rps.map((rp) => rp.rpNumber)).toEqual(["1", "2"]);
    expect(notebook.dispensings[1]!.doctorGroups[0]!.rps.map((rp) => rp.rpNumber)).toEqual(["1", "2", "3"]);
  });
});

describe("例10: 患者等から医療機関・薬局への提供", () => {
  const result = parse(readFixture("example-10.txt"));

  it("出力区分2では医療機関コード等が省略されていてもエラーにならない", () => {
    expect(result.issues).toEqual([]);
    expect(result.notebook.outputCategory).toBe("2");
    expect(result.notebook.dispensings[0]!.institution).toMatchObject({
      name: "株式会社 工業会薬局 駅前店",
      prefectureCode: undefined,
      institutionCode: undefined,
    });
  });

  it("患者等記入レコード(601)を読み取れる", () => {
    expect(result.notebook.dispensings[0]!.patientEntries).toEqual([
      { text: "朝に薬を飲んだ後、めまいがあった", inputDate: "R020407" },
    ]);
  });

  it("出力区分1では同じデータが必須項目不足になる", () => {
    const asToPatient = parse(readFixture("example-10.txt").replace("JAHISTC08,2", "JAHISTC08,1"));
    expect(asToPatient.ok).toBe(false);
    expect(asToPatient.issues.some((issue) => issue.fieldKey === "prefectureCode")).toBe(true);
  });
});

describe("例11: 要指導医薬品・一般用医薬品と手帳メモ", () => {
  const { notebook } = parse(readFixture("example-11.txt"));

  it("成分レコード(31)を通番で服用レコード(3)に紐づける", () => {
    expect(notebook.otcDrugs).toHaveLength(2);
    expect(notebook.otcDrugs[0]).toMatchObject({
      name: "ﾊﾞﾌｧﾘﾝ",
      startDate: "R020406",
      endDate: "R020409",
      sequence: "1",
    });
    expect(notebook.otcDrugs[0]!.ingredients.map((item) => item.name)).toEqual([
      "イブプロフェン",
      "アセトアミノフェン",
      "無水カフェイン",
    ]);
    expect(notebook.otcDrugs[1]!.ingredients).toHaveLength(3);
    expect(notebook.otcDrugs[1]!.ingredients[2]).toMatchObject({ codeType: "1", code: undefined });
  });

  it("手帳メモレコード(4)を読み取れる", () => {
    expect(notebook.notebookMemos).toEqual([
      { text: "健康診断", inputDate: "R020411", recordCreator: "2" },
      { text: "インフルエンザ予防接種", inputDate: "R020331", recordCreator: "2" },
    ]);
  });

  it("複数の調剤情報とかかりつけ薬剤師を読み取れる", () => {
    expect(notebook.dispensings).toHaveLength(2);
    expect(notebook.familyPharmacists[0]).toMatchObject({ name: "薬剤師 次郎" });
  });
});

describe("異常系", () => {
  it("入力が空ならエラーになる", () => {
    const result = parse("");
    expect(result.ok).toBe(false);
    expect(result.issues[0]!.code).toBe(ISSUE_CODE.emptyInput);
  });

  it("先頭がバージョンレコードでなければエラーになる", () => {
    const result = parse("1,鈴木 太郎,1,S330303");
    expect(result.ok).toBe(false);
    expect(result.issues.map((issue) => issue.code)).toContain(ISSUE_CODE.missingVersionRecord);
  });

  it("未知のバージョン情報は警告として解析を継続する", () => {
    const result = parse("JAHISTC99,1\r\n1,鈴木 太郎,1,S330303");
    expect(result.ok).toBe(true);
    expect(result.issues.map((issue) => issue.code)).toContain(ISSUE_CODE.unknownVersion);
    expect(result.notebook.specVersions).toBeUndefined();
  });

  it("出力区分が無い場合はエラーになる", () => {
    const result = parse("JAHISTC08\r\n1,鈴木 太郎,1,S330303");
    expect(result.ok).toBe(false);
    expect(result.issues.some((issue) => issue.fieldKey === "outputCategory")).toBe(true);
  });

  it("必須項目が欠けている場合はエラーになる", () => {
    const result = parse("JAHISTC08,1\r\n1,鈴木 太郎");
    expect(result.ok).toBe(false);
    const issue = result.issues.find((item) => item.code === ISSUE_CODE.missingRequiredField)!;
    expect(issue.fieldKey).toBe("sex");
    expect(issue.line).toBe(2);
  });

  it("薬品コード種別が「1:コードなし」以外なのにコードが無い場合はエラーになる", () => {
    const result = parse(
      ["JAHISTC08,1", "1,鈴木 太郎,1,S330303", "5,R020410,1", "201,1,ﾉﾙﾊﾞｽｸ錠2.5mg,1,錠,2,,1,,,"].join("\r\n"),
    );
    expect(result.ok).toBe(false);
    expect(result.issues.some((issue) => issue.message.includes("「薬品コード」は必須"))).toBe(true);
  });

  it("未定義のコード値・不正な年月日・桁数超過は警告になる", () => {
    const result = parse("JAHISTC08,1\r\n1,鈴木 太郎,9,20250230,,,,,,,");
    expect(result.ok).toBe(true);
    const codes = result.issues.map((issue) => issue.code);
    expect(codes).toContain(ISSUE_CODE.invalidCode);
    expect(codes).toContain(ISSUE_CODE.invalidDate);

    const tooLong = parse(`JAHISTC08,1\r\n1,${"あ".repeat(21)},1,S330303`);
    expect(tooLong.issues.map((issue) => issue.code)).toContain(ISSUE_CODE.fieldTooLong);
  });

  it("strict では警告もエラー扱いになる", () => {
    const text = "JAHISTC08,1\r\n1,鈴木 太郎,9,S330303,,,,,,,";
    expect(parse(text).ok).toBe(true);
    expect(parse(text, { strict: true }).ok).toBe(false);
  });

  it("検証を無効にできる", () => {
    const text = "JAHISTC08,1\r\n1,鈴木 太郎,9,20250230,,,,,,,";
    expect(parse(text, { validate: false }).issues).toEqual([]);
    expect(parse(text, { checkCodeTables: false }).issues.every((issue) => issue.code !== ISSUE_CODE.invalidCode)).toBe(
      true,
    );
  });

  it("未知のレコードは警告として保持し、内容を失わない", () => {
    const result = parse("JAHISTC08,1\r\n1,鈴木 太郎,1,S330303\r\n999,将来の拡張,X");
    expect(result.ok).toBe(true);
    expect(result.notebook.unknownRecords).toEqual([{ recordNo: "999", fields: ["将来の拡張", "X"], line: 3 }]);
  });

  it("調剤等年月日より前のレコードは暗黙の調剤情報として扱う", () => {
    const result = parse("JAHISTC08,1\r\n1,鈴木 太郎,1,S330303\r\n11,株式会社 工業会薬局 駅前店,13,4,1234567,,,,1");
    expect(result.ok).toBe(true);
    expect(result.issues.map((issue) => issue.code)).toContain(ISSUE_CODE.orphanRecord);
    expect(result.notebook.dispensings[0]!.institution?.name).toBe("株式会社 工業会薬局 駅前店");
  });

  it("同一№レコードが重複した場合は警告し、最初のレコードを採用する", () => {
    const result = parse(
      ["JAHISTC08,1", "1,鈴木 太郎,1,S330303", "5,R020410,1", "11,薬局A,13,4,1234567,,,,1", "11,薬局B,13,4,7654321,,,,1"].join("\r\n"),
    );
    expect(result.issues.map((issue) => issue.code)).toContain(ISSUE_CODE.duplicateRecord);
    expect(result.notebook.dispensings[0]!.institution?.name).toBe("薬局A");
  });

  it("改行コードは CR+LF / LF / CR のいずれも受け付け、EOFを無視する", () => {
    const lines = ["JAHISTC08,1", "1,鈴木 太郎,1,S330303"];
    for (const newline of ["\r\n", "\n", "\r"]) {
      expect(parse(lines.join(newline)).notebook.patient?.name).toBe("鈴木 太郎");
    }
    expect(parse(`${lines.join("\r\n")}\r\n\x1a`).notebook.patient?.name).toBe("鈴木 太郎");
  });

  it("parseOrThrow はエラー時に例外を送出する", () => {
    expect(() => parseOrThrow(readFixture("example-01.txt"))).not.toThrow();
    expect(() => parseOrThrow("1,鈴木 太郎")).toThrow(/解析に失敗/);
  });
});
