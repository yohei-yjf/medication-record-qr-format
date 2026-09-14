/**
 * JAHIS電子版お薬手帳データフォーマット仕様書 Ver.2.6「別表 各種コード表」および
 * 各レコードレイアウトの備考欄で定義されているコード表。
 */
export interface CodeTable {
  /** コード表の識別名 */
  readonly name: string;
  /** 仕様書上の名称 */
  readonly label: string;
  /** コード値 -> 内容 */
  readonly values: Readonly<Record<string, string>>;
  readonly note?: string;
}

/** 別表１ 年号区分コード */
export const ERA: CodeTable = {
  name: "era",
  label: "年号区分コード",
  values: { M: "明治", T: "大正", S: "昭和", H: "平成", R: "令和" },
};

const PREFECTURE_NAMES = [
  "北海道", "青森", "岩手", "宮城", "秋田", "山形", "福島", "茨城", "栃木", "群馬",
  "埼玉", "千葉", "東京", "神奈川", "新潟", "富山", "石川", "福井", "山梨", "長野",
  "岐阜", "静岡", "愛知", "三重", "滋賀", "京都", "大阪", "兵庫", "奈良", "和歌山",
  "鳥取", "島根", "岡山", "広島", "山口", "徳島", "香川", "愛媛", "高知", "福岡",
  "佐賀", "長崎", "熊本", "大分", "宮崎", "鹿児島", "沖縄",
];

/** 別表２ 都道府県コード */
export const PREFECTURE: CodeTable = {
  name: "prefecture",
  label: "都道府県コード",
  values: Object.fromEntries(PREFECTURE_NAMES.map((name, index) => [String(index + 1).padStart(2, "0"), name])),
};

/** 別表３ 点数表コード */
export const SCORE_TABLE: CodeTable = {
  name: "scoreTable",
  label: "点数表コード",
  values: { "1": "医科", "3": "歯科", "4": "調剤" },
  note: "処方－医療機関レコード(51)では 1:医科 / 3:歯科 のみ。",
};

/** 別表４ 剤形コード */
export const DOSAGE_FORM: CodeTable = {
  name: "dosageForm",
  label: "剤形コード",
  values: {
    "1": "内服",
    "2": "内滴",
    "3": "屯服",
    "4": "注射",
    "5": "外用",
    "6": "浸煎",
    "7": "湯",
    "9": "材料",
    "10": "その他",
  },
};

/** バージョンレコード 出力区分 */
export const OUTPUT_CATEGORY: CodeTable = {
  name: "outputCategory",
  label: "出力区分",
  values: {
    "1": "医療機関・薬局から患者等に情報を提供する場合",
    "2": "患者等から医療機関・薬局に情報を提供する場合",
  },
};

/** レコード作成者 */
export const RECORD_CREATOR: CodeTable = {
  name: "recordCreator",
  label: "レコード作成者",
  values: { "1": "医療関係者", "2": "患者等", "8": "その他", "9": "不明" },
};

/** 患者特記種別 (患者特記レコード) */
export const PATIENT_REMARK_TYPE: CodeTable = {
  name: "patientRemarkType",
  label: "患者特記種別",
  values: { "1": "アレルギー歴", "2": "副作用歴", "3": "既往歴", "9": "その他" },
};

/** 薬品コード種別 (薬品レコード) */
export const DRUG_CODE_TYPE: CodeTable = {
  name: "drugCodeType",
  label: "薬品コード種別",
  values: {
    "1": "コードなし",
    "2": "レセプト電算コード",
    "3": "厚労省コード",
    "4": "YJコード",
    "6": "HOTコード",
  },
};

/** 一般名コード種別 (薬品レコード) */
export const GENERAL_NAME_CODE_TYPE: CodeTable = {
  name: "generalNameCodeType",
  label: "一般名コード種別",
  values: { "1": "コードなし", "2": "一般名コード" },
};

/** 成分コード種別 (要指導医薬品・一般用医薬品成分レコード) */
export const INGREDIENT_CODE_TYPE: CodeTable = {
  name: "ingredientCodeType",
  label: "コード種別",
  values: { "1": "コードなし", "2": "成分名コード(セルフメディケーションデータベースセンター)" },
};

/** 用法コード種別 (用法レコード) */
export const USAGE_CODE_TYPE: CodeTable = {
  name: "usageCodeType",
  label: "用法コード種別",
  values: { "1": "コードなし", "2": "JAMI用法コード" },
  note: "3以降は将来の統一コードのために予約されている。",
};

/** 提供情報種別 (医療機関等提供情報レコード) */
export const PROVIDED_INFO_TYPE: CodeTable = {
  name: "providedInfoType",
  label: "提供情報種別",
  values: {
    "30": "入院中に副作用が発現した薬剤に関する情報",
    "31": "退院後の療養を担う保険医療機関での投薬又は保険薬局での調剤に必要な服薬の状況及び投薬上の工夫に関する情報",
    "99": "その他",
  },
};

/** 性別 (患者情報レコード) */
export const SEX: CodeTable = {
  name: "sex",
  label: "患者性別",
  values: { "1": "男", "2": "女" },
};

export const CODE_TABLES = {
  era: ERA,
  prefecture: PREFECTURE,
  scoreTable: SCORE_TABLE,
  dosageForm: DOSAGE_FORM,
  outputCategory: OUTPUT_CATEGORY,
  recordCreator: RECORD_CREATOR,
  patientRemarkType: PATIENT_REMARK_TYPE,
  drugCodeType: DRUG_CODE_TYPE,
  generalNameCodeType: GENERAL_NAME_CODE_TYPE,
  ingredientCodeType: INGREDIENT_CODE_TYPE,
  usageCodeType: USAGE_CODE_TYPE,
  providedInfoType: PROVIDED_INFO_TYPE,
  sex: SEX,
} as const satisfies Record<string, CodeTable>;

export type CodeTableName = keyof typeof CODE_TABLES;

/** コード値がコード表に定義されているかを判定する。 */
export const isValidCode = (table: CodeTable, value: string): boolean =>
  Object.prototype.hasOwnProperty.call(table.values, value);

/** コード値に対応する内容を返す(未定義の場合は undefined)。 */
export const describeCode = (table: CodeTable, value: string): string | undefined => table.values[value];
