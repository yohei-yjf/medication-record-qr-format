# medication-record-qr-format (Python)

おくすり手帳(電子版お薬手帳)のQRコードを読み取って構造化データに変換し、
構造化データからQRコードを生成する Python ライブラリです。

**JAHIS電子版お薬手帳データフォーマット仕様書 Ver.2.6**(JAHIS技術文書 24-104、バージョン情報 `JAHISTC08`)に準拠しています。

同じリポジトリの [TypeScript実装](../README.md) と同じ仕様定義・同じテストデータを共有しており、
解析結果・出力テキストは両者で一致します。

## 特徴

- **QRコード → 構造化データ**: PNG画像・PIL Image・テキストのいずれからでも読み取れます
- **構造化データ → QRコード**: PNG / SVG / data URI を生成できます
- **Shift_JIS(cp932)対応**: 仕様どおり8ビットバイトモードで Shift_JIS のバイト列を格納します
- **分割制御レコード(911)対応**: 1つのQRコードに収まらないデータは自動で分割し、読み取り時に連番順で自動結合します
- **仕様定義が単一の情報源**: 仕様書 3.2.8「各種レコードレイアウト」をそのまま定義表として持ち、解析・出力・検証をすべてそこから駆動します
- **提供方向を踏まえた検証**: 「医療機関等⇒患者等」と「患者等⇒医療機関等」で異なる必須項目を、出力区分から判定して検証します
- **止まらない解析**: 仕様から外れたデータも可能な限り構造化し、問題は `issues` として報告します
- 型ヒント同梱(`py.typed`)、解析・出力だけなら**依存ライブラリなし**

## インストール

```bash
# 解析・出力のみ(依存なし)
pip install medication-record-qr-format

# QRコードの生成も行う
pip install "medication-record-qr-format[encode]"

# QRコードの読み取りも行う
pip install "medication-record-qr-format[decode]"

# 両方
pip install "medication-record-qr-format[qr]"
```

