import { readFileSync, readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";

/**
 * 仕様書「付録１ お薬手帳イメージと出力データ例」の出力データ例をそのまま収めたフィクスチャ。
 * ファイルはUTF-8・CR+LFで保存している(QRコードへの格納時にShift_JISへ変換される)。
 */
export const readFixture = (name: string): string =>
  readFileSync(fileURLToPath(new URL(`../fixtures/${name}`, import.meta.url)), "utf8");

/** 付録１の出力データ例(例1〜例11)のフィクスチャ名 */
export const EXAMPLE_FIXTURES = readdirSync(fileURLToPath(new URL("../fixtures", import.meta.url)))
  .filter((name) => name.startsWith("example-"))
  .sort();
