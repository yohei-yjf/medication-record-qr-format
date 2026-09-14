# medication-record-qr-format

おくすり手帳(電子版お薬手帳)のQRコードを読み取って構造化データに変換し、
構造化データからQRコードを生成する TypeScript ライブラリです。

**JAHIS電子版お薬手帳データフォーマット仕様書 Ver.2.6**(JAHIS技術文書 24-104、バージョン情報 `JAHISTC08`)に準拠しています。

## 特徴

- **QRコード → 構造化データ**: PNG画像・RGBA画素データ・テキストのいずれからでも読み取れます
- **構造化データ → QRコード**: PNG / SVG / data URL を生成できます
- **Shift_JIS 対応**: 仕様どおり Shift_JIS でQRコードに格納します(UTF-8 も選択可)
- **分割制御レコード(911)対応**: 1つのQRコードに収まらないデータは自動で分割し、読み取り時に連番順で自動結合します
- **仕様定義が単一の情報源**: 仕様書 3.2.8「各種レコードレイアウト」をそのまま表として持ち、解析・出力・検証をすべてそこから駆動します
- **提供方向を踏まえた検証**: 「医療機関等⇒患者等」と「患者等⇒医療機関等」で異なる必須項目を、出力区分から判定して検証します
- **止まらない解析**: 仕様から外れたデータも可能な限り構造化し、問題は `issues` として報告します
- 依存は純粋 JavaScript のみ(ネイティブモジュール不要)

テストは仕様書「付録１ お薬手帳イメージと出力データ例」の**出力データ例(例1〜例11)をそのまま**
フィクスチャとして使用しています。詳細は [SPEC-NOTES.md](./SPEC-NOTES.md) を参照してください。

## インストール

```bash
npm install medication-record-qr-format
```

Node.js 20 以上が必要です。

## 使い方

### QRコードを読み込んで構造化データに変換する

```ts
import { readFileSync } from "node:fs";
import { readNotebookFromPngs } from "medication-record-qr-format";

const result = readNotebookFromPngs([readFileSync("okusuri.png")]);

if (!result.ok) {
  console.error(result.issues);
}

const notebook = result.notebook;
console.log(notebook.patient?.name);                    // 鈴木 太郎
console.log(notebook.dispensings[0].date);              // R020410
console.log(notebook.dispensings[0].institution?.name); // 株式会社 工業会薬局 駅前店

for (const dispensing of notebook.dispensings) {
  for (const group of dispensing.doctorGroups) {
    for (const rp of group.rps) {
      console.log(`RP${rp.rpNumber} ${rp.usage?.name} ×${rp.usage?.dispensingQuantity}${rp.usage?.dispensingUnit}`);
      for (const drug of rp.drugs) {
        console.log(`  ${drug.name} ${drug.dose}${drug.unitName}`);
      }
    }
  }
}
```

入れ子をたどらずに一覧したい場合は `collectRps` / `collectDrugs` が使えます。

```ts
import { collectDrugs } from "medication-record-qr-format";

for (const { dispensing, doctorGroup, rp, drug } of collectDrugs(notebook)) {
  console.log(dispensing.date, doctorGroup.doctor?.name, rp.rpNumber, drug.name);
}
```

分割された複数のQRコードは、読み取った順番に関係なくまとめて渡せます。

```ts
const result = readNotebookFromPngs([readFileSync("2.png"), readFileSync("1.png")]);
```

### ブラウザ(カメラ・canvas)から読み取る

```ts
import { readNotebookFromImageData } from "medication-record-qr-format";

const context = canvas.getContext("2d")!;
context.drawImage(video, 0, 0, canvas.width, canvas.height);

const result = readNotebookFromImageData([context.getImageData(0, 0, canvas.width, canvas.height)]);
```

### すでにデコード済みのテキストを解析する

```ts
import { parse } from "medication-record-qr-format";

const result = parse("JAHISTC08,1\r\n1,鈴木 太郎,1,S330303,,,,,,,\r\n...");
```

### 構造化データをQRコードに変換する

