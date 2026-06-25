import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from mm03_parser import parse_mm03_ocr_text


def test_parse_mm03_ocr_text_prefers_title_material_number_and_normalizes_fields():
    text = """
    显示物料50006420 (成品)
    物料
    60006420
    新希望(琴牌)罐装鲜奶300ML*12
    工厂
    410
    青岛新希望琴牌乳业工厂
    基本单位
    每一个
    评估分类
    ?921
    价格控制
    S
    标准价格
    1,327.79
    """

    record = parse_mm03_ocr_text(text, "MM03销售.png")

    assert record["source_file"] == "MM03销售.png"
    assert record["material_number"] == "50006420"
    assert record["material_description"].startswith("新希望")
    assert record["plant"] == "410"
    assert record["plant_name"] == "青岛新希望琴牌乳业工厂"
    assert record["base_unit"] == "每一个"
    assert record["valuation_class"] == "7921"
    assert record["price_control"] == "S"


def test_parse_mm03_ocr_text_normalizes_valuation_class_ocr_noise():
    text = """
    显示物辫10000000 (原辅材料)
    物料
    IOOOOOO0
    原辅材料
    工厂
    410
    青岛新希望琴牌乳业工厂
    基本单位
    千克
    评怙分类
    SOO0
    价格控制
    V
    """

    record = parse_mm03_ocr_text(text, "MM03采购.png")

    assert record["material_number"] == "10000000"
    assert record["material_description"] == "原辅材料"
    assert record["plant"] == "410"
    assert record["valuation_class"] == "3000"
    assert record["price_control"] == "V"
