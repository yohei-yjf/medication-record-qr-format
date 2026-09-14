/**
 * JAHIS電子版お薬手帳データの構造化データモデル。
 *
 * 各インタフェースは仕様書のレコードに対応し、プロパティ名は
 * `src/spec/records.ts` の `FieldSpec.key` と一致する。
 * 値は仕様書どおりの文字列のまま保持する(年月日は `YYYYMMDD` または和暦 `GYYMMDD`)。
 */

/** 解析前のレコード(1行 = 1レコード) */
export interface RawRecord {
  /** 1始まりの行番号 */
  readonly line: number;
  /** レコード番号(バージョンレコードのみ `JAHISTC**`) */
  readonly recordNo: string;
  /** カンマ区切りの全項目。`fields[0]` はレコード番号。 */
  readonly fields: readonly string[];
  /** 元の行文字列 */
  readonly raw: string;
}

/** 仕様上定義されていないレコード */
export interface UnknownRecord {
  readonly recordNo: string;
  readonly fields: readonly string[];
  readonly line: number;
}

/** 患者情報レコード(1) */
export interface Patient {
  name?: string;
  /** 1:男 / 2:女 */
  sex?: string;
  birthDate?: string;
  postalCode?: string;
  address?: string;
  phone?: string;
  emergencyContact?: string;
  bloodType?: string;
  /** kg */
  weight?: string;
  kanaName?: string;
}

/** 患者特記レコード(2) */
export interface PatientRemark {
  /** 1:アレルギー歴 / 2:副作用歴 / 3:既往歴 / 9:その他 */
  remarkType?: string;
  text?: string;
  recordCreator?: string;
}

/** 要指導医薬品・一般用医薬品成分レコード(31) */
export interface OtcDrugIngredient {
  name?: string;
  codeType?: string;
  code?: string;
  recordCreator?: string;
}

/** 要指導医薬品・一般用医薬品服用レコード(3) */
export interface OtcDrug {
  name?: string;
  startDate?: string;
  endDate?: string;
  recordCreator?: string;
  /** 成分レコード(31)との紐づけに使う通番 */
  sequence?: string;
  janCode?: string;
  ingredients: OtcDrugIngredient[];
}

/** 手帳メモレコード(4) */
export interface NotebookMemo {
  text?: string;
  inputDate?: string;
  recordCreator?: string;
}

/** 調剤－医療機関等レコード(11) */
export interface DispensingInstitution {
  name?: string;
  prefectureCode?: string;
  scoreTableCode?: string;
  institutionCode?: string;
  postalCode?: string;
  address?: string;
  phone?: string;
  recordCreator?: string;
}

/** 調剤－医師・薬剤師レコード(15) */
export interface DispensingStaff {
  name?: string;
  contact?: string;
  recordCreator?: string;
}

/** 処方－医療機関レコード(51) */
export interface PrescribingInstitution {
  name?: string;
  prefectureCode?: string;
  scoreTableCode?: string;
  institutionCode?: string;
  recordCreator?: string;
}

/** 処方－医師レコード(55) */
export interface PrescribingDoctor {
  name?: string;
  departmentName?: string;
  recordCreator?: string;
}

/** 内容とレコード作成者のみを持つレコード(281/291/311/391/401/421/501) */
export interface TextNote {
  text?: string;
  recordCreator?: string;
}

/** 薬品レコード(201) */
export interface Drug {
  name?: string;
  /** 用量 */
  dose?: string;
  unitName?: string;
  /** 1:コードなし / 2:レセプト電算 / 3:厚労省 / 4:YJ / 6:HOT */
  codeType?: string;
  code?: string;
  recordCreator?: string;
  generalName?: string;
  generalNameCodeType?: string;
  generalNameCode?: string;
  /** 薬品補足レコード(281) */
  supplements: TextNote[];
  /** 薬品服用注意レコード(291) */
  cautions: TextNote[];
}

/** 用法レコード(301) */
export interface Usage {
  name?: string;
  dispensingQuantity?: string;
  dispensingUnit?: string;
  /** 剤形コード(別表４) */
  dosageFormCode?: string;
  codeType?: string;
  code?: string;
  recordCreator?: string;
}

/** RP(処方指示)単位の情報 */
export interface Rp {
  /** RP番号(1～) */
  rpNumber: string;
  drugs: Drug[];
  /** 用法レコード(301)。1RPに1レコード。 */
  usage?: Usage;
  /** 用法補足レコード(311) */
  usageSupplements: TextNote[];
  /** 処方服用注意レコード(391) */
  prescriptionCautions: TextNote[];
  /** 対応する薬品レコード(201)より前に出現した薬品補足(281)・薬品服用注意(291) */
  orphanDrugNotes: TextNote[];
}

