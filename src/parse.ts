import { ISSUE_CODE, IssueCollector, type Issue } from "./issues.js";
import { RECORD_NO, directionOf, findRecordSpec, type Direction, type RecordSpec } from "./spec/records.js";
import { DEFAULT_VERSION, findFormatVersion, isVersionRecord, specVersionsOf } from "./spec/version.js";
import { fieldAt, parseRawRecords } from "./text/records.js";
import {
  createEmptyDispensing,
  createEmptyNotebook,
  createEmptyRp,
  type Dispensing,
  type DoctorGroup,
  type Drug,
  type MedicationNotebook,
  type OtcDrug,
  type RawRecord,
  type Rp,
  type TextNote,
} from "./types.js";
import { validateRecord, validateUsageName, type ValidationOptions } from "./validate.js";

export interface ParseOptions extends ValidationOptions {
  /** 警告もエラーとして扱い `ok` を false にする(既定: false)。構造化データ自体は取得できる。 */
  readonly strict?: boolean;
  /** 項目・コード表の検証を行う(既定: true) */
  readonly validate?: boolean;
  /** 解析前のレコードを結果に含める(既定: true) */
  readonly keepRawRecords?: boolean;
  /**
   * 出力区分が未設定の場合に仮定する情報提供方向。
   * 必須項目の判定に使用する。
   */
  readonly direction?: Direction;
}

export interface ParseResult {
  /** エラーが無ければ true (strict 指定時は警告が1件でもあれば false) */
  readonly ok: boolean;
  /** 構造化データ。解析できた範囲を常に返す。 */
  readonly notebook: MedicationNotebook;
  readonly issues: readonly Issue[];
  readonly records: readonly RawRecord[];
}

type Values = Record<string, string | undefined>;

/** レコードレイアウトの定義に従って項目値を読み出す。 */
const readFields = (record: RawRecord, spec: RecordSpec): Values => {
  const values: Values = {};
  for (const field of spec.fields) {
    const value = fieldAt(record, field.index);
    if (value !== undefined) values[field.key] = value;
  }
  return values;
};

const toTextNote = (values: Values): TextNote => ({ text: values["text"], recordCreator: values["recordCreator"] });

class NotebookBuilder {
  readonly notebook: MedicationNotebook;
  private dispensing: Dispensing | undefined;
  private doctorGroup: DoctorGroup | undefined;
  private rp: Rp | undefined;
  private drug: Drug | undefined;
  private lastOtcDrug: OtcDrug | undefined;

  constructor(
    version: string,
    private readonly issues: IssueCollector,
    private readonly direction: Direction | undefined,
  ) {
    this.notebook = createEmptyNotebook(version);
    const specVersions = specVersionsOf(version);
    if (specVersions !== undefined) this.notebook.specVersions = specVersions;
  }

  private duplicate(record: RawRecord, spec: RecordSpec): void {
    this.issues.warn(
      ISSUE_CODE.duplicateRecord,
      `${spec.label}(${spec.recordNo}) は「${spec.repetition}」ですが複数回出現しました。最初のレコードを採用します。`,
      { line: record.line, recordNo: spec.recordNo },
    );
  }

  /** 調剤等年月日レコード(5)より前に調剤情報グループのレコードが現れた場合の救済 */
  private ensureDispensing(record: RawRecord, spec: RecordSpec): Dispensing {
    if (this.dispensing === undefined) {
      this.issues.warn(
        ISSUE_CODE.orphanRecord,
        `${spec.label}(${spec.recordNo}) が調剤等年月日レコード(5)より前に出現したため、暗黙の調剤情報として扱います。`,
        { line: record.line, recordNo: spec.recordNo },
      );
      this.dispensing = createEmptyDispensing();
      this.notebook.dispensings.push(this.dispensing);
    }
    return this.dispensing;
  }