```ts
import { writeFileSync } from "node:fs";
import { encodeNotebookToPngs, serialize } from "medication-record-qr-format";

// お薬手帳データのテキストとして出力する
const text = serialize(notebook);

// QRコードのPNG画像として出力する(上限を超える場合は自動で複数枚に分割)
const pngs = await encodeNotebookToPngs(notebook, { errorCorrectionLevel: "M", scale: 6 });
pngs.forEach((png, index) => writeFileSync(`okusuri-${index + 1}.png`, png));
```

SVG や data URL も生成できます。

```ts
import { encodeNotebookToDataUrls, encodeNotebookToSvgs } from "medication-record-qr-format";

const svgs = await encodeNotebookToSvgs(notebook);
const dataUrls = await encodeNotebookToDataUrls(notebook);
```

## 構造化データの形

仕様書 3.2.5「情報グループとレコード情報」の入れ子構造を、そのままオブジェクトの入れ子で表現します。

```
MedicationNotebook                   バージョンレコード(JAHISTC**)
├─ patient                           患者情報(1)
├─ patientRemarks[]                  患者特記(2)
├─ otcDrugs[]                        要指導医薬品・一般用医薬品服用(3)
│   └─ ingredients[]                 要指導医薬品・一般用医薬品成分(31)
├─ notebookMemos[]                   手帳メモ(4)
├─ dispensings[]                     調剤等年月日(5)ごとの調剤情報グループ
│   ├─ institution                   調剤－医療機関等(11)
│   ├─ staff                         調剤－医師・薬剤師(15)
│   ├─ prescribingInstitution        処方－医療機関(51)
│   ├─ doctorGroups[]                処方－医師(55)ごとのRPのまとまり
│   │   ├─ doctor                    処方－医師(55)
│   │   └─ rps[]                     RP(処方指示)単位
│   │       ├─ drugs[]               薬品(201)
│   │       │   ├─ supplements[]     薬品補足(281)
│   │       │   └─ cautions[]        薬品服用注意(291)
│   │       ├─ usage                 用法(301)
│   │       ├─ usageSupplements[]    用法補足(311)
│   │       └─ prescriptionCautions[] 処方服用注意(391)
│   ├─ cautions[]                    服用注意(401)
│   ├─ providedInfos[]               医療機関等提供情報(411)
│   ├─ remainingDrugChecks[]         残薬確認(421)
│   ├─ remarks[]                     備考(501)
│   └─ patientEntries[]              患者等記入(601)
├─ familyPharmacists[]               かかりつけ薬剤師(701)
├─ split                             分割制御(911)
└─ unknownRecords[]                  未知のレコード(前方互換のため保持)
```

項目値はすべて仕様書どおりの**文字列のまま**保持します。
年月日は西暦8桁(`20200410`)と和暦7桁(`R020410`)のどちらも記録されたまま保持し、
数値変換や和暦変換は行いません(利用側の要件に委ねる方針です)。

コード値の意味は `CODE_TABLES` から引けます。

```ts
import { CODE_TABLES, describeCode } from "medication-record-qr-format";

describeCode(CODE_TABLES.sex, "1");              // "男"
describeCode(CODE_TABLES.prefecture, "13");      // "東京"
describeCode(CODE_TABLES.dosageForm, "3");       // "屯服"
describeCode(CODE_TABLES.drugCodeType, "2");     // "レセプト電算コード"
```

## 解析結果と検証

`parse` は解析できた範囲を常に返し、問題は `issues` として報告します。

```ts
const result = parse(text);

result.ok;       // エラーが無ければ true
result.notebook; // 構造化データ(常に取得できる)
result.issues;   // [{ level, code, message, line, recordNo, fieldIndex, fieldKey }, ...]
result.records;  // 解析前のレコード(行番号・項目の生値)
```

| 深刻度 | 扱い | 例 |
| --- | --- | --- |
| `error` | `ok` が false になる | バージョンレコードが無い / 必須項目が無い / コード種別に対応するコードが無い |
| `warning` | 解析は継続する | 未定義のコード値 / バイト数超過 / 年月日やデータ型の不正 / 未知のレコード / 同一№レコードの重複 / 用法レコードの欠落 |

必須項目の判定は、バージョンレコードの出力区分(1:医療機関等⇒患者等 / 2:患者等⇒医療機関等)に従います。

