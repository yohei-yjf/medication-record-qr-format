import type { CodeTableName } from "./codes.js";

/** 構造化データ上のレコード種別 */
export const RECORD_KIND = {
  version: "version",
  patient: "patient",
  patientRemark: "patientRemark",
  otcDrug: "otcDrug",
  otcDrugIngredient: "otcDrugIngredient",
  notebookMemo: "notebookMemo",
  dispensingDate: "dispensingDate",
  dispensingInstitution: "dispensingInstitution",
  dispensingStaff: "dispensingStaff",
  prescribingInstitution: "prescribingInstitution",
  prescribingDoctor: "prescribingDoctor",
  drug: "drug",
  drugSupplement: "drugSupplement",
  drugCaution: "drugCaution",
  usage: "usage",
  usageSupplement: "usageSupplement",
  prescriptionCaution: "prescriptionCaution",
  caution: "caution",
  providedInfo: "providedInfo",
  remainingDrugCheck: "remainingDrugCheck",
  remark: "remark",
  patientEntry: "patientEntry",
  familyPharmacist: "familyPharmacist",
  splitControl: "splitControl",
} as const;

export type RecordKind = (typeof RECORD_KIND)[keyof typeof RECORD_KIND];

/**
 * レコード番号。
 * バージョンレコードのみレコード番号を持たず、先頭項目がバージョン情報(`JAHISTC**`)になる。
 */
export const RECORD_NO = {
  patient: "1",
  patientRemark: "2",
  otcDrug: "3",
  otcDrugIngredient: "31",
  notebookMemo: "4",
  dispensingDate: "5",
  dispensingInstitution: "11",
  dispensingStaff: "15",
  prescribingInstitution: "51",
  prescribingDoctor: "55",
  drug: "201",
  drugSupplement: "281",
  drugCaution: "291",
  usage: "301",
  usageSupplement: "311",
  prescriptionCaution: "391",
  caution: "401",
  providedInfo: "411",
  remainingDrugCheck: "421",
  remark: "501",
  patientEntry: "601",
  familyPharmacist: "701",
  splitControl: "911",
} as const;

export type RecordNo = (typeof RECORD_NO)[keyof typeof RECORD_NO];

/** 仕様書 表3-2「データ型」 */
export type FieldType =
  /** 9: 数値 */
  | "9"
  /** X: 英数字、ピリオド、ハイフン */
  | "X"
  /** N: 文字列(全角半角混在可) */
  | "N";

/**
 * 必須区分。仕様書のレコードレイアウトは情報の提供方向ごとに必須項目が異なる。
 * - `both`: どちらの方向でも必須
 * - `toPatient`: 医療機関・薬局 -> 患者等 の場合に必須
 * - `toProvider`: 患者等 -> 医療機関・薬局 の場合に必須
 * - `conditional`: 条件付きで必須(備考欄に条件が記載されている項目)
 * - 省略: 任意
 */
export type RequiredKind = "both" | "toPatient" | "toProvider" | "conditional";

export interface FieldSpec {
  /** レコード内の項目位置(レコード番号を 0 とした 1 始まりの連番) */
  readonly index: number;
  /** 構造化データ上のキー */
  readonly key: string;
  /** 仕様書上の項目名称 */
  readonly label: string;
  /** 仕様書上の型 */
  readonly type: FieldType;
  /** 仕様書上のバイト数 */
  readonly bytes: number;
  readonly required?: RequiredKind;
  /** 年月日項目(西暦8桁 YYYYMMDD / 和暦7桁 GYYMMDD) */
  readonly isDate?: boolean;
  readonly codeTable?: CodeTableName;
  readonly note?: string;
}

export interface RecordSpec {
  readonly recordNo: string;
  readonly kind: RecordKind;
  /** 仕様書上のレコード名称 */
  readonly label: string;
  /** 仕様書 表3-8「レコード出力条件」の同一№レコード出力 */
  readonly repetition: "不可" | "可" | "１調剤情報に１レコード" | "１ＲＰに１レコード" | "１ＲＰに複数レコード出力可" | "１薬品に複数レコード出力可" | "１用法に複数レコード出力可";
  /** 先頭項目がRP番号のレコード */
  readonly rpScoped?: boolean;
  readonly fields: readonly FieldSpec[];
  readonly note?: string;
}

