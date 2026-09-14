"""使い方の例。

1. お薬手帳データのテキストを構造化データへ変換する
2. 構造化データをQRコードのPNG画像として書き出す
3. 書き出したPNG画像を読み戻して構造化データに戻す

実行: python examples/round_trip.py
"""

from __future__ import annotations

from pathlib import Path

from medication_record_qr import (
    CODE_TABLES,
    describe_code,
    encode_notebook_to_pngs,
    parse,
    read_notebook_from_pngs,
    serialize,
)

# 仕様書「付録１ お薬手帳イメージと出力データ例」の例4(複数診療科での出力)
FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "example-04.txt"

with open(FIXTURE, encoding="utf-8", newline="") as fp:
    text = fp.read()

# 1. テキスト -> 構造化データ
result = parse(text)
for issue in result.issues:
    print(f"[{issue.level}] {issue.message}")

notebook = result.notebook
patient = notebook.patient
assert patient is not None
print(f"患者: {patient.name} ({describe_code(CODE_TABLES['sex'], patient.sex or '')})")

for dispensing in notebook.dispensings:
    institution = dispensing.institution
    print(f"\n調剤等年月日 {dispensing.date} / {institution.name if institution else '(なし)'}")
    prescribing = dispensing.prescribing_institution
    print(f"  処方元: {prescribing.name if prescribing else '(なし)'}")

    for group in dispensing.doctor_groups:
        if group.doctor is not None:
            print(f"  {group.doctor.department_name or ''} {group.doctor.name}")
        for rp in group.rps:
            usage = rp.usage
            dosage_form = describe_code(CODE_TABLES["dosage_form"], usage.dosage_form_code or "") if usage else None
            usage_name = usage.name if usage and usage.name else ""
            print(f"    RP{rp.rp_number} [{dosage_form or '-'}] {usage_name}")
            for drug in rp.drugs:
                print(f"      {drug.name} {drug.dose or ''}{drug.unit_name or ''}")

# 2. 構造化データ -> QRコード
pngs = encode_notebook_to_pngs(notebook, scale=6)
for index, png in enumerate(pngs, start=1):
    Path(f"okusuri-{index}.png").write_bytes(png)
print(f"\nQRコードを {len(pngs)} 枚出力しました")

# 3. QRコード -> 構造化データ
restored = read_notebook_from_pngs(pngs)
print("往復一致:", serialize(restored.notebook) == text)
