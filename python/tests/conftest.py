"""テスト共通の設定。

フィクスチャは仕様書「付録１ お薬手帳イメージと出力データ例」の出力データ例そのもので、
TypeScript実装と共通のディレクトリ(リポジトリ直下の ``fixtures/``)に置いている。
"""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures"


def read_fixture(name: str) -> str:
    """フィクスチャを読み込む(レコード終端 CR+LF をそのまま保持する)。"""
    with open(FIXTURES_DIR / name, encoding="utf-8", newline="") as fp:
        return fp.read()


#: 付録１の出力データ例(例1〜例11)
EXAMPLE_FIXTURES = sorted(path.name for path in FIXTURES_DIR.glob("example-*.txt"))

#: 分割出力例を含む全フィクスチャ
ALL_FIXTURES = sorted(path.name for path in FIXTURES_DIR.glob("*.txt"))

#: 出力データ例がレコードレイアウトと一致していないもの(SPEC-NOTES.md 参照)
INCONSISTENT_EXAMPLES = ("example-07.txt", "example-08.txt", "example-11.txt")

#: エラー・警告なしで解析できる出力データ例
CLEAN_EXAMPLES = [name for name in EXAMPLE_FIXTURES if name not in INCONSISTENT_EXAMPLES]


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    return FIXTURES_DIR
