# おくすり手帳QRコードのサンプル調査

インターネット上で公開されている、JAHIS電子版お薬手帳データフォーマット(JAHIS TC)のQRコード／データのサンプルを調査した結果です。

調査日: 2026-09-14

## 結論(先に要点)

- **スキャン可能な「お薬手帳QRコードのサンプル画像」を配布しているサイトは見つかりませんでした。**
  公開されているサンプルの実体は、**仕様書の「出力データ例」(テキスト)** と **OSSのテストデータ** です。
- 電子版お薬手帳アプリ各社(harmo / EPARK / お薬手帳プラス / NOBORI など)のページは
  「調剤明細書に印字されたQRコードを読み取る手順」の説明で、サンプルデータの配布はしていません。
- 実物のQRコードを復号したデータが公開されている例はありましたが、
  それは **院外処方箋2次元シンボル(`JAHIS10`)** であって、**お薬手帳(`JAHISTC**`)ではありません**(後述)。
- そのため本リポジトリでは、**仕様書の出力データ例をそのままテストデータ**として採用しています。

下表の QRコード画像は、いずれも本ライブラリで生成し、生成したPNGを読み取って
元のテキストと完全一致することを確認済みです(再現方法は末尾)。

## 1. 入手・検証できたサンプル

| # | サンプル | QRコード | 内容 | データ量 | 検証結果 | ソース |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | JAHIS仕様書 付録1 例1<br>薬局で出力(内服薬のみ) | [PNG](./samples/01_jahis-appendix1-example-01.png) | `JAHISTC08,1` / 患者(鈴木 太郎・S330303) / 調剤 R020410 / 工業会薬局 駅前店 / 工業会病院 / RP2件(ｺﾘｵﾊﾟﾝｶﾌﾟｾﾙ5mg 他) | 441バイト<br>12レコード | 解析エラー・警告なし、テキスト完全往復 | [JAHIS技術文書 24-104 Ver.2.6](https://www.jahis.jp/standard/detail/id=1058)(PDF 付録1) |
| 2 | JAHIS仕様書 付録1 例4<br>複数診療科での出力 | [PNG](./samples/02_jahis-appendix1-example-04.png) | 処方－医師レコード(55)が2件(内科 工業会 次郎 / 皮膚科 佐藤 三郎)、RP1〜7、残薬確認(421)・備考(501)を含む | 995バイト<br>27レコード | 同上 | 同上 |
| 3 | JAHIS仕様書 付録1 例11<br>患者等→医療機関等 | [PNG](./samples/03_jahis-appendix1-example-11.png) | `JAHISTC08,2` / 患者特記(2)・要指導医薬品(3,31)・手帳メモ(4)・複数調剤・患者等記入(601)・かかりつけ薬剤師(701) | 1,560バイト<br>40レコード | かかりつけ薬剤師の「連絡先」未設定を検出(※) | 同上 |
| 4 | JAHIS仕様書 3.2.9(3)<br>分割出力例 1/2 | [PNG](./samples/04_jahis-split-part-1.png) | 分割制御レコード `911,12345678901234,2,1` を末尾に持つ1枚目 | 465バイト<br>14レコード | 解析エラーなし、2枚を結合して元データに復元できることを確認 | 同上(PDF 3.2.9(3)) |
| 5 | JAHIS仕様書 3.2.9(3)<br>分割出力例 2/2 | [PNG](./samples/05_jahis-split-part-2.png) | `911,12345678901234,2,2` を末尾に持つ2枚目 | 544バイト<br>15レコード | 同上 | 同上 |
| 6 | 第三者OSS `jahis-rx-parser`<br>全レコード種別 | [PNG](./samples/06_oss-tc-supported-records-full.png) | `JAHISTC08,1` / 患者・患者特記・OTC・成分・手帳メモ・調剤・処方・薬品・用法・各種注意を網羅した合成データ | 895バイト<br>24レコード | 本ライブラリで解析エラー・警告なし | [GitHub YasushiMatsumoto/jahis-rx-parser](https://github.com/YasushiMatsumoto/jahis-rx-parser) `test/fixtures/tc-supported-records-full.txt` (MIT) |

※ 例11・例7は、仕様書の出力データ例がレコードレイアウト(表3-31)と一致していない箇所です。詳細は [SPEC-NOTES.md](../SPEC-NOTES.md) を参照。

### 1-1. 第三者OSSのテストデータ(8件)の検証結果

[jahis-rx-parser](https://github.com/YasushiMatsumoto/jahis-rx-parser)(MIT)の `test/fixtures/tc-*.txt` を、本ライブラリで解析した結果です。

| ファイル | バージョン | 出力区分 | 本ライブラリでの解析結果 |
| --- | --- | --- | --- |
| `tc-minimal-valid.txt` | JAHISTC01 (Ver.1.0) | 1 | エラー・警告なし |
| `tc-multi-dispensing.txt` | JAHISTC08 | 1 | エラー・警告なし(調剤2件) |
| `tc-supported-records-full.txt` | JAHISTC08 | 1 | エラー・警告なし |
| `tc-with-otc-components-and-remaining-medicine.txt` | JAHISTC08 | 2 | エラー・警告なし |
| `tc-split-output-part-2.txt` | JAHISTC08 | 1 | エラー・警告なし |
| `tc-output-category-2-full.txt` | JAHISTC12 | 2 | `unknown-version` 警告(JAHISTC12 は仕様書 表3-9 のサンプルにのみ登場する番号) |
| `tc-invalid-missing-drug-code.txt` | JAHISTC01 | 1 | `missing-required-field` エラー(意図的な不正データ。作者の意図どおり検出) |
| `tc-invalid-missing-otc-sequence-parent.txt` | JAHISTC08 | 2 | `orphan-record` 警告(同上) |

8件中6件は正常に解析でき、残り2件は**意図的に不正なデータ**で、本ライブラリが期待どおりエラー／警告を出しました。
テキストの往復は、改行コードを合わせれば3件が完全一致します。残りは薬品レコード(201)の末尾の空項目を
出力するかがレコード単位で異なるだけで、**構造化データとしては同値**です。

## 2. 注意: 実物のQRコード復号例は「処方箋」のものでした

`jahis-rx-parser` には、実際のQRコードを復号して匿名化したという
`test/fixtures/qr-decoded-anonymized.txt` と `test/external-data/sample.txt` が含まれています。
ただし、いずれも1行目が **`JAHIS10`** であり、これは別規格です。

| 規格 | 先頭行 | 用途 | 本ライブラリの対象 |
| --- | --- | --- | --- |
| JAHIS電子版お薬手帳データフォーマット | `JAHISTC08` など | 薬局・医療機関 ⇔ 患者等 のお薬手帳データ交換 | **対象** |
| JAHIS院外処方箋2次元シンボル記録条件規約 | `JAHIS10` など | 医療機関 → 薬局 の処方箋データ | 対象外 |

本ライブラリにこれらを読ませると、`missing-version-record` エラーとともに
「先頭レコードがバージョンレコード(JAHISTC**)ではありません: JAHIS10」と報告されます(期待どおりの動作)。

## 3. 参照先(この環境からは取得できず、内容は未検証)

以下は検索で存在を確認しましたが、**実行環境のネットワークポリシーにより取得できなかった**ため、
掲載内容は未確認です。サンプルデータの配布があるかどうかも未検証です。

| 区分 | ページ | URL |
| --- | --- | --- |
| 規格 | JAHIS電子版お薬手帳データフォーマット仕様書(各版) | https://www.jahis.jp/standard/detail/id=1058 |
| 規格(転載) | 厚生労働省 掲載の Ver.1.1 PDF | https://www.mhlw.go.jp/seisakunitsuite/bunya/kenkou_iryou/iyakuhin/dl/01-06.pdf |
| 規格(転載) | 香川県 掲載の Ver.1.0 PDF | https://www.pref.kagawa.lg.jp/documents/7477/142_240926.pdf |
| アプリ | harmo おくすり手帳 「調剤明細書等のQRコードを使って登録する」 | https://support.harmo.biz/input/p795 |
| アプリ | EPARKお薬手帳 「QRコードの登録方法」 | https://okusuritecho.epark.jp/renew/faq/details/1685f4f53bc8806f |
| アプリ | 日本調剤 お薬手帳プラス 「お薬情報の登録：QRコード読み取り」 | https://portal.okusuriplus.com/support/guide/2081/ |
| アプリ | NOBORI 「QRコードを読み取ってお薬を追加する」 | https://nobori.me/help/view/2-8/ |
| 記事 | Qiita「電子版お薬手帳をWebブラウザ表示する」 | https://qiita.com/hiro_literal/items/c357ee15b0b98ff176c3 |

## 4. その他の関連リポジトリ

| リポジトリ | 内容 | サンプルデータ |
| --- | --- | --- |
| [oika/jahis-okusuri-unifier](https://github.com/oika/jahis-okusuri-unifier) | お薬手帳アプリが1調剤1ファイルで出力したCSVを結合するツール(C#) | 無し。READMEに「エクスポートしたファイルの1行目が `JAHISTC07,1` のような文字列ならJAHISフォーマット」と実運用での記載あり |
| [YasushiMatsumoto/jahis-rx-parser](https://github.com/YasushiMatsumoto/jahis-rx-parser) | JAHIS Rx / JAHIS TC のパーサ(TypeScript, MIT) | `test/fixtures/tc-*.txt` 8件(上表) |

PyPI には関連パッケージが見つかりませんでした(`jahis` / `okusuri` / `medication-notebook` いずれも未登録)。

## 5. サンプルQRコードの再現方法

`docs/samples/*.png` は、本リポジトリのテストデータから生成したものです。同じものを再生成できます。

```bash
# TypeScript
npx tsx examples/round-trip.ts

# Python
cd python && python examples/round_trip.py
```

任意のフィクスチャからQRコードを生成する場合:

```python
from medication_record_qr import encode_text_to_png, decode_qr_from_png

with open("fixtures/example-04.txt", encoding="utf-8", newline="") as fp:
    text = fp.read()

png = encode_text_to_png(text, scale=6)
open("sample.png", "wb").write(png)

assert decode_qr_from_png(png) == text  # 読み取って元のテキストと一致
```
