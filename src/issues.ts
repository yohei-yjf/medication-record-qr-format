/** 解析・検証で検出した問題の深刻度 */
export type IssueLevel = "error" | "warning";

export const ISSUE_CODE = {
  emptyInput: "empty-input",
  missingVersionRecord: "missing-version-record",
  unknownVersion: "unknown-version",
  unknownRecord: "unknown-record",
  duplicateRecord: "duplicate-record",
  missingRequiredField: "missing-required-field",
  tooManyFields: "too-many-fields",
  fieldTooLong: "field-too-long",
  invalidCode: "invalid-code",
  invalidDate: "invalid-date",
  invalidType: "invalid-type",
  orphanRecord: "orphan-record",
  missingUsage: "missing-usage",
  splitMismatch: "split-mismatch",
} as const;

export type IssueCode = (typeof ISSUE_CODE)[keyof typeof ISSUE_CODE];

export interface Issue {
  readonly level: IssueLevel;
  readonly code: IssueCode;
  readonly message: string;
  /** 1始まりの行番号 */
  readonly line?: number;
  readonly recordNo?: string;
  /** レコード内の項目位置(レコード番号を 0 とした連番) */
  readonly fieldIndex?: number;
  readonly fieldKey?: string;
}

export class IssueCollector {
  private readonly issues: Issue[] = [];

  add(issue: Issue): void {
    this.issues.push(issue);
  }

  error(code: IssueCode, message: string, context: Omit<Issue, "level" | "code" | "message"> = {}): void {
    this.add({ level: "error", code, message, ...context });
  }

  warn(code: IssueCode, message: string, context: Omit<Issue, "level" | "code" | "message"> = {}): void {
    this.add({ level: "warning", code, message, ...context });
  }

  get all(): Issue[] {
    return this.issues;
  }

  get hasError(): boolean {
    return this.issues.some((issue) => issue.level === "error");
  }
}

/** 構造化データをテキストへ変換する際のエラー */
export class SerializeError extends Error {
  constructor(
    message: string,
    readonly context?: { recordNo?: string; fieldKey?: string; value?: string },
  ) {
    super(message);
    this.name = "SerializeError";
  }
}

/** QRコードの読み取り・生成に失敗した際のエラー */
export class QrCodeError extends Error {
  constructor(message: string, options?: unknown) {
    super(message);
    this.name = "QrCodeError";
    if (options !== undefined) this.cause = options;
  }
}
