import re


def _clean_text(value):
    text = str(value or "").strip()
    return text if text.lower() not in {"nan", "none", "null"} else ""


def _normalize_code(value, *, field=""):
    text = _clean_text(value)
    if not text:
        return ""
    replacements = {
        "O": "0",
        "o": "0",
        "I": "1",
        "l": "1",
        "|": "1",
        "，": "",
        ",": "",
        " ": "",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    if field == "valuation_class":
        text = text.replace("?", "7")
        if text.startswith("S"):
            text = "3" + text[1:]
    return re.sub(r"[^0-9A-Za-z_.-]", "", text)


def normalize_plant_code(value):
    text = _normalize_code(value).upper()
    text = re.sub(r"[^0-9A-Z]", "", text)
    if len(text) == 3:
        # SAP plant is fixed at four characters. OCR often drops a repeated
        # middle character in screenshots, for example 4110 -> 410.
        return text[:2] + text[1:]
    if len(text) > 4:
        return text[:4]
    return text


def _next_value(lines, labels, *, numeric=False, field=""):
    label_set = tuple(labels)
    for idx, line in enumerate(lines):
        if any(label in line for label in label_set):
            for candidate in lines[idx + 1:idx + 5]:
                if not candidate or any(label in candidate for label in label_set):
                    continue
                value = _normalize_code(candidate, field=field) if numeric else _clean_text(candidate)
                if value:
                    return value
    return ""


def _is_description_noise(text):
    cleaned = _clean_text(text)
    normalized = _normalize_code(cleaned)
    if not cleaned:
        return True
    if re.fullmatch(r"[\[\\]?", cleaned):
        return True
    if re.fullmatch(r"\d{3,18}", normalized):
        return True
    noise_fragments = (
        "编辑",
        "转到",
        "环境",
        "系统",
        "帮助",
        "附加数据",
        "组织级别",
        "锁定的字段",
        "质量管理",
        "质里管理",
        "会计",
        "成本",
        "咸本",
        "工厂库存",
        "期间",
        "成本核算运行",
        "评估",
        "评怙",
        "价格",
        "库存",
        "货币",
        "公司代码",
        "未来价格",
        "上期价格",
        "最近价格",
        "成本构成",
        "KB/s",
        "KBIs",
        "NN03",
        "OVR",
    )
    return any(fragment in cleaned for fragment in noise_fragments)


def _find_material(lines, full_text):
    title_match = re.search(r"显示物[料辫]\s*([A-Za-z0-9OIl|?]+)\s*[（(]([^）)]+)[）)]", full_text)
    title_number = _normalize_code(title_match.group(1)) if title_match else ""
    title_desc = _clean_text(title_match.group(2)) if title_match else ""

    for idx, line in enumerate(lines):
        if "物料" in line and len(line) <= 8:
            for candidate in lines[idx + 1:idx + 5]:
                material = _normalize_code(candidate)
                if re.fullmatch(r"\d{6,18}", material):
                    return title_number or material, title_desc

    return title_number, title_desc


def _find_material_description(lines, material_number, fallback):
    normalized_material = _normalize_code(material_number)
    for idx, line in enumerate(lines):
        if line.strip() in {"物料", "物料号", "Material"}:
            for candidate in lines[idx + 1:idx + 8]:
                if _is_description_noise(candidate):
                    continue
                if "工厂" in candidate:
                    continue
                if len(_clean_text(candidate)) >= 3:
                    return _clean_text(candidate)

    if normalized_material:
        for idx, line in enumerate(lines):
            if "显示物" in line:
                continue
            if _normalize_code(line) == normalized_material:
                for candidate in lines[idx + 1:idx + 5]:
                    text = _clean_text(candidate)
                    normalized = _normalize_code(text)
                    if normalized == normalized_material or _is_description_noise(text):
                        continue
                    if "工厂" in text:
                        continue
                    if len(text) >= 3:
                        return text
    return fallback


def _find_price_control(lines):
    for idx, line in enumerate(lines):
        if "价格控制" not in line:
            continue
        for candidate in lines[idx + 1:idx + 5]:
            value = _normalize_code(candidate).upper()
            if value in {"S", "V"}:
                return value
    return ""


def _find_plant(lines):
    for idx, line in enumerate(lines):
        if line.strip() in {"工厂", "Plant"}:
            for candidate in lines[idx + 1:idx + 5]:
                plant = normalize_plant_code(candidate)
                if re.fullmatch(r"[A-Z0-9]{4}", plant):
                    return plant

    for idx, line in enumerate(lines):
        text = _clean_text(line)
        if "青岛" in text or ("工厂" in text and len(text) > 4 and "工厂库存" not in text):
            for candidate in reversed(lines[max(0, idx - 4):idx]):
                plant = normalize_plant_code(candidate)
                if re.fullmatch(r"[A-Z0-9]{4}", plant):
                    return plant
    return ""


def _find_plant_name(lines):
    for line in lines:
        text = _clean_text(line)
        if "工厂" in text and len(text) > 4:
            return text
    return ""


def parse_mm03_ocr_text(ocr_text, source_file=""):
    lines = [_clean_text(line) for line in str(ocr_text or "").splitlines()]
    lines = [line for line in lines if line]
    full_text = "\n".join(lines)

    material_number, title_desc = _find_material(lines, full_text)
    valuation_class = _next_value(lines, ["评估分类", "评估分", "评怙分类", "评估类"], numeric=True, field="valuation_class")

    return {
        "source_file": _clean_text(source_file),
        "material_number": material_number,
        "plant": _find_plant(lines),
        "valuation_class": valuation_class,
    }


def mm03_records_to_dataframe_rows(records):
    rows = []
    for record in records or []:
        rows.append({
            "MM03文件": record.get("source_file", ""),
            "物料号": record.get("material_number", ""),
            "工厂编号": normalize_plant_code(record.get("plant", "")),
            "评估分类": record.get("valuation_class", ""),
        })
    return rows
