import { RECORD_KIND, recordSpecOf, type RecordKind } from "./spec/records.js";
import { DEFAULT_VERSION } from "./spec/version.js";
import { FIELD_SEPARATOR, RECORD_SEPARATOR, formatRecord, type FormatRecordOptions } from "./text/records.js";
import type { MedicationNotebook, TextNote } from "./types.js";

export interface SerializeOptions extends FormatRecordOptions {
  /** 出力するバージョン情報(既定: `notebook.version`、無ければ JAHISTC08) */
  readonly version?: string;
  /** レコード終端(既定: CR+LF) */
  readonly newline?: string;
}

type Values = Record<string, string | undefined>;

const emit = (lines: string[], kind: RecordKind, values: Values, options: SerializeOptions): void => {
  const spec = recordSpecOf(kind);
  if (spec === undefined) throw new Error(`レコード定義が見つかりません: ${kind}`);
  lines.push(
    formatRecord(
      spec.recordNo,
      spec.fields.map((field) => values[field.key]),
      options,
    ),
  );
};

const emitNotes = (
  lines: string[],
  kind: RecordKind,
  notes: readonly TextNote[],
  options: SerializeOptions,
  extra: Values = {},
): void => {
  for (const note of notes) {
    emit(lines, kind, { ...extra, text: note.text, recordCreator: note.recordCreator }, options);
  }
};

/**
 * 構造化データを、仕様書「レコード出力順」に従った行の配列へ変換する。
 * 先頭要素はバージョンレコード、分割制御レコード(911)がある場合は末尾になる。
 */
export const toRecordLines = (notebook: MedicationNotebook, options: SerializeOptions = {}): string[] => {
  const lines: string[] = [];

  lines.push(formatRecord(options.version ?? notebook.version ?? DEFAULT_VERSION, [notebook.outputCategory], options));

  if (notebook.patient !== undefined) emit(lines, RECORD_KIND.patient, notebook.patient as Values, options);
  for (const remark of notebook.patientRemarks) emit(lines, RECORD_KIND.patientRemark, remark as Values, options);

  for (const otcDrug of notebook.otcDrugs) {
    emit(lines, RECORD_KIND.otcDrug, otcDrug as unknown as Values, options);
    for (const ingredient of otcDrug.ingredients) {
      emit(
        lines,
        RECORD_KIND.otcDrugIngredient,
        { otcDrugSequence: otcDrug.sequence, ...(ingredient as Values) },
        options,
      );
    }
  }

  for (const memo of notebook.notebookMemos) emit(lines, RECORD_KIND.notebookMemo, memo as Values, options);

  for (const dispensing of notebook.dispensings) {
    emit(lines, RECORD_KIND.dispensingDate, { date: dispensing.date, recordCreator: dispensing.recordCreator }, options);

    if (dispensing.institution !== undefined) {
      emit(lines, RECORD_KIND.dispensingInstitution, dispensing.institution as Values, options);
    }
    if (dispensing.staff !== undefined) {
      emit(lines, RECORD_KIND.dispensingStaff, dispensing.staff as Values, options);
    }
    if (dispensing.prescribingInstitution !== undefined) {
      emit(lines, RECORD_KIND.prescribingInstitution, dispensing.prescribingInstitution as Values, options);
    }

    for (const group of dispensing.doctorGroups) {
      if (group.doctor !== undefined) emit(lines, RECORD_KIND.prescribingDoctor, group.doctor as Values, options);

      for (const rp of group.rps) {
        const rpNumber = rp.rpNumber;
        emitNotes(lines, RECORD_KIND.drugSupplement, rp.orphanDrugNotes, options, { rpNumber });

        for (const drug of rp.drugs) {
          emit(lines, RECORD_KIND.drug, { rpNumber, ...(drug as unknown as Values) }, options);
          emitNotes(lines, RECORD_KIND.drugSupplement, drug.supplements, options, { rpNumber });
          emitNotes(lines, RECORD_KIND.drugCaution, drug.cautions, options, { rpNumber });
        }

        if (rp.usage !== undefined) emit(lines, RECORD_KIND.usage, { rpNumber, ...(rp.usage as Values) }, options);
        emitNotes(lines, RECORD_KIND.usageSupplement, rp.usageSupplements, options, { rpNumber });
        emitNotes(lines, RECORD_KIND.prescriptionCaution, rp.prescriptionCautions, options, { rpNumber });
      }
    }

    emitNotes(lines, RECORD_KIND.caution, dispensing.cautions, options);
    for (const info of dispensing.providedInfos) {
      emit(
        lines,
        RECORD_KIND.providedInfo,
        { text: info.text, infoType: info.infoType, recordCreator: info.recordCreator },
        options,
      );
    }
    emitNotes(lines, RECORD_KIND.remainingDrugCheck, dispensing.remainingDrugChecks, options);
    emitNotes(lines, RECORD_KIND.remark, dispensing.remarks, options);
    for (const entry of dispensing.patientEntries) emit(lines, RECORD_KIND.patientEntry, entry as Values, options);
  }

  for (const pharmacist of notebook.familyPharmacists) {
    emit(lines, RECORD_KIND.familyPharmacist, pharmacist as Values, options);
  }

  for (const unknown of notebook.unknownRecords) {
    lines.push([unknown.recordNo, ...unknown.fields].join(FIELD_SEPARATOR));
  }

  if (notebook.split !== undefined) emit(lines, RECORD_KIND.splitControl, notebook.split as Values, options);

  return lines;
};

/** 構造化データを JAHIS電子版お薬手帳データのテキストへ変換する。 */
export const serialize = (notebook: MedicationNotebook, options: SerializeOptions = {}): string =>
  toRecordLines(notebook, options).join(options.newline ?? RECORD_SEPARATOR);
