/**
 * 使い方の例:
 *   1. お薬手帳データのテキストを構造化データへ変換する
 *   2. 構造化データをQRコードのPNG画像として書き出す
 *   3. 書き出したPNG画像を読み戻して構造化データに戻す
 *
 * 実行: npx tsx examples/round-trip.ts
 */
import { readFileSync, writeFileSync } from "node:fs";
import {
  CODE_TABLES,
  describeCode,
  encodeNotebookToPngs,
  parse,
  readNotebookFromPngs,
  serialize,
} from "../src/index.js";

// 仕様書「付録１ お薬手帳イメージと出力データ例」の例4(複数診療科での出力)
const text = readFileSync(new URL("../fixtures/example-04.txt", import.meta.url), "utf8");

// 1. テキスト -> 構造化データ
const { notebook, issues } = parse(text);
if (issues.length > 0) console.warn(issues);

console.log(`患者: ${notebook.patient?.name} (${describeCode(CODE_TABLES.sex, notebook.patient?.sex ?? "")})`);
for (const dispensing of notebook.dispensings) {
  console.log(`\n調剤等年月日 ${dispensing.date} / ${dispensing.institution?.name}`);
  console.log(`  処方元: ${dispensing.prescribingInstitution?.name ?? "(なし)"}`);

  for (const group of dispensing.doctorGroups) {
    if (group.doctor !== undefined) {
      console.log(`  ${group.doctor.departmentName ?? ""} ${group.doctor.name}`);
    }
    for (const rp of group.rps) {
      const dosageForm = describeCode(CODE_TABLES.dosageForm, rp.usage?.dosageFormCode ?? "");
      console.log(`    RP${rp.rpNumber} [${dosageForm ?? "-"}] ${rp.usage?.name ?? ""}`);
      for (const drug of rp.drugs) console.log(`      ${drug.name} ${drug.dose ?? ""}${drug.unitName ?? ""}`);
    }
  }
}

// 2. 構造化データ -> QRコード
const pngs = await encodeNotebookToPngs(notebook, { scale: 6 });
pngs.forEach((png, index) => writeFileSync(`okusuri-${index + 1}.png`, png));
console.log(`\nQRコードを ${pngs.length} 枚出力しました`);

// 3. QRコード -> 構造化データ
const restored = readNotebookFromPngs(pngs);
console.log("往復一致:", serialize(restored.notebook) === text);