/**
 * 処方－医師レコード(55)を区切りとしたRPのまとまり。
 * 処方－医師レコードが出力されない場合は `doctor` を持たない1つのグループになる。
 */
export interface DoctorGroup {
  doctor?: PrescribingDoctor;
  rps: Rp[];
}

/** 調剤等年月日レコード(5)を起点とする1回の来院・来局の情報 */
export interface Dispensing {
  date?: string;
  recordCreator?: string;
  /** 調剤－医療機関等レコード(11) */
  institution?: DispensingInstitution;
  /** 調剤－医師・薬剤師レコード(15) */
  staff?: DispensingStaff;
  /** 処方－医療機関レコード(51)。薬局で調剤を行った場合のみ出力される。 */
  prescribingInstitution?: PrescribingInstitution;
  /** 処方－医師レコード(55)ごとのRPのまとまり */
  doctorGroups: DoctorGroup[];
  /** 服用注意レコード(401) */
  cautions: TextNote[];
  /** 医療機関等提供情報レコード(411) */
  providedInfos: Array<TextNote & { infoType?: string }>;
  /** 残薬確認レコード(421) */
  remainingDrugChecks: TextNote[];
  /** 備考レコード(501) */
  remarks: TextNote[];
  /** 患者等記入レコード(601) */
  patientEntries: Array<{ text?: string; inputDate?: string }>;
}

/** かかりつけ薬剤師レコード(701) */
export interface FamilyPharmacist {
  name?: string;
  pharmacyName?: string;
  contact?: string;
  startDate?: string;
  endDate?: string;
  recordCreator?: string;
}

/** 分割制御レコード(911) */
export interface SplitControl {
  dataId?: string;
  totalCount?: string;
  sequence?: string;
}

/** お薬手帳データ全体 */
export interface MedicationNotebook {
  /** バージョン情報 (例: "JAHISTC08") */
  version: string;
  /** バージョン情報に対応する仕様書バージョン (例: ["2.5", "2.6"]) */
  specVersions?: readonly string[];
  /** 出力区分 (1:医療機関等⇒患者等 / 2:患者等⇒医療機関等) */
  outputCategory?: string;
  patient?: Patient;
  patientRemarks: PatientRemark[];
  otcDrugs: OtcDrug[];
  notebookMemos: NotebookMemo[];
  /** 調剤等年月日が新しいものから古いものの順に並ぶ */
  dispensings: Dispensing[];
  familyPharmacists: FamilyPharmacist[];
  /** 分割制御レコード(911) */
  split?: SplitControl;
  /** 仕様上定義されていないレコード(前方互換のため保持する) */
  unknownRecords: UnknownRecord[];
}

export const createEmptyNotebook = (version: string): MedicationNotebook => ({
  version,
  patientRemarks: [],
  otcDrugs: [],
  notebookMemos: [],
  dispensings: [],
  familyPharmacists: [],
  unknownRecords: [],
});

export const createEmptyDispensing = (): Dispensing => ({
  doctorGroups: [],
  cautions: [],
  providedInfos: [],
  remainingDrugChecks: [],
  remarks: [],
  patientEntries: [],
});

export const createEmptyRp = (rpNumber: string): Rp => ({
  rpNumber,
  drugs: [],
  usageSupplements: [],
  prescriptionCautions: [],
  orphanDrugNotes: [],
});

/** 1つのRPと、それが属する調剤・医師の組み合わせ */
export interface RpContext {
  readonly dispensing: Dispensing;
  readonly doctorGroup: DoctorGroup;
  readonly rp: Rp;
}

/** お薬手帳データに含まれる全てのRPを、調剤・医師の情報とともに列挙する。 */
export const collectRps = (notebook: MedicationNotebook): RpContext[] =>
  notebook.dispensings.flatMap((dispensing) =>
    dispensing.doctorGroups.flatMap((doctorGroup) =>
      doctorGroup.rps.map((rp) => ({ dispensing, doctorGroup, rp })),
    ),
  );

/** お薬手帳データに含まれる全ての薬品を列挙する。 */
export const collectDrugs = (notebook: MedicationNotebook): Array<RpContext & { drug: Drug }> =>
  collectRps(notebook).flatMap((context) => context.rp.drugs.map((drug) => ({ ...context, drug })));