```ts
parse(text, { strict: true });              // 警告が1件でもあれば ok === false
parse(text, { validate: false });           // 項目検証を行わない
parse(text, { checkCodeTables: false });    // コード表の検証のみ行わない
parse(text, { direction: "toPatient" });    // 出力区分が読み取れない場合に仮定する提供方向
parseOrThrow(text);                         // エラー時に例外を送出する
```

## 分割の制御

仕様書 3.2.9(3)「データを分割した場合の出力方法」に従い、各シンボルの先頭にバージョンレコード、
末尾に分割制御レコード(911)を出力します。

```ts
import { mergeSplitParts, splitForQr, toQrTexts } from "medication-record-qr-format";

// 1シンボルに収まるよう分割する
const parts = splitForQr(text, { maxBytesPerSymbol: 1800, dataId: "12345678901234" });

// 読み取ったテキストを結合する(データ連番順に並べ替える)
const merged = mergeSplitParts(parts);
merged.text;
merged.issues;  // 重複・欠落・データ固有IDの不一致を報告

// 構造化データから、QRコードに入れるテキストの配列を得る
const texts = toQrTexts(notebook, { maxBytesPerSymbol: 1800 });
```

`encodeNotebookTo*` は既定で分割を行います。分割したくない場合は `split: false` を指定してください。
QRコードの容量を節約したい場合は `omitTrailingEmptyFields: true` で末尾の空項目を省略できます。

## 主なAPI

| API | 用途 |
| --- | --- |
| `parse(text, options)` / `parseOrThrow` | テキスト → 構造化データ |
| `serialize(notebook, options)` / `toRecordLines` | 構造化データ → テキスト |
| `decodeQrFromPng` / `decodeQrFromImageData` | QR画像 → テキスト |
| `readNotebookFromPngs` / `readNotebookFromImageData` / `readNotebookFromTexts` | QR画像・テキスト → 構造化データ(分割の結合を含む) |
| `encodeTextToPng` / `encodeTextToSvg` / `encodeTextToDataUrl` | テキスト → QRコード |
| `encodeNotebookToPngs` / `encodeNotebookToSvgs` / `encodeNotebookToDataUrls` | 構造化データ → QRコード(分割対応) |
| `splitForQr` / `mergeSplitParts` | 分割制御レコードを使った分割・結合 |
| `collectRps` / `collectDrugs` | 入れ子をたどらずにRP・薬品を列挙する |
| `RECORD_SPECS` / `CODE_TABLES` / `FORMAT_VERSIONS` | 仕様定義そのもの(項目名・型・バイト数・コード表) |

## 設計方針

- **仕様定義を単一の情報源にする**: `src/spec/records.ts` のレコード定義表(項目名・型・バイト数・必須区分)から、
  解析・出力・検証をすべて駆動します。仕様書が改版された場合も定義表を直せば全体に反映されます。
- **往復で壊さない**: 付録1の出力データ例は、解析して再出力すると**1バイトも違わず元に戻る**ことをテストしています。
  未知のレコードもそのまま保持して再出力します。
- **現場のデータで止まらない**: 仕様から外れた値も可能な限り構造化し、問題は `issues` で報告します。
- **解釈を押し付けない**: 値は文字列のまま保持し、コード値の意味付けは利用側が選べるようにしています。

## 開発

```bash
npm install
npm test          # vitest
npm run typecheck # tsc --noEmit
npm run build     # tsup (ESM + CJS + d.ts)
npm run check     # 上記すべて
```

テストでは次を検証しています。

- レコード定義表が仕様書のレイアウト(項目名・型・バイト数)と一致していること
- 別表1〜4のコード表の内容
- 付録1の出力データ例(例1〜例11)がエラー・警告なしで解析できること
- 出力データ例の構造(調剤情報グループ、処方－医師レコードによるRPのまとまり、補足レコードの紐づけ)
- 異常系(必須項目の欠落・未定義のコード値・未知のレコード・順序の逸脱・重複)
- テキストの往復(解析 → 出力で元のテキストと完全一致)
- QRコードの往復(構造化データ → PNG画像 → 実際にQRコードを読み取り → 構造化データ)
- 仕様書 3.2.9(3) の分割出力例の結合、および任意サイズでの分割・結合

## ライセンス

MIT
