/**
 * バージョンレコードのバージョン情報(仕様書 3.1)。
 *
 * バージョン情報は `"JAHISTC"` + 半角数字2桁(9桁固定)で、仕様書の改版に伴い数値を1つ上げる。
 * ただしバージョン情報が変わらない改版もあるため、識別子と仕様書バージョンは1対多の関係になる。
 */
export const VERSION_PATTERN = /^JAHISTC(\d{2})$/;

export interface FormatVersionInfo {
  /** バージョン情報 (例: "JAHISTC08") */
  readonly version: string;
  /** このバージョン情報を使用する仕様書バージョン */
  readonly specVersions: readonly string[];
}

/** 仕様書の改訂履歴に基づくバージョン情報の対応表。 */
export const FORMAT_VERSIONS: readonly FormatVersionInfo[] = [
  { version: "JAHISTC01", specVersions: ["1.0"] },
  { version: "JAHISTC02", specVersions: ["1.1"] },
  { version: "JAHISTC03", specVersions: ["2.0"] },
  { version: "JAHISTC04", specVersions: ["2.1"] },
  { version: "JAHISTC05", specVersions: ["2.2"] },
  { version: "JAHISTC06", specVersions: ["2.3"] },
  { version: "JAHISTC07", specVersions: ["2.4"] },
  // Ver.2.6 はバージョン情報を変更していない(改訂内容は薬品コードの備考追加のみ)
  { version: "JAHISTC08", specVersions: ["2.5", "2.6"] },
];

/** このライブラリが対象とする仕様書バージョン */
export const TARGET_SPEC_VERSION = "2.6";

/** このライブラリが既定で出力するバージョン情報 (仕様書 Ver.2.6) */
export const DEFAULT_VERSION = "JAHISTC08";

const BY_VERSION = new Map(FORMAT_VERSIONS.map((info) => [info.version, info]));

/** `JAHISTC` + 2桁数字 の形式かどうかを判定する。 */
export const isVersionRecord = (value: string): boolean => VERSION_PATTERN.test(value);

export const findFormatVersion = (version: string): FormatVersionInfo | undefined => BY_VERSION.get(version);

/** バージョン情報に対応する仕様書バージョンを返す(未知の場合は undefined)。 */
export const specVersionsOf = (version: string): readonly string[] | undefined => BY_VERSION.get(version)?.specVersions;

/** バージョン情報に含まれるバージョン番号を数値で返す。 */
export const versionNumberOf = (version: string): number | undefined => {
  const matched = VERSION_PATTERN.exec(version);
  return matched === null ? undefined : Number(matched[1]);
};
