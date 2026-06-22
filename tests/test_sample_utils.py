import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from sample_utils import enrich_samples_with_account_descriptions, load_account_description_map


def test_load_account_description_map_prefers_skat(tmp_path):
    (tmp_path / "SKAT.csv").write_text(
        "SAKNR,TXT50\n2202040000,应付账款-GR/IR\n1405020000,库存商品-自制成品\n",
        encoding="utf-8-sig",
    )
    (tmp_path / "TrialBalance.csv").write_text(
        "SAKNR,TXT50\n2202040000,应付账款-GR/余额表\n",
        encoding="utf-8-sig",
    )

    descriptions = load_account_description_map(tmp_path)

    assert descriptions["2202040000"] == "应付账款-GR/IR"
    assert descriptions["1405020000"] == "库存商品-自制成品"


def test_enrich_samples_with_account_descriptions_replaces_bad_ocr_text():
    samples = [{
        "DOC_NUM": "6000004976",
        "SAKNR": "2202040000",
        "TXT50": "应付账款-GR/珢",
        "AMOUNT": "598.470,60-",
    }]

    enriched = enrich_samples_with_account_descriptions(samples, {
        "2202040000": "应付账款-GR/IR"
    })

    assert enriched[0]["TXT50"] == "应付账款-GR/IR"
    assert samples[0]["TXT50"] == "应付账款-GR/珢"
