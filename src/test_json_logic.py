import re
import json

def test_extraction_logic(res):
    print(f"--- 原始输入 ---\n{res}\n---")
    
    # 1. 尝试移除 Markdown 代码块标记
    clean_res = re.sub(r'```json\s*|\s*```', '', res, flags=re.IGNORECASE).strip()
    print(f"--- 移除 Markdown 后 ---\n{clean_res}\n---")
    
    # 2. 正则匹配最外层的 {}
    match = re.search(r'\{.*\}', clean_res, re.DOTALL)
    if match:
        json_str = match.group()
        print(f"--- 匹配到的 JSON 字符串 ---\n{json_str}\n---")
        try:
            data = json.loads(json_str)
            print("✅ 成功解析 JSON")
            return data
        except Exception as e:
            print(f"❌ json.loads 失败: {e}")
            # 尝试修复 AI 可能导致的尾部逗号等小错误
            try:
                fixed_json = re.sub(r',\s*\}', '}', json_str)
                data = json.loads(fixed_json)
                print("✅ 修复后成功解析 JSON")
                return data
            except Exception as e2:
                print(f"❌ 修复后依然失败: {e2}")
    else:
        print("❌ 未能匹配到 {} 结构")
    return None

# 模拟一些可能的 AI 返回情况
print("\n测试情况 1: 带 Markdown 和文字")
test_extraction_logic("好的，解析如下：\n```json\n{\"DOC_NUM\": \"4900019620\"}\n```")

print("\n测试情况 2: 纯文字报错")
test_extraction_logic("抱歉，我没能找到凭证号。")

print("\n测试情况 3: 带乱码的 JSON")
test_extraction_logic("{\"DOC_NUM\": \"4900019620\",}")
