"""AI 增强模块：使用 AI API 为纯文本文章自动添加 Markdown 结构标记。"""

import random
import base64
import requests


def is_plain_text(text):
    """检测文本是否为纯文本（缺少 Markdown 标记）。

    统计 ## 标题、**加粗**、- 列表、> 引用、` 代码 等格式标记数量，
    如果标记数量很少（<3个），返回 True，表示文本基本是纯文本。

    Args:
        text (str): 待检测的文本

    Returns:
        bool: True 表示是纯文本，False 表示已包含较多 Markdown 标记
    """
    if not text:
        return True

    count = 0

    # 统计 ## 标题标记
    count += text.count("##")

    # 统计 **加粗** 标记（成对出现算一组）
    count += text.count("**") // 2

    # 统计 - 列表标记（行首的短横线）
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("- "):
            count += 1

    # 统计 > 引用标记
    for line in text.splitlines():
        stripped = line.lstrip()
        if stripped.startswith("> "):
            count += 1

    # 统计 ` 代码标记（成对出现算一组）
    count += text.count("`") // 2

    # 标记数量少于 3 个，视为纯文本
    return count < 3


def build_enhance_prompt(text):
    """构建 AI 增强的提示词。

    根据规则生成完整的 prompt，指导 AI 为纯文本添加 Markdown 结构标记，
    同时不改变原文措辞。

    Args:
        text (str): 原始纯文本

    Returns:
        str: 完整的 prompt
    """
    rules = """请对以下纯文本添加 Markdown 结构标记，严格遵循以下规则：

1. 加标题：识别逻辑段落和主题转换点，在转换处插入 ## 标题
2. 分段落：确保段落之间有空行分隔
3. 加列表：识别并列/枚举性质的内容，加 - 或 1. 标记
4. 加强调：识别关键词、产品名、核心概念，加 **加粗**
5. 清理格式：去除多余空行、修正缩进、统一标点
6. 不改措辞：不调语序、不增删内容、不润色文字

只输出添加标记后的文本，不要添加任何解释说明。"""

    return f"{rules}\n\n---\n\n{text}"


def call_ai_api(prompt, ai_config):
    """调用 AI API（OpenAI 兼容接口）。

    使用 chat/completions 接口发送请求，获取 AI 增强后的文本。

    Args:
        prompt (str): 完整的提示词
        ai_config (dict): AI 配置，含 url（基础 URL）、api_key、model

    Returns:
        dict: {"content": str, "error": str}
    """
    base_url = ai_config.get("url", "").rstrip("/")
    api_key = ai_config.get("api_key", "")
    model = ai_config.get("model", "")

    # 构建完整的 API 地址
    url = f"{base_url}/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        data = response.json()

        # 从响应中提取内容
        content = data["choices"][0]["message"]["content"]
        return {"content": content, "error": ""}

    except requests.exceptions.Timeout:
        return {"content": "", "error": "AI API 请求超时（60秒）"}
    except requests.exceptions.ConnectionError:
        return {"content": "", "error": f"无法连接 AI API：{url}"}
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else "未知"
        return {"content": "", "error": f"AI API 返回错误（HTTP {status_code}）"}
    except KeyError:
        return {"content": "", "error": "AI API 返回数据格式异常"}
    except Exception as e:
        return {"content": "", "error": f"调用 AI API 失败：{str(e)}"}


def enhance_text(text, ai_config):
    """AI 增强纯文本，自动添加 Markdown 结构标记。

    Args:
        text (str): 原始纯文本
        ai_config (dict): AI 配置，含 url/api_key/model

    Returns:
        dict: {"enhanced": str, "error": str}
    """
    # 检查 ai_config 是否为空或缺少 api_key
    if not ai_config:
        return {"enhanced": "", "error": "未配置 AI 服务，请在设置中填写 API Key"}

    api_key = ai_config.get("api_key", "")
    if not api_key:
        return {"enhanced": "", "error": "未配置 AI 服务，请在设置中填写 API Key"}

    # 构建提示词
    prompt = build_enhance_prompt(text)

    # 调用 AI API
    result = call_ai_api(prompt, ai_config)

    if result["error"]:
        return {"enhanced": "", "error": result["error"]}

    return {"enhanced": result["content"], "error": ""}


def test_ai_connection(ai_config):
    """测试 AI API 连接是否正常。

    发送一个简单的请求来验证 API Key 和 URL 是否有效。

    Args:
        ai_config (dict): AI 配置，含 url/api_key/model

    Returns:
        dict: {"success": bool, "error": str, "model": str}
    """
    if not ai_config or not ai_config.get("api_key"):
        return {"success": False, "error": "未配置 API Key", "model": ""}

    base_url = ai_config.get("url", "").rstrip("/")
    api_key = ai_config.get("api_key", "")
    model = ai_config.get("model", "")

    url = f"{base_url}/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Hi"}],
        "max_tokens": 5,
        "temperature": 0,
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        if response.status_code == 200:
            data = response.json()
            actual_model = data.get("model", model)
            return {"success": True, "error": "", "model": actual_model}
        else:
            try:
                err_data = response.json()
                err_msg = err_data.get("error", {}).get("message", f"HTTP {response.status_code}")
            except:
                err_msg = f"HTTP {response.status_code}"
            return {"success": False, "error": err_msg, "model": model}
    except requests.exceptions.Timeout:
        return {"success": False, "error": "连接超时（15秒）", "model": model}
    except requests.exceptions.ConnectionError:
        return {"success": False, "error": f"无法连接到 {base_url}", "model": model}
    except Exception as e:
        return {"success": False, "error": str(e), "model": model}