const f = (
  index: number,
  key: string,
  label: string,
  type: FieldType,
  bytes: number,
  extra: Omit<FieldSpec, "index" | "key" | "label" | "type" | "bytes"> = {},
): FieldSpec => ({ index, key, label, type, bytes, ...extra });

const recordCreator = (index: number): FieldSpec =>
  f(index, "recordCreator", "レコード作成者", "9", 1, { required: "both", codeTable: "recordCreator" });

const rpNumber = (): FieldSpec => f(1, "rpNumber", "RP番号", "9", 3, { required: "both" });

/** RP番号 + 内容 + レコード作成者 のレイアウト */
const rpTextFields = (label: string, bytes: number): readonly FieldSpec[] => [
  rpNumber(),
  f(2, "text", label, "N", bytes, { required: "both" }),
  recordCreator(3),
];

/** 内容 + レコード作成者 のレイアウト */
const textFields = (label: string, bytes: number): readonly FieldSpec[] => [
  f(1, "text", label, "N", bytes, { required: "both" }),
  recordCreator(2),
];

/** 表3-9 バージョンレコード */
export const VERSION_RECORD_SPEC = {
  label: "バージョンレコード",
  fields: [
    f(0, "version", "バージョン情報", "X", 9, { required: "both" }),
    f(1, "outputCategory", "出力区分", "9", 1, { required: "both", codeTable: "outputCategory" }),
  ] as const,
} as const;