Python 3.10 以上が必要です。QRコードの生成には [segno](https://pypi.org/project/segno/)、
読み取りには [zxing-cpp](https://pypi.org/project/zxing-cpp/) と [Pillow](https://pypi.org/project/pillow/) を使用します。

## 使い方

### QRコードを読み込んで構造化データに変換する

```python
from pathlib import Path

from medication_record_qr import read_notebook_from_pngs

result = read_notebook_from_pngs([Path("okusuri.png").read_bytes()])

if not result.ok:
    for issue in result.issues:
        print(issue.level, issue.code, issue.message)

notebook = result.notebook
print(notebook.patient.name)  # 鈴木 太郎
print(notebook.dispensings[0].date)  # R020410
print(notebook.dispensings[0].institution.name)  # 株式会社 工業会薬局 駅前店

for dispensing in notebook.dispensings:
    for group in dispensing.doctor_groups:
        for rp in group.rps:
            print(f"RP{rp.rp_number} {rp.usage.name} ×{rp.usage.dispensing_quantity}{rp.usage.dispensing_unit}")
            for drug in rp.drugs:
                print(f"  {drug.name} {drug.dose}{drug.unit_name}")
```

入れ子をたどらずに一覧したい場合は `collect_rps` / `collect_drugs` が使えます。

```python
from medication_record_qr import collect_drugs

for dispensing, group, rp, drug in collect_drugs(notebook):
    print(dispensing.date, group.doctor.name if group.doctor else "", rp.rp_number, drug.name)
```

分割された複数のQRコードは、読み取った順番に関係なくまとめて渡せます。

```python
result = read_notebook_from_pngs([Path("2.png").read_bytes(), Path("1.png").read_bytes()])
```

### カメラ画像・PIL Image から読み取る

```python
from PIL import Image

from medication_record_qr import read_notebook_from_images

result = read_notebook_from_images([Image.open("okusuri.jpg")])
```

### すでにデコード済みのテキストを解析する

```python
from medication_record_qr import parse

result = parse("JAHISTC08,1\r\n1,鈴木 太郎,1,S330303,,,,,,,\r\n...")
```

### 構造化データをQRコードに変換する

```python
from pathlib import Path

from medication_record_qr import encode_notebook_to_pngs, serialize

# お薬手帳データのテキストとして出力する
text = serialize(notebook)

# QRコードのPNG画像として出力する(上限を超える場合は自動で複数枚に分割)
for index, png in enumerate(encode_notebook_to_pngs(notebook, error="m", scale=6), start=1):
    Path(f"okusuri-{index}.png").write_bytes(png)
```

SVG や data URI も生成できます。

```python
from medication_record_qr import encode_notebook_to_data_uris, encode_notebook_to_svgs

svgs = encode_notebook_to_svgs(notebook)
data_uris = encode_notebook_to_data_uris(notebook)
```

## 構造化データの形

仕様書 3.2.5「情報グループとレコード情報」の入れ子構造を、そのままデータクラスの入れ子で表現します。

```
MedicationNotebook                    バージョンレコード(JAHISTC**)
├─ patient                            患者情報(1)
├─ patient_remarks[]                  患者特記(2)
├─ otc_drugs[]                        要指導医薬品・一般用医薬品服用(3)
│   └─ ingredients[]                  要指導医薬品・一般用医薬品成分(31)
├─ notebook_memos[]                   手帳メモ(4)
├─ dispensings[]                      調剤等年月日(5)ごとの調剤情報グループ
│   ├─ institution                    調剤－医療機関等(11)
│   ├─ staff                          調剤－医師・薬剤師(15)
│   ├─ prescribing_institution        処方－医療機関(51)
│   ├─ doctor_groups[]                処方－医師(55)ごとのRPのまとまり
│   │   ├─ doctor                     処方－医師(55)
│   │   └─ rps[]                      RP(処方指示)単位
│   │       ├─ drugs[]                薬品(201)
│   │       │   ├─ supplements[]      薬品補足(281)
│   │       │   └─ cautions[]         薬品服用注意(291)
│   │       ├─ usage                  用法(301)
│   │       ├─ usage_supplements[]    用法補足(311)
│   │       └─ prescription_cautions[] 処方服用注意(391)
│   ├─ cautions[]                     服用注意(401)
│   ├─ provided_infos[]               医療機関等提供情報(411)
│   ├─ remaining_drug_checks[]        残薬確認(421)
│   ├─ remarks[]                      備考(501)
│   └─ patient_entries[]              患者等記入(601)
├─ family_pharmacists[]               かかりつけ薬剤師(701)
├─ split                              分割制御(911)
└─ unknown_records[]                  未知のレコード(前方互換のため保持)
```

項目値はすべて仕様書どおりの**文字列のまま**保持します。
年月日は西暦8桁(`20200410`)と和暦7桁(`R020410`)のどちらも記録されたまま保持し、
`date` 型への変換や和暦変換は行いません(利用側の要件に委ねる方針です)。

コード値の意味は `CODE_TABLES` から引けます。

```python
from medication_record_qr import CODE_TABLES, describe_code

describe_code(CODE_TABLES["sex"], "1")  # "男"
describe_code(CODE_TABLES["prefecture"], "13")  # "東京"
describe_code(CODE_TABLES["dosage_form"], "3")  # "屯服"
describe_code(CODE_TABLES["drug_code_type"], "2")  # "レセプト電算コード"
```

## 解析結果と検証

`parse` は解析できた範囲を常に返し、問題は `issues` として報告します。

```python
result = parse(text)

result.ok  # エラーが無ければ True
result.notebook  # 構造化データ(常に取得できる)
result.issues  # [Issue(level=..., code=..., message=..., line=..., record_no=..., field_key=...), ...]
result.records  # 解析前のレコード(行番号・項目の生値)
```

| 深刻度 | 扱い | 例 |
| --- | --- | --- |
| `error` | `ok` が False になる | バージョンレコードが無い / 必須項目が無い / コード種別に対応するコードが無い |
| `warning` | 解析は継続する | 未定義のコード値 / バイト数超過 / 年月日やデータ型の不正 / 未知のレコード / 同一№レコードの重複 / 用法レコードの欠落 |

必須項目の判定は、バージョンレコードの出力区分(1:医療機関等⇒患者等 / 2:患者等⇒医療機関等)に従います。

```python
parse(text, strict=True)  # 警告が1件でもあれば ok is False
parse(text, validate=False)  # 項目検証を行わない
parse(text, check_code_tables=False)  # コード表の検証のみ行わない
parse(text, direction="to_patient")  # 出力区分が読み取れない場合に仮定する提供方向
parse_or_raise(text)  # エラー時に ParseError を送出する
```

## 分割の制御

仕様書 3.2.9(3)「データを分割した場合の出力方法」に従い、各シンボルの先頭にバージョンレコード、
末尾に分割制御レコード(911)を出力します。

```python
from medication_record_qr import merge_split_parts, split_for_qr, to_qr_texts

# 1シンボルに収まるよう分割する
parts = split_for_qr(text, max_bytes_per_symbol=1800, data_id="12345678901234")

# 読み取ったテキストを結合する(データ連番順に並べ替える)
merged = merge_split_parts(parts)
merged.text
merged.issues  # 重複・欠落・データ固有IDの不一致を報告

# 構造化データから、QRコードに入れるテキストの配列を得る
texts = to_qr_texts(notebook, max_bytes_per_symbol=1800)
```

`encode_notebook_to_*` は既定で分割を行います。分割したくない場合は `split=False` を指定してください。
QRコードの容量を節約したい場合は `omit_trailing_empty_fields=True` で末尾の空項目を省略できます。

## 主なAPI

| API | 用途 |
| --- | --- |
| `parse(text, ...)` / `parse_or_raise` | テキスト → 構造化データ |
| `serialize(notebook, ...)` / `to_record_lines` | 構造化データ → テキスト |
| `decode_qr_from_png` / `decode_qr_from_image` | QR画像 → テキスト |
| `read_notebook_from_pngs` / `read_notebook_from_images` / `read_notebook_from_texts` | QR画像・テキスト → 構造化データ(分割の結合を含む) |
| `encode_text_to_png` / `encode_text_to_svg` / `encode_text_to_data_uri` | テキスト → QRコード |
| `encode_notebook_to_pngs` / `encode_notebook_to_svgs` / `encode_notebook_to_data_uris` | 構造化データ → QRコード(分割対応) |
| `split_for_qr` / `merge_split_parts` | 分割制御レコードを使った分割・結合 |
| `collect_rps` / `collect_drugs` | 入れ子をたどらずにRP・薬品を列挙する |
| `RECORD_SPECS` / `CODE_TABLES` / `FORMAT_VERSIONS` | 仕様定義そのもの(項目名・型・バイト数・コード表) |

## 文字コードについて

仕様書は Shift_JIS(JIS X 0201-1976 の8単位符号および JIS X 0208-1983 附属書1)を前提としています。
本ライブラリの既定値は、実際の医療システムで使われている Windows-31J(`cp932`)です。
Python 標準の `shift_jis` コーデックは波ダッシュ・全角チルダなどの扱いが異なり、
`Ｂ＋` や `～` を含むデータで変換に失敗することがあるためです。

外字が含まれていないかは `unencodable_characters` で確認できます。

```python
from medication_record_qr import unencodable_characters

unencodable_characters("髙橋 太郎")  # ['髙'] のように Shift_JIS で表現できない文字を返す
```

## 開発

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"

pytest          # テスト
mypy            # 型チェック
ruff check .    # Lint
```

テストでは次を検証しています。

- レコード定義表が仕様書のレイアウト(項目名・型・バイト数)と一致していること
- 別表1〜4のコード表の内容
- 付録1の出力データ例(例1〜例11)がエラー・警告なしで解析できること
- 出力データ例の構造(調剤情報グループ、処方－医師レコードによるRPのまとまり、補足レコードの紐づけ)
- 異常系(必須項目の欠落・未定義のコード値・未知のレコード・順序の逸脱・重複)
- テキストの往復(解析 → 出力で元のテキストと完全一致)
- **QRコードの往復**(`tests/test_qr_round_trip.py`): テキスト → QRコードのPNG画像 → 画像として読み取り → 元のテキストと完全一致。
  全フィクスチャについて、誤り訂正レベル l/m/q/h、画像サイズ・余白違い、型番指定、UTF-8指定、
  1シンボルの上限(1800バイト)いっぱいのデータ、複数シンボルに分割したデータで検証しています。
  QRコードに格納された生のバイト列が Shift_JIS(cp932) のバイト列と一致することも確認しています
- 構造化データの往復(構造化データ → QRコード → 読み取り → 構造化データ)
- 仕様書 3.2.9(3) の分割出力例の結合、および任意サイズでの分割・結合

仕様の対応状況・PDF内で記載が一致していない箇所については [SPEC-NOTES.md](../SPEC-NOTES.md) を参照してください。

## ライセンス

MIT