def generate_summary(content, ai_config):
    """AI 生成 120 字以内的文章摘要，用于公众号草稿箱的 digest 字段。

    Args:
        content (str): 文章内容（Markdown 或纯文本）
        ai_config (dict): AI 配置

    Returns:
        dict: {"summary": str, "error": str}
    """
    if not ai_config or not ai_config.get("api_key"):
        return {"summary": "", "error": "未配置 AI 服务，请在设置中填写 API Key"}

    prompt = f"""请为以下文章生成一段120字以内的摘要，要求：
1. 准确概括文章核心内容
2. 语言简洁有力，吸引读者点击
3. 不要使用引号包裹摘要
4. 只输出摘要文本，不要添加任何解释

---

{content[:3000]}"""

    result = call_ai_api(prompt, ai_config)
    if result["error"]:
        return {"summary": "", "error": result["error"]}

    summary = result["content"].strip().strip('"').strip("'")[:120]
    return {"summary": summary, "error": ""}


def generate_cover_svg(title, subtitle=""):
    """根据文章标题生成 SVG 格式的公众号封面图（2.35:1 比例）。

    生成一个渐变背景 + 标题文字的 SVG 封面，无需图片 API。

    Args:
        title (str): 文章标题
        subtitle (str): 副标题或摘要，可选

    Returns:
        dict: {"svg": str, "base64": str, "error": str}
    """
    # 预设渐变色方案
    gradients = [
        ("#667eea", "#764ba2"),  # 蓝紫
        ("#f093fb", "#f5576c"),  # 粉红
        ("#4facfe", "#00f2fe"),  # 天蓝
        ("#43e97b", "#38f9d7"),  # 绿松
        ("#fa709a", "#fee140"),  # 橙粉
        ("#a18cd1", "#fbc2eb"),  # 淡紫
        ("#fccb90", "#d57eeb"),  # 暖橙紫
        ("#e0c3fc", "#8ec5fc"),  # 薰衣草蓝
        ("#f5576c", "#ff6a00"),  # 红橙
        ("#0c3483", "#a2b6df"),  # 深蓝浅蓝
    ]

    color1, color2 = random.choice(gradients)

    # 截断标题（SVG 中中文宽度估算）
    display_title = title[:20] + "..." if len(title) > 20 else title
    display_subtitle = subtitle[:30] + "..." if len(subtitle) > 30 else subtitle

    # 计算标题字号
    title_len = len(display_title)
    if title_len <= 8:
        font_size = 52
    elif title_len <= 14:
        font_size = 40
    else:
        font_size = 32

    y_title = 180 if not display_subtitle else 160
    subtitle_part = ""
    if display_subtitle:
        subtitle_part = (
            f'<text x="450" y="220" text-anchor="middle" '
            f'font-family="PingFang SC,Microsoft YaHei,sans-serif" '
            f'font-size="18" fill="rgba(255,255,255,0.85)">{display_subtitle}</text>'
        )

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="900" height="383" viewBox="0 0 900 383">'
        f'<defs>'
        f'<linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">'
        f'<stop offset="0%" style="stop-color:{color1}"/>'
        f'<stop offset="100%" style="stop-color:{color2}"/>'
        f'</linearGradient>'
        f'<filter id="shadow" x="-5%" y="-5%" width="110%" height="110%">'
        f'<feDropShadow dx="0" dy="2" stdDeviation="4" flood-color="rgba(0,0,0,0.3)"/>'
        f'</filter>'
        f'</defs>'
        f'<rect width="900" height="383" fill="url(#bg)" rx="0"/>'
        f'<text x="450" y="{y_title}" text-anchor="middle" '
        f'font-family="PingFang SC,Microsoft YaHei,Noto Sans SC,sans-serif" '
        f'font-size="{font_size}" font-weight="bold" fill="white" filter="url(#shadow)">{display_title}</text>'
        f'{subtitle_part}'
        f'<text x="450" y="360" text-anchor="middle" '
        f'font-family="PingFang SC,Microsoft YaHei,sans-serif" '
        f'font-size="14" fill="rgba(255,255,255,0.5)">SuperSu · AI 排版</text>'
        f'</svg>'
    )

    svg_b64 = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
    data_uri = f"data:image/svg+xml;base64,{svg_b64}"

    return {"svg": svg, "base64": data_uri, "error": ""}