export const RECORD_SPECS: readonly RecordSpec[] = [
  {
    // 表3-10
    recordNo: RECORD_NO.patient,
    kind: RECORD_KIND.patient,
    label: "患者情報レコード",
    repetition: "不可",
    fields: [
      f(1, "name", "患者氏名", "N", 40, { required: "both" }),
      f(2, "sex", "患者性別", "9", 1, { required: "both", codeTable: "sex" }),
      f(3, "birthDate", "患者生年月日", "X", 8, { required: "both", isDate: true }),
      f(4, "postalCode", "患者郵便番号", "X", 8),
      f(5, "address", "患者住所", "N", 800),
      f(6, "phone", "患者電話番号", "X", 13),
      f(7, "emergencyContact", "緊急連絡先", "N", 800),
      f(8, "bloodType", "血液型", "N", 20),
      f(9, "weight", "体重", "X", 7, { note: "kgで記録。整数3桁+小数点+小数3桁" }),
      f(10, "kanaName", "患者氏名カナ", "N", 40),
    ],
  },
  {
    // 表3-11
    recordNo: RECORD_NO.patientRemark,
    kind: RECORD_KIND.patientRemark,
    label: "患者特記レコード",
    repetition: "可",
    fields: [
      f(1, "remarkType", "患者特記種別", "9", 1, { required: "both", codeTable: "patientRemarkType" }),
      f(2, "text", "患者特記内容", "N", 120, { required: "both" }),
      recordCreator(3),
    ],
  },
  {
    // 表3-12
    recordNo: RECORD_NO.otcDrug,
    kind: RECORD_KIND.otcDrug,
    label: "要指導医薬品・一般用医薬品服用レコード",
    repetition: "可",
    fields: [
      f(1, "name", "薬品名称", "N", 120, { required: "both" }),
      f(2, "startDate", "服用開始年月日", "X", 8, { isDate: true }),
      f(3, "endDate", "服用終了年月日", "X", 8, { isDate: true }),
      recordCreator(4),
      f(5, "sequence", "要指導医薬品・一般用医薬品レコード通番", "9", 3, {
        note: "成分レコード(31)を記録する場合は必須",
      }),
      f(6, "janCode", "ＪＡＮコード", "9", 13),
    ],
  },
  {
    // 表3-13
    recordNo: RECORD_NO.otcDrugIngredient,
    kind: RECORD_KIND.otcDrugIngredient,
    label: "要指導医薬品・一般用医薬品成分レコード",
    repetition: "可",
    fields: [
      f(1, "otcDrugSequence", "要指導医薬品・一般用医薬品レコード通番", "9", 3, { required: "both" }),
      f(2, "name", "成分名", "N", 256, { required: "both" }),
      f(3, "codeType", "コード種別", "9", 1, { required: "both", codeTable: "ingredientCodeType" }),
      f(4, "code", "成分コード", "X", 20, { note: "コード種別が「1:コードなし」の場合は省略する" }),
      recordCreator(5),
    ],
  },
  {
    // 表3-14
    recordNo: RECORD_NO.notebookMemo,
    kind: RECORD_KIND.notebookMemo,
    label: "手帳メモレコード",
    repetition: "可",
    fields: [
      f(1, "text", "手帳メモ情報", "N", 400, { required: "both" }),
      f(2, "inputDate", "メモ入力年月日", "X", 8, { isDate: true }),
      recordCreator(3),
    ],
  },
  {
    // 表3-15
    recordNo: RECORD_NO.dispensingDate,
    kind: RECORD_KIND.dispensingDate,
    label: "調剤等年月日レコード",
    repetition: "１調剤情報に１レコード",
    note: "1回の来院・来局を表す調剤情報グループの開始レコード。",
    fields: [
      f(1, "date", "調剤等年月日", "X", 8, { required: "both", isDate: true }),
      recordCreator(2),
    ],
  },
  {
    // 表3-16
    recordNo: RECORD_NO.dispensingInstitution,
    kind: RECORD_KIND.dispensingInstitution,
    label: "調剤－医療機関等レコード",
    repetition: "１調剤情報に１レコード",
    fields: [
      f(1, "name", "医療機関等名称", "N", 120, { required: "both" }),
      f(2, "prefectureCode", "医療機関等都道府県", "X", 2, { required: "toPatient", codeTable: "prefecture" }),
      f(3, "scoreTableCode", "医療機関等点数表", "X", 1, { required: "toPatient", codeTable: "scoreTable" }),
      f(4, "institutionCode", "医療機関等コード", "X", 7, {
        required: "toPatient",
        note: "遡及指定申請中の場合は省略可。0から始まる場合も7桁固定で記録する",
      }),
      f(5, "postalCode", "医療機関等郵便番号", "X", 8),
      f(6, "address", "医療機関等住所", "N", 800),
      f(7, "phone", "医療機関等電話番号", "X", 13),
      recordCreator(8),
    ],
  },
  {
    // 表3-17
    recordNo: RECORD_NO.dispensingStaff,
    kind: RECORD_KIND.dispensingStaff,
    label: "調剤－医師・薬剤師レコード",
    repetition: "１調剤情報に１レコード",
    fields: [
      f(1, "name", "医師・薬剤師氏名", "N", 40, { required: "both" }),
      f(2, "contact", "医師・薬剤師連絡先", "N", 800),
      recordCreator(3),
    ],
  },
  {
    // 表3-18
    recordNo: RECORD_NO.prescribingInstitution,
    kind: RECORD_KIND.prescribingInstitution,
    label: "処方－医療機関レコード",
    repetition: "１調剤情報に１レコード",
    note: "薬局で調剤を行った場合にのみ出力する。",
    fields: [
      f(1, "name", "医療機関名称", "N", 120, { required: "both" }),
      f(2, "prefectureCode", "医療機関都道府県", "X", 2, { required: "toPatient", codeTable: "prefecture" }),
      f(3, "scoreTableCode", "医療機関点数表", "X", 1, { required: "toPatient", codeTable: "scoreTable" }),
      f(4, "institutionCode", "医療機関コード", "X", 7, { required: "toPatient" }),
      recordCreator(5),
    ],
  },
  {
    // 表3-19
    recordNo: RECORD_NO.prescribingDoctor,
    kind: RECORD_KIND.prescribingDoctor,
    label: "処方－医師レコード",
    repetition: "可",
    note: "当レコード以降、次の処方－医師レコードが出現するまでのRP情報は、この医師により処方されたものとみなす。",
    fields: [
      f(1, "name", "医師氏名", "N", 40, { required: "both" }),
      f(2, "departmentName", "診療科名", "N", 80),
      recordCreator(3),
    ],
  },
  {
    // 表3-20
    recordNo: RECORD_NO.drug,
    kind: RECORD_KIND.drug,
    label: "薬品レコード",
    repetition: "１ＲＰに複数レコード出力可",
    rpScoped: true,
    fields: [
      rpNumber(),
      f(2, "name", "薬品名称", "N", 120, { required: "both" }),
      f(3, "dose", "用量", "X", 12, {
        required: "toPatient",
        note: "内服:1日量、内滴:全量、屯服:1回量、外用:全量、注射:全量、浸煎薬:1日量、湯薬:1日量、材料:全量、その他:全量",
      }),
      f(4, "unitName", "単位名", "N", 12, { required: "toPatient" }),
      f(5, "codeType", "薬品コード種別", "9", 1, { required: "toPatient", codeTable: "drugCodeType" }),
      f(6, "code", "薬品コード", "X", 13, {
        required: "conditional",
        note: "薬品コード種別が「1:コードなし」の場合は省略する",
      }),
      recordCreator(7),
      f(8, "generalName", "一般名", "N", 120),
      f(9, "generalNameCodeType", "一般名コード種別", "9", 1, { codeTable: "generalNameCodeType" }),
      f(10, "generalNameCode", "一般名コード", "X", 12, {
        note: "一般名コード種別が「1:コードなし」の場合は省略する",
      }),
    ],
  },
  {
    // 表3-21
    recordNo: RECORD_NO.drugSupplement,
    kind: RECORD_KIND.drugSupplement,
    label: "薬品補足レコード",
    repetition: "１薬品に複数レコード出力可",
    rpScoped: true,
    note: "直前の薬品レコード(201)を補足する。",
    fields: rpTextFields("薬品補足情報", 100),
  },
  {
    // 表3-22
    recordNo: RECORD_NO.drugCaution,
    kind: RECORD_KIND.drugCaution,
    label: "薬品服用注意レコード",
    repetition: "１薬品に複数レコード出力可",
    rpScoped: true,
    note: "直前の薬品レコード(201)に対する注意事項。",
    fields: rpTextFields("内容", 400),
  },
  {
    // 表3-23
    recordNo: RECORD_NO.usage,
    kind: RECORD_KIND.usage,
    label: "用法レコード",
    repetition: "１ＲＰに１レコード",
    rpScoped: true,
    fields: [
      rpNumber(),
      f(2, "name", "用法名称", "N", 100, {
        required: "conditional",
        note: "薬局が出力する場合、剤形コードが「材料」「その他」以外は必須。医療機関では出力困難な場合は省略可",
      }),
      f(3, "dispensingQuantity", "調剤数量", "9", 3, {
        required: "toPatient",
        note: "内服:投与日数、内滴:1固定、屯服:投与回数、外用:1固定、注射:1固定、浸煎薬・湯薬:投与日数、材料:1固定、その他:1固定",
      }),
      f(4, "dispensingUnit", "調剤単位", "N", 100, {
        required: "toPatient",
        note: "内服:日分、内滴:調剤、屯服:回分、注射:調剤、外用:調剤、浸煎・湯薬:日分、材料:調剤、その他:調剤",
      }),
      f(5, "dosageFormCode", "剤形コード", "X", 2, { required: "toPatient", codeTable: "dosageForm" }),
      f(6, "codeType", "用法コード種別", "9", 1, { required: "toPatient", codeTable: "usageCodeType" }),
      f(7, "code", "用法コード", "X", 16, {
        required: "conditional",
        note: "用法コード種別が「1:コードなし」の場合は省略する",
      }),
      recordCreator(8),
    ],
  },
  {
    // 表3-24
    recordNo: RECORD_NO.usageSupplement,
    kind: RECORD_KIND.usageSupplement,
    label: "用法補足レコード",
    repetition: "１用法に複数レコード出力可",
    rpScoped: true,
    fields: rpTextFields("用法補足情報", 100),
  },
  {
    // 表3-25
    recordNo: RECORD_NO.prescriptionCaution,
    kind: RECORD_KIND.prescriptionCaution,
    label: "処方服用注意レコード",
    repetition: "１ＲＰに複数レコード出力可",
    rpScoped: true,
    fields: rpTextFields("内容", 400),
  },
  {
    // 表3-26
    recordNo: RECORD_NO.caution,
    kind: RECORD_KIND.caution,
    label: "服用注意レコード",
    repetition: "可",
    note: "1回の来院・来局の投薬全体に対する服用上の注意。",
    fields: textFields("内容", 400),
  },
  {
    // 表3-27
    recordNo: RECORD_NO.providedInfo,
    kind: RECORD_KIND.providedInfo,
    label: "医療機関等提供情報レコード",
    repetition: "可",
    fields: [
      f(1, "text", "内容", "N", 400, { required: "both" }),
      f(2, "infoType", "提供情報種別", "9", 2, { required: "both", codeTable: "providedInfoType" }),
      recordCreator(3),
    ],
  },
  {
    // 表3-28
    recordNo: RECORD_NO.remainingDrugCheck,
    kind: RECORD_KIND.remainingDrugCheck,
    label: "残薬確認レコード",
    repetition: "可",
    fields: textFields("残薬内容", 400),
  },
  {
    // 表3-29
    recordNo: RECORD_NO.remark,
    kind: RECORD_KIND.remark,
    label: "備考レコード",
    repetition: "可",
    fields: textFields("備考情報", 400),
  },
  {
    // 表3-30
    recordNo: RECORD_NO.patientEntry,
    kind: RECORD_KIND.patientEntry,
    label: "患者等記入レコード",
    repetition: "可",
    fields: [
      f(1, "text", "患者等記入情報", "N", 400, { required: "both" }),
      f(2, "inputDate", "入力年月日", "X", 8, { isDate: true }),
    ],
  },
  {
    // 表3-31
    recordNo: RECORD_NO.familyPharmacist,
    kind: RECORD_KIND.familyPharmacist,
    label: "かかりつけ薬剤師レコード",
    repetition: "可",
    fields: [
      f(1, "name", "かかりつけ薬剤師氏名", "N", 40, { required: "both" }),
      f(2, "pharmacyName", "勤務先薬局名称", "N", 120, { required: "both" }),
      f(3, "contact", "連絡先", "N", 800, { required: "both" }),
      f(4, "startDate", "担当開始日", "X", 8, { isDate: true }),
      f(5, "endDate", "担当終了日", "X", 8, { isDate: true }),
      recordCreator(6),
    ],
  },
  {
    // 表3-32
    recordNo: RECORD_NO.splitControl,
    kind: RECORD_KIND.splitControl,
    label: "分割制御レコード",
    repetition: "不可",
    note: "データを分割した場合のみ、分割された各データの末尾に出力する。",
    fields: [
      f(1, "dataId", "データ固有ID", "9", 14, { required: "both" }),
      f(2, "totalCount", "分割数", "9", 3, { required: "both" }),
      f(3, "sequence", "データ連番", "9", 3, { required: "both", note: "1～999" }),
    ],
  },
];

