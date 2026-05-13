from flask import Flask, request, jsonify
from zhipuai import ZhipuAI
import os
import json
import re

app = Flask(__name__)

# 初始化客户端
api_key = os.getenv("ZHIPUAI_API_KEY")
if not api_key:
    raise ValueError("ZHIPUAI_API_KEY environment variable is not set")

client = ZhipuAI(api_key=api_key)

# 支持的语言映射
LANGUAGES = {
    "zh": "中文",
    "en": "英文",
    "ja": "日语",
    "ko": "韩语",
    "fr": "法语",
    "de": "德语",
    "es": "西班牙语",
    "ru": "俄语",
    "ar": "阿拉伯语",
    "it": "意大利语",
    "pt": "葡萄牙语"
}

@app.route('/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({'status': 'healthy', 'service': 'translator'})

@app.route('/translate/batch', methods=['POST'])
def translate_batch():
    """批量翻译 - 单次请求完成"""
    try:
        data = request.get_json()
        
        texts = data.get('texts', [])
        target_lang = data.get('target_lang', 'zh')
        
        if not texts:
            return jsonify({'error': '文本列表不能为空'}), 400
        
        if len(texts) > 50:
            return jsonify({'error': '单次最多翻译50条文本'}), 400
        
        lang_name = LANGUAGES.get(target_lang, target_lang)
        
        # 使用JSON格式确保解析准确
        prompt = f"""请将以下文本列表依次翻译成{lang_name}。

文本列表：
{json.dumps(texts, ensure_ascii=False)}

请以JSON格式返回翻译结果，格式如下：
{{"translations": ["翻译1", "翻译2", "翻译3"]}}

要求：
1. 只返回JSON，不要添加任何其他内容
2. 确保翻译结果数量与原文本数量相同
3. 保持翻译结果的顺序与原文本一致"""

        response = client.chat.completions.create(
            model="glm-4-flash",
            messages=[{"role": "user", "content": prompt}],
            thinking={"type": "disabled"},
            temperature=0.3
        )
        
        result_text = response.choices[0].message.content
        
        # 解析JSON响应
        try:
            json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
            if json_match:
                result_json = json.loads(json_match.group())
                translations = result_json.get('translations', [])
            else:
                translations = json.loads(result_text).get('translations', [])
        except json.JSONDecodeError:
            translations = [line.strip() for line in result_text.strip().split('\n') if line.strip()]
            translations = [re.sub(r'^\d+[\.\、\s]+', '', t) for t in translations]
        
        # 确保数量匹配
        if len(translations) != len(texts):
            if len(translations) < len(texts):
                translations.extend([f"翻译失败"] * (len(texts) - len(translations)))
            else:
                translations = translations[:len(texts)]
        
        results = []
        for original, translated in zip(texts, translations):
            results.append({
                'original': original,
                'translated': translated
            })
        
        return jsonify({
            'success': True,
            'results': results,
            'target_lang': target_lang,
            'count': len(results)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/translate', methods=['POST'])
def translate_single():
    """单条翻译接口"""
    try:
        data = request.get_json()
        
        text = data.get('text', '')
        target_lang = data.get('target_lang', 'zh')
        
        if not text:
            return jsonify({'error': '文本不能为空'}), 400
        
        lang_name = LANGUAGES.get(target_lang, target_lang)
        prompt = f"将以下文本翻译成{lang_name}，只返回翻译结果：\n{text}"
        
        response = client.chat.completions.create(
            model="glm-4-flash",
            messages=[{"role": "user", "content": prompt}],
            thinking={"type": "disabled"}
        )
        
        return jsonify({
            'success': True,
            'original': text,
            'translated': response.choices[0].message.content,
            'target_lang': target_lang
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/languages', methods=['GET'])
def get_languages():
    """获取支持的语言列表"""
    return jsonify(LANGUAGES)

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    debug = os.getenv("DEBUG", "False").lower() == "true"
    app.run(host='0.0.0.0', port=port, debug=debug)