  /** 処方－医師レコード(55)が出力されない場合は、医師を持たない1グループにまとめる */
  private ensureDoctorGroup(record: RawRecord, spec: RecordSpec): DoctorGroup {
    const dispensing = this.ensureDispensing(record, spec);
    const last = dispensing.doctorGroups[dispensing.doctorGroups.length - 1];
    if (last !== undefined) return last;
    const group: DoctorGroup = { rps: [] };
    dispensing.doctorGroups.push(group);
    return group;
  }

  private rpOf(record: RawRecord, spec: RecordSpec, rpNumber: string | undefined): Rp {
    const group = this.ensureDoctorGroup(record, spec);
    const key = rpNumber ?? "";
    const dispensing = this.dispensing!;

    const existing = dispensing.doctorGroups.flatMap((item) => item.rps).find((item) => item.rpNumber === key);
    if (existing !== undefined) {
      if (this.rp !== existing) {
        this.rp = existing;
        this.drug = undefined;
      }
      return existing;
    }

    const rp = createEmptyRp(key);
    group.rps.push(rp);
    this.rp = rp;
    this.drug = undefined;
    return rp;
  }

  startDispensing(values: Values): void {
    const dispensing = createEmptyDispensing();
    dispensing.date = values["date"];
    dispensing.recordCreator = values["recordCreator"];
    this.notebook.dispensings.push(dispensing);
    this.dispensing = dispensing;
    this.doctorGroup = undefined;
    this.rp = undefined;
    this.drug = undefined;
  }

  setDispensingInstitution(record: RawRecord, spec: RecordSpec, values: Values): void {
    const dispensing = this.ensureDispensing(record, spec);
    if (dispensing.institution !== undefined) return this.duplicate(record, spec);
    dispensing.institution = {
      name: values["name"],
      prefectureCode: values["prefectureCode"],
      scoreTableCode: values["scoreTableCode"],
      institutionCode: values["institutionCode"],
      postalCode: values["postalCode"],
      address: values["address"],
      phone: values["phone"],
      recordCreator: values["recordCreator"],
    };
  }

  setDispensingStaff(record: RawRecord, spec: RecordSpec, values: Values): void {
    const dispensing = this.ensureDispensing(record, spec);
    if (dispensing.staff !== undefined) return this.duplicate(record, spec);
    dispensing.staff = {
      name: values["name"],
      contact: values["contact"],
      recordCreator: values["recordCreator"],
    };
  }

  setPrescribingInstitution(record: RawRecord, spec: RecordSpec, values: Values): void {
    const dispensing = this.ensureDispensing(record, spec);
    if (dispensing.prescribingInstitution !== undefined) return this.duplicate(record, spec);
    dispensing.prescribingInstitution = {
      name: values["name"],
      prefectureCode: values["prefectureCode"],
      scoreTableCode: values["scoreTableCode"],
      institutionCode: values["institutionCode"],
      recordCreator: values["recordCreator"],
    };
  }

  startDoctorGroup(record: RawRecord, spec: RecordSpec, values: Values): void {
    const dispensing = this.ensureDispensing(record, spec);
    const group: DoctorGroup = {
      doctor: {
        name: values["name"],
        departmentName: values["departmentName"],
        recordCreator: values["recordCreator"],
      },
      rps: [],
    };
    dispensing.doctorGroups.push(group);
    this.doctorGroup = group;
    this.rp = undefined;
    this.drug = undefined;
  }

  addDrug(record: RawRecord, spec: RecordSpec, values: Values): void {
    const rp = this.rpOf(record, spec, values["rpNumber"]);
    const drug: Drug = {
      name: values["name"],
      dose: values["dose"],
      unitName: values["unitName"],
      codeType: values["codeType"],
      code: values["code"],
      recordCreator: values["recordCreator"],
      generalName: values["generalName"],
      generalNameCodeType: values["generalNameCodeType"],
      generalNameCode: values["generalNameCode"],
      supplements: [],
      cautions: [],
    };
    rp.drugs.push(drug);
    this.drug = drug;
  }