const SPEC_BY_RECORD_NO = new Map<string, RecordSpec>(RECORD_SPECS.map((spec) => [spec.recordNo, spec]));
const SPEC_BY_KIND = new Map<RecordKind, RecordSpec>(RECORD_SPECS.map((spec) => [spec.kind, spec]));

export const findRecordSpec = (recordNo: string): RecordSpec | undefined => SPEC_BY_RECORD_NO.get(recordNo);
export const recordSpecOf = (kind: RecordKind): RecordSpec | undefined => SPEC_BY_KIND.get(kind);

/**
 * 情報の提供方向。仕様書のレコード出力条件・必須区分はこの方向によって異なる。
 * バージョンレコードの出力区分に対応する。
 */
export type Direction = "toPatient" | "toProvider";

/** 出力区分(1/2)から情報の提供方向を得る。 */
export const directionOf = (outputCategory: string | undefined): Direction | undefined => {
  if (outputCategory === "1") return "toPatient";
  if (outputCategory === "2") return "toProvider";
  return undefined;
};

/** 指定した提供方向において、その項目が必須かどうかを返す。 */
export const isRequiredFor = (field: FieldSpec, direction: Direction | undefined): boolean => {
  if (field.required === "both") return true;
  if (field.required === undefined || field.required === "conditional") return false;
  // 提供方向が不明な場合は、どちらの方向でも必須である項目のみを必須として扱う
  return direction === undefined ? false : field.required === direction;
};
