import easyocr
import json
import io
import re
import os
import numpy as np
from PIL import Image, ImageDraw
import ssl

# 核心修复：绕过 SSL 证书校验
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except:
    pass

class OCRProcessor:
    def __init__(self):
        # 初始化 EasyOCR
        self.reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)

    def process_and_parse(self, image_bytes, llm_client=None):
        try:
            # 1. 执行识别
            result = self.reader.readtext(image_bytes)
            if not result:
                return {"error": "未发现文字内容"}
            
            # 2. 提取文本
            ocr_text = "\n".join([line[1] for line in result])
            
            # 3. 绘制预览图
            image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            draw = ImageDraw.Draw(image)
            for line in result:
                box = line[0]
                points = [(p[0], p[1]) for p in box]
                draw.polygon(points, outline="red", width=3)
            
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='JPEG')
            viz_bytes = img_byte_arr.getvalue()

            final_res = {
                "OCR_TEXT": ocr_text,
                "viz_img": viz_bytes
            }

            if llm_client and not llm_client.mock_mode:
                parsed_elements = self.parse_with_llm(ocr_text, llm_client)
                final_res.update(parsed_elements)
            
            return final_res
            
        except Exception as e:
            return {"error": f"OCR 运行故障: {str(e)}"}

    def parse_with_llm(self, text, llm_client):
        """
        利用 DeepSeek 解析 SAP 截图。
        针对 R1 模型的各种“怪异”输出进行了终极兼容性优化。
        """
        system_prompt = "你是一个财务数据机器人。你只能输出纯 JSON 数据，严禁任何解释性文字。"
        user_prompt = f"""请分析以下 OCR 文字。
---
{text}
---
### 目标：
识别所有会计分录行项目。必须提取：DOC_NUM (凭证号), SAKNR (科目), TXT50 (名称), AMOUNT (数值), SHKZG (S/H), DATE (YYYY-MM-DD)。

### 格式要求：
直接返回一个 JSON 数组，例如：
[
  {{"DOC_NUM": "...", "SAKNR": "...", "TXT50": "...", "AMOUNT": 12.34, "SHKZG": "S", "DATE": "2026-06-01"}},
  ...
]
"""
        try:
            raw_res = llm_client.generate_text(system_prompt, user_prompt)
            
            # --- 终极 JSON 捕获逻辑 ---
            # 1. 物理移除思考链
            clean_text = re.sub(r'<think>[\s\S]*?</think>', '', raw_res, flags=re.IGNORECASE).strip()
            
            # 2. 强力提取：找到第一个 [ 或 { 到最后一个 ] 或 }
            # 这能解决“Here is the JSON: [...]”这种带前后缀的情况
            start_idx = -1
            end_idx = -1
            for char_idx, char in enumerate(clean_text):
                if char in ('[', '{'):
                    if start_idx == -1: start_idx = char_idx
                if char in (']', '}'):
                    end_idx = char_idx
            
            json_str = ""
            if start_idx != -1 and end_idx != -1:
                json_str = clean_text[start_idx:end_idx+1]
            
            # 3. 尝试解析
            data = None
            if json_str:
                try:
                    # 尝试修复一些常见的 AI 生成错误（如换行符、多余逗号）
                    json_str = re.sub(r',\s*([\]\}])', r'\1', json_str)
                    data = json.loads(json_str)
                except:
                    # 尝试使用更宽松的解析（寻找多个独立的 {} 对象）
                    try:
                        potential_dicts = re.findall(r'\{[\s\S]*?\}', json_str)
                        data = [json.loads(re.sub(r',\s*([\]\}])', r'\1', d)) for d in potential_dicts]
                    except:
                        pass
            
            if not data:
                return {"error": "AI 返回格式无法解析", "raw_content": raw_res}
            
            # 统一转为列表
            raw_list = data if isinstance(data, list) else [data]
            
            # 4. 字段归一化与日期清洗
            normalized = []
            mapping = {
                "DOC_NUM": ["doc_num", "凭证号", "开票凭证", "凭证编号"],
                "DATE": ["date", "日期", "过账日期", "记账日期", "凭证日期"],
                "SAKNR": ["saknr", "科目", "总账科目", "帐目", "代码"],
                "TXT50": ["txt50", "科目名称", "描述", "短文本", "名称"],
                "AMOUNT": ["amount", "金额", "数值"],
                "SHKZG": ["shkzg", "借/贷", "标识", "方向"]
            }
            
            for item in raw_list:
                node = {}
                for target, aliases in mapping.items():
                    val = item.get(target)
                    if val is None:
                        for a in aliases:
                            if a in item: val = item[a]; break
                    
                    if target == "DATE" and val:
                        val = str(val).replace('.', '-').replace('/', '-')
                    if target == "AMOUNT" and val:
                        try:
                            # 清洗金额中的逗号
                            if isinstance(val, str):
                                val = val.replace(',', '')
                            val = float(val)
                        except: pass
                    node[target] = val
                normalized.append(node)
                
            return {"items": normalized}
            
        except Exception as e:
            return {"error": f"AI 解析崩溃: {str(e)}", "raw": raw_res}