  addDrugNote(record: RawRecord, spec: RecordSpec, values: Values, target: "supplements" | "cautions"): void {
    const rp = this.rpOf(record, spec, values["rpNumber"]);
    const note = toTextNote(values);
    if (this.drug === undefined || !rp.drugs.includes(this.drug)) {
      this.issues.warn(
        ISSUE_CODE.orphanRecord,
        `${spec.label}(${spec.recordNo}) に対応する薬品レコード(201)が直前にありません。RP単位の情報として保持します。`,
        { line: record.line, recordNo: spec.recordNo },
      );
      rp.orphanDrugNotes.push(note);
      return;
    }
    this.drug[target].push(note);
  }

  setUsage(record: RawRecord, spec: RecordSpec, values: Values): void {
    const rp = this.rpOf(record, spec, values["rpNumber"]);
    if (rp.usage !== undefined) {
      this.issues.warn(ISSUE_CODE.duplicateRecord, `RP${rp.rpNumber} に用法レコード(301)が複数存在します。`, {
        line: record.line,
        recordNo: spec.recordNo,
      });
    }
    rp.usage = {
      name: values["name"],
      dispensingQuantity: values["dispensingQuantity"],
      dispensingUnit: values["dispensingUnit"],
      dosageFormCode: values["dosageFormCode"],
      codeType: values["codeType"],
      code: values["code"],
      recordCreator: values["recordCreator"],
    };

    validateUsageName(this.issues, {
      line: record.line,
      direction: this.direction,
      dispensedByPharmacy: this.dispensing?.prescribingInstitution !== undefined,
      dosageFormCode: values["dosageFormCode"],
      name: values["name"],
    });
  }

  addRpNote(record: RawRecord, spec: RecordSpec, values: Values, target: "usageSupplements" | "prescriptionCautions"): void {
    this.rpOf(record, spec, values["rpNumber"])[target].push(toTextNote(values));
  }

  addOtcDrug(values: Values): void {
    const otcDrug: OtcDrug = {
      name: values["name"],
      startDate: values["startDate"],
      endDate: values["endDate"],
      recordCreator: values["recordCreator"],
      sequence: values["sequence"],
      janCode: values["janCode"],
      ingredients: [],
    };
    this.notebook.otcDrugs.push(otcDrug);
    this.lastOtcDrug = otcDrug;
  }

  addOtcIngredient(record: RawRecord, spec: RecordSpec, values: Values): void {
    const sequence = values["otcDrugSequence"];
    const matched = this.notebook.otcDrugs.find((drug) => sequence !== undefined && drug.sequence === sequence);
    const target = matched ?? this.lastOtcDrug;

    if (target === undefined) {
      this.issues.warn(
        ISSUE_CODE.orphanRecord,
        `${spec.label}(${spec.recordNo}) に対応する要指導医薬品・一般用医薬品服用レコード(3)がありません。`,
        { line: record.line, recordNo: spec.recordNo },
      );
      return;
    }
    if (matched === undefined) {
      this.issues.warn(
        ISSUE_CODE.orphanRecord,
        `通番 ${sequence ?? "(未設定)"} に一致する要指導医薬品・一般用医薬品服用レコード(3)が無いため、直前のレコードに紐づけました。`,
        { line: record.line, recordNo: spec.recordNo },
      );
    }

    target.ingredients.push({
      name: values["name"],
      codeType: values["codeType"],
      code: values["code"],
      recordCreator: values["recordCreator"],
    });
  }

  addDispensingNote(
    record: RawRecord,
    spec: RecordSpec,
    values: Values,
    target: "cautions" | "remainingDrugChecks" | "remarks",
  ): void {
    this.ensureDispensing(record, spec)[target].push(toTextNote(values));
  }

  addProvidedInfo(record: RawRecord, spec: RecordSpec, values: Values): void {
    this.ensureDispensing(record, spec).providedInfos.push({
      text: values["text"],
      infoType: values["infoType"],
      recordCreator: values["recordCreator"],
    });
  }

  addPatientEntry(record: RawRecord, spec: RecordSpec, values: Values): void {
    this.ensureDispensing(record, spec).patientEntries.push({
      text: values["text"],
      inputDate: values["inputDate"],
    });
  }

