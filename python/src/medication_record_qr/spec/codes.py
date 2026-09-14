"""JAHIS電子版お薬手帳データフォーマット仕様書 Ver.2.6「別表 各種コード表」。

各レコードレイアウトの備考欄で定義されている区分値も同じ形式で保持する。
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class CodeTable:
    """コード表。"""

    #: コード表の識別名
    name: str
    #: 仕様書上の名称
    label: str
    #: コード値 -> 内容
    values: Mapping[str, str]
    note: str | None = None

    def is_valid(self, value: str) -> bool:
        """コード値がコード表に定義されているかを返す。"""
        return value in self.values

    def describe(self, value: str) -> str | None:
        """コード値に対応する内容を返す(未定義の場合は ``None``)。"""
        return self.values.get(value)


def _table(name: str, label: str, values: dict[str, str], note: str | None = None) -> CodeTable:
    return CodeTable(name=name, label=label, values=MappingProxyType(dict(values)), note=note)


#: 別表１ 年号区分コード
ERA = _table("era", "年号区分コード", {"M": "明治", "T": "大正", "S": "昭和", "H": "平成", "R": "令和"})

_PREFECTURE_NAMES = (
    "北海道",
    "青森",
    "岩手",
    "宮城",
    "秋田",
    "山形",
    "福島",
    "茨城",
    "栃木",
    "群馬",
    "埼玉",
    "千葉",
    "東京",
    "神奈川",
    "新潟",
    "富山",
    "石川",
    "福井",
    "山梨",
    "長野",
    "岐阜",
    "静岡",
    "愛知",
    "三重",
    "滋賀",
    "京都",
    "大阪",
    "兵庫",
    "奈良",
    "和歌山",
    "鳥取",
    "島根",
    "岡山",
    "広島",
    "山口",
    "徳島",
    "香川",
    "愛媛",
    "高知",
    "福岡",
    "佐賀",
    "長崎",
    "熊本",
    "大分",
    "宮崎",
    "鹿児島",
    "沖縄",
)

#: 別表２ 都道府県コード
PREFECTURE = _table(
    "prefecture",
    "都道府県コード",
    {f"{index + 1:02d}": name for index, name in enumerate(_PREFECTURE_NAMES)},
)

#: 別表３ 点数表コード
SCORE_TABLE = _table(
    "score_table",
    "点数表コード",
    {"1": "医科", "3": "歯科", "4": "調剤"},
    "処方－医療機関レコード(51)では 1:医科 / 3:歯科 のみ。",
)

#: 別表４ 剤形コード
DOSAGE_FORM = _table(
    "dosage_form",
    "剤形コード",
    {
        "1": "内服",
        "2": "内滴",
        "3": "屯服",
        "4": "注射",
        "5": "外用",
        "6": "浸煎",
        "7": "湯",
        "9": "材料",
        "10": "その他",
    },
)

#: バージョンレコード 出力区分
OUTPUT_CATEGORY = _table(
    "output_category",
    "出力区分",
    {
        "1": "医療機関・薬局から患者等に情報を提供する場合",
        "2": "患者等から医療機関・薬局に情報を提供する場合",
    },
)

#: レコード作成者
RECORD_CREATOR = _table(
    "record_creator",
    "レコード作成者",
    {"1": "医療関係者", "2": "患者等", "8": "その他", "9": "不明"},
)

#: 患者特記種別 (患者特記レコード)
PATIENT_REMARK_TYPE = _table(
    "patient_remark_type",
    "患者特記種別",
    {"1": "アレルギー歴", "2": "副作用歴", "3": "既往歴", "9": "その他"},
)

#: 薬品コード種別 (薬品レコード)
DRUG_CODE_TYPE = _table(
    "drug_code_type",
    "薬品コード種別",
    {
        "1": "コードなし",
        "2": "レセプト電算コード",
        "3": "厚労省コード",
        "4": "YJコード",
        "6": "HOTコード",
    },
)

#: 一般名コード種別 (薬品レコード)
GENERAL_NAME_CODE_TYPE = _table(
    "general_name_code_type",
    "一般名コード種別",
    {"1": "コードなし", "2": "一般名コード"},
)

#: コード種別 (要指導医薬品・一般用医薬品成分レコード)
INGREDIENT_CODE_TYPE = _table(
    "ingredient_code_type",
    "コード種別",
    {"1": "コードなし", "2": "成分名コード(セルフメディケーションデータベースセンター)"},
)

#: 用法コード種別 (用法レコード)
USAGE_CODE_TYPE = _table(
    "usage_code_type",
    "用法コード種別",
    {"1": "コードなし", "2": "JAMI用法コード"},
    "3以降は将来の統一コードのために予約されている。",
)

#: 提供情報種別 (医療機関等提供情報レコード)
PROVIDED_INFO_TYPE = _table(
    "provided_info_type",
    "提供情報種別",
    {
        "30": "入院中に副作用が発現した薬剤に関する情報",
        "31": (
            "退院後の療養を担う保険医療機関での投薬又は保険薬局での調剤に必要な服薬の状況及び投薬上の工夫に関する情報"
        ),
        "99": "その他",
    },
)

#: 患者性別 (患者情報レコード)
SEX = _table("sex", "患者性別", {"1": "男", "2": "女"})

#: コード表名 -> コード表
CODE_TABLES: Mapping[str, CodeTable] = MappingProxyType(
    {
        table.name: table
        for table in (
            ERA,
            PREFECTURE,
            SCORE_TABLE,
            DOSAGE_FORM,
            OUTPUT_CATEGORY,
            RECORD_CREATOR,
            PATIENT_REMARK_TYPE,
            DRUG_CODE_TYPE,
            GENERAL_NAME_CODE_TYPE,
            INGREDIENT_CODE_TYPE,
            USAGE_CODE_TYPE,
            PROVIDED_INFO_TYPE,
            SEX,
        )
    }
)


def describe_code(table: CodeTable, value: str) -> str | None:
    """コード値に対応する内容を返す(未定義の場合は ``None``)。"""
    return table.describe(value)


def is_valid_code(table: CodeTable, value: str) -> bool:
    """コード値がコード表に定義されているかを返す。"""
    return table.is_valid(value)