  setPatient(record: RawRecord, spec: RecordSpec, values: Values): void {
    if (this.notebook.patient !== undefined) return this.duplicate(record, spec);
    this.notebook.patient = {
      name: values["name"],
      sex: values["sex"],
      birthDate: values["birthDate"],
      postalCode: values["postalCode"],
      address: values["address"],
      phone: values["phone"],
      emergencyContact: values["emergencyContact"],
      bloodType: values["bloodType"],
      weight: values["weight"],
      kanaName: values["kanaName"],
    };
  }

  setSplit(record: RawRecord, spec: RecordSpec, values: Values): void {
    if (this.notebook.split !== undefined) return this.duplicate(record, spec);
    this.notebook.split = {
      dataId: values["dataId"],
      totalCount: values["totalCount"],
      sequence: values["sequence"],
    };
  }
}

const handleRecord = (record: RawRecord, spec: RecordSpec, builder: NotebookBuilder): void => {
  const values = readFields(record, spec);
  const notebook = builder.notebook;

  switch (spec.recordNo) {
    case RECORD_NO.patient:
      return builder.setPatient(record, spec, values);
    case RECORD_NO.patientRemark:
      notebook.patientRemarks.push({
        remarkType: values["remarkType"],
        text: values["text"],
        recordCreator: values["recordCreator"],
      });
      return;
    case RECORD_NO.otcDrug:
      return builder.addOtcDrug(values);
    case RECORD_NO.otcDrugIngredient:
      return builder.addOtcIngredient(record, spec, values);
    case RECORD_NO.notebookMemo:
      notebook.notebookMemos.push({
        text: values["text"],
        inputDate: values["inputDate"],
        recordCreator: values["recordCreator"],
      });
      return;
    case RECORD_NO.dispensingDate:
      return builder.startDispensing(values);
    case RECORD_NO.dispensingInstitution:
      return builder.setDispensingInstitution(record, spec, values);
    case RECORD_NO.dispensingStaff:
      return builder.setDispensingStaff(record, spec, values);
    case RECORD_NO.prescribingInstitution:
      return builder.setPrescribingInstitution(record, spec, values);
    case RECORD_NO.prescribingDoctor:
      return builder.startDoctorGroup(record, spec, values);
    case RECORD_NO.drug:
      return builder.addDrug(record, spec, values);
    case RECORD_NO.drugSupplement:
      return builder.addDrugNote(record, spec, values, "supplements");
    case RECORD_NO.drugCaution:
      return builder.addDrugNote(record, spec, values, "cautions");
    case RECORD_NO.usage:
      return builder.setUsage(record, spec, values);
    case RECORD_NO.usageSupplement:
      return builder.addRpNote(record, spec, values, "usageSupplements");
    case RECORD_NO.prescriptionCaution:
      return builder.addRpNote(record, spec, values, "prescriptionCautions");
    case RECORD_NO.caution:
      return builder.addDispensingNote(record, spec, values, "cautions");
    case RECORD_NO.providedInfo:
      return builder.addProvidedInfo(record, spec, values);
    case RECORD_NO.remainingDrugCheck:
      return builder.addDispensingNote(record, spec, values, "remainingDrugChecks");
    case RECORD_NO.remark:
      return builder.addDispensingNote(record, spec, values, "remarks");
    case RECORD_NO.patientEntry:
      return builder.addPatientEntry(record, spec, values);
    case RECORD_NO.familyPharmacist:
      notebook.familyPharmacists.push({
        name: values["name"],
        pharmacyName: values["pharmacyName"],
        contact: values["contact"],
        startDate: values["startDate"],
        endDate: values["endDate"],
        recordCreator: values["recordCreator"],
      });
      return;
    case RECORD_NO.splitControl:
      return builder.setSplit(record, spec, values);
    default:
      return;
  }
};

/**
 * JAHIS電子版お薬手帳データのテキストを構造化データへ変換する。
 *
 * @param text QRコードから読み取ったテキスト。複数シンボルに分割されている場合は
 *             `mergeSplitParts` で結合してから渡す。
 */
export const parse = (text: string, options: ParseOptions = {}): ParseResult => {
  const issues = new IssueCollector();
  const records = parseRawRecords(text);

  if (records.length === 0) {
    issues.error(ISSUE_CODE.emptyInput, "入力にレコードが1件も含まれていません。");
    return { ok: false, notebook: createEmptyNotebook(DEFAULT_VERSION), issues: issues.all, records: [] };
  }

  const header = records[0]!;
  const hasVersionRecord = isVersionRecord(header.recordNo);
  const version = hasVersionRecord ? header.recordNo : DEFAULT_VERSION;
  const body = hasVersionRecord ? records.slice(1) : records;

  if (!hasVersionRecord) {
    issues.error(
      ISSUE_CODE.missingVersionRecord,
      `先頭レコードがバージョンレコード(JAHISTC**)ではありません: ${header.recordNo}`,
      { line: header.line, recordNo: header.recordNo },
    );
  } else if (findFormatVersion(version) === undefined) {
    issues.warn(ISSUE_CODE.unknownVersion, `未知のバージョン情報です: ${version}。解析は継続します。`, {
      line: header.line,
      recordNo: version,
    });
  }

  const outputCategory = hasVersionRecord ? fieldAt(header, 1) : undefined;
  if (hasVersionRecord && outputCategory === undefined) {
    issues.error(ISSUE_CODE.missingRequiredField, "バージョンレコードの必須項目「出力区分」が未設定です。", {
      line: header.line,
      recordNo: version,
      fieldIndex: 1,
      fieldKey: "outputCategory",
    });
  } else if (outputCategory !== undefined && outputCategory !== "1" && outputCategory !== "2") {
    issues.warn(ISSUE_CODE.invalidCode, `バージョンレコードの「出力区分」が不正です: ${outputCategory}`, {
      line: header.line,
      recordNo: version,
      fieldIndex: 1,
      fieldKey: "outputCategory",
    });
  }

  const direction = directionOf(outputCategory) ?? options.direction;
  const builder = new NotebookBuilder(version, issues, direction);
  if (outputCategory !== undefined) builder.notebook.outputCategory = outputCategory;

  for (const record of body) {
    const spec = findRecordSpec(record.recordNo);
    if (spec === undefined) {
      issues.warn(ISSUE_CODE.unknownRecord, `未知のレコード番号です: ${record.recordNo}`, {
        line: record.line,
        recordNo: record.recordNo,
      });
      builder.notebook.unknownRecords.push({
        recordNo: record.recordNo,
        fields: record.fields.slice(1),
        line: record.line,
      });
      continue;
    }

    if (options.validate !== false) validateRecord(record, spec, issues, direction, options);
    handleRecord(record, spec, builder);
  }

  for (const dispensing of builder.notebook.dispensings) {
    for (const group of dispensing.doctorGroups) {
      for (const rp of group.rps) {
        if (rp.usage === undefined) {
          issues.warn(ISSUE_CODE.missingUsage, `RP${rp.rpNumber} に用法レコード(301)がありません。`);
        }
      }
    }
  }

  const allIssues = issues.all;
  return {
    ok: options.strict === true ? allIssues.length === 0 : !issues.hasError,
    notebook: builder.notebook,
    issues: allIssues,
    records: options.keepRawRecords === false ? [] : records,
  };
};

/** `parse` と同じだが、エラーがある場合に例外を送出する。 */
export const parseOrThrow = (text: string, options: ParseOptions = {}): MedicationNotebook => {
  const result = parse(text, options);
  if (!result.ok) {
    const detail = result.issues
      .filter((issue) => issue.level === "error" || options.strict === true)
      .map((issue) => `- [${issue.level}] ${issue.code}${issue.line ? ` (${issue.line}行目)` : ""}: ${issue.message}`)
      .join("\n");
    throw new Error(`お薬手帳データの解析に失敗しました:\n${detail}`);
  }
  return result.notebook;
};
