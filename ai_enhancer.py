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
    """AI 生成 100 字左右的公众号摘要。

    让 AI 像编辑写推荐语一样自由发挥，避免套话。

    Args:
        content (str): 文章内容
        ai_config (dict): AI 配置

    Returns:
        dict: {"summary": str, "error": str}
    """
    if not ai_config or not ai_config.get("api_key"):
        return {"summary": "", "error": "未配置 AI 服务，请在设置中填写 API Key"}

    prompt = f"""你是公众号的资深编辑。看完下面这篇文章后，写一段能吸引读者点击的摘要。

要求：
- 字数 80-100 字左右，2-4 句话
- 像跟朋友推荐一样自然，不要端着
- 可以抛出文章中最戳人的一个细节、一个悬念、或一句有共鸣的感受
- 禁止使用"本文介绍了""总而言之""通过分析""通过""让我们""综上所述"等套话

只写摘要本身，不要加任何解释或标题。

文章内容：
{content[:3000]}"""

    result = call_ai_api(prompt, ai_config)
    if result["error"]:
        return {"summary": "", "error": result["error"]}

    summary = result["content"].strip().strip('"').strip("'").strip('\u201c').strip('\u201d')[:120]
    return {"summary": summary, "error": ""}


def _escape_xml(text):
    """转义 XML 特殊字符，防止 SVG 解析失败。"""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def generate_cover(title, subtitle, content, ai_config):
    """通过 AI 生成公众号封面图（PNG 格式）。

    流程：
    1. 用文本 AI 根据文章内容生成封面背景的描述 prompt
    2. 调用 AI 图片生成 API 生成背景图
    3. 用 Pillow 在背景图上叠加中文标题

    Args:
        title (str): 文章标题
        subtitle (str): 副标题或摘要
        content (str): 文章全文
        ai_config (dict): AI 配置

    Returns:
        dict: {"base64": str, "error": str}
            base64 为 PNG 的纯 base64 字符串
    """
    if not ai_config or not ai_config.get("api_key"):
        return _generate_cover_png_fallback(title, subtitle)

    base_url = ai_config.get("url", "").rstrip("/")
    api_key = ai_config.get("api_key", "")
    model = ai_config.get("model", "")

    # Step 1: 用文本 AI 生成封面背景的 prompt
    prompt_result = call_ai_api(
        f"""You are a professional graphic designer. Based on the following article, describe a background image for a WeChat public account cover (landscape, 2.35:1 aspect ratio).

Requirements:
- Return ONLY an English prompt for AI image generation, no explanation
- The image should be a clean, professional background with negative space for text overlay
- Include color scheme, visual style, and mood suggestions
- NO text or characters in the image
- Suitable for a WeChat article cover about: {title}

Article content:
{content[:1500]}

Return only the image generation prompt.""",
        ai_config
    )

    if prompt_result["error"]:
        return _generate_cover_png_fallback(title, subtitle)

    image_prompt = prompt_result["content"].strip()

    # Step 2: 调用图片生成 API
    headers = {"Authorization": f"Bearer {api_key}"}
    img_payload = {
        "model": model,
        "prompt": image_prompt,
        "size": "1792x1024",
        "n": 1,
    }

    image_endpoints = [
        "/images/generations",
        "/v1/images/generations",
    ]

    bg_image = None
    for endpoint in image_endpoints:
        url = f"{base_url}{endpoint}"
        try:
            response = requests.post(url, json=img_payload, headers=headers, timeout=120)
            response.raise_for_status()
            data = response.json()

            if "data" in data and len(data["data"]) > 0:
                img_data = data["data"][0]
                if "b64_json" in img_data:
                    bg_image = base64.b64decode(img_data["b64_json"])
                    break
                elif "url" in img_data:
                    img_resp = requests.get(img_data["url"], timeout=30)
                    img_resp.raise_for_status()
                    bg_image = img_resp.content
                    break
        except Exception:
            continue

    if bg_image is None:
        return _generate_cover_png_fallback(title, subtitle)

    # Step 3: 用 Pillow 在 AI 生成的背景上叠加中文标题
    return _overlay_title_on_image(bg_image, title, subtitle)


def _overlay_title_on_image(image_data, title, subtitle=""):
    """在图片上叠加中文标题文字。"""
    from PIL import Image, ImageDraw, ImageFont
    import io

    bg = Image.open(io.BytesIO(image_data)).convert("RGB")
    # 缩放到封面比例
    target_width, target_height = 900, 383
    bg = bg.resize((target_width, target_height), Image.Resampling.LANCZOS)

    draw = ImageDraw.Draw(bg)

    # 加一层半透明遮罩让文字更清晰
    overlay = Image.new("RGBA", (target_width, target_height), (0, 0, 0, 60))
    bg = bg.convert("RGBA")
    bg = Image.alpha_composite(bg, overlay).convert("RGB")
    draw = ImageDraw.Draw(bg)

    display_title = title[:30] + "..." if len(title) > 30 else title
    title_len = len(display_title)
    if title_len <= 8:
        title_size = 48
    elif title_len <= 14:
        title_size = 38
    else:
        title_size = 30

    # 加载字体
    font_paths = [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
    ]
    title_font = None
    subtitle_font = None
    brand_font = None

    for fp in font_paths:
        try:
            title_font = ImageFont.truetype(fp, title_size)
            subtitle_font = ImageFont.truetype(fp, 16)
            brand_font = ImageFont.truetype(fp, 13)
            break
        except (IOError, OSError):
            continue

    if title_font is None:
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
        brand_font = ImageFont.load_default()

    # 绘制标题（白色，居中）
    draw.text((target_width // 2, 160), display_title, fill=(255, 255, 255), font=title_font, anchor="mm")

    if subtitle:
        display_subtitle = subtitle[:50] + "..." if len(subtitle) > 50 else subtitle
        draw.text((target_width // 2, 210), display_subtitle, fill=(230, 230, 230), font=subtitle_font, anchor="mm")

    draw.text((target_width // 2, target_height - 20), "SuperSu AI 排版", fill=(200, 200, 200), font=brand_font, anchor="mm")

    buffer = io.BytesIO()
    bg.save(buffer, format="PNG", quality=95)
    png_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return {"base64": png_b64, "error": ""}


def _generate_cover_png_fallback(title, subtitle=""):
    """降级方案：使用 Pillow 生成简单渐变封面。"""
    from PIL import Image, ImageDraw, ImageFont

    width, height = 900, 383
    gradients = [
        ((102, 126, 234), (118, 75, 162)),   # 蓝紫
        ((240, 147, 251), (245, 87, 108)),    # 粉红
        ((79, 172, 254), (0, 242, 254)),      # 天蓝
        ((67, 233, 123), (56, 249, 215)),     # 绿松
        ((250, 112, 154), (254, 225, 64)),    # 橙粉
        ((161, 140, 209), (251, 194, 235)),   # 淡紫
        ((252, 203, 144), (213, 126, 235)),   # 暖橙紫
        ((224, 195, 252), (142, 197, 252)),   # 薰衣草蓝
        ((245, 87, 108), (255, 106, 0)),      # 红橙
        ((12, 52, 131), (162, 182, 223)),     # 深蓝浅蓝
    ]

    color1, color2 = random.choice(gradients)

    # 创建渐变背景
    img = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(img)
    for y in range(height):
        ratio = y / height
        r = int(color1[0] + (color2[0] - color1[0]) * ratio)
        g = int(color1[1] + (color2[1] - color1[1]) * ratio)
        b = int(color1[2] + (color2[2] - color1[2]) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))

    # 尝试加载字体
    font_paths = [
        "C:/Windows/Fonts/msyh.ttc",       # 微软雅黑
        "C:/Windows/Fonts/simhei.ttf",     # 黑体
        "C:/Windows/Fonts/simsun.ttc",     # 宋体
        "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
    ]
    
    display_title = title[:30] + "..." if len(title) > 30 else title
    display_subtitle = subtitle[:50] + "..." if len(subtitle) > 50 else subtitle

    # 根据标题长度计算字号
    title_len = len(display_title)
    if title_len <= 8:
        title_size = 52
    elif title_len <= 14:
        title_size = 40
    else:
        title_size = 32

    # 加载字体
    title_font = None
    subtitle_font = None
    brand_font = None
    
    for font_path in font_paths:
        try:
            title_font = ImageFont.truetype(font_path, title_size)
            subtitle_font = ImageFont.truetype(font_path, 18)
            brand_font = ImageFont.truetype(font_path, 14)
            break
        except (IOError, OSError):
            continue
    
    if title_font is None:
        title_font = ImageFont.load_default()
        subtitle_font = ImageFont.load_default()
        brand_font = ImageFont.load_default()

    # 计算文字位置（居中）
    if display_subtitle:
        y_title = 140
        y_subtitle = 200
    else:
        y_title = 170
        y_subtitle = None

    # 绘制标题（白色，加粗效果通过字体选择实现）
    draw.text((width // 2, y_title), display_title, fill=(255, 255, 255), font=title_font, anchor="mm")

    # 绘制副标题
    if y_subtitle and display_subtitle:
        # 半透明白色（Pillow 不支持 alpha，用浅灰代替）
        draw.text((width // 2, y_subtitle), display_subtitle, fill=(220, 220, 220), font=subtitle_font, anchor="mm")

    # 绘制底部品牌
    draw.text((width // 2, height - 25), "SuperSu AI 排版", fill=(200, 200, 200), font=brand_font, anchor="mm")

    # 转为 base64
    import io
    buffer = io.BytesIO()
    img.save(buffer, format="PNG", quality=95)
    png_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    # SVG 字段返回空字符串（不再需要）
    return {"svg": "", "base64": png_b64, "error": ""}


def _generate_cover_svg_fallback(title, subtitle=""):
    """Pillow 不可用时降级为 SVG 封面。"""
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

    # 转义 XML 特殊字符
    display_title = _escape_xml(display_title)
    display_subtitle = _escape_xml(display_subtitle)

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
        f'font-size="14" fill="rgba(255,255,255,0.5)">SuperSu AI 排版</text>'
        f'</svg>'
    )

    svg_b64 = base64.b64encode(svg.encode("utf-8")).decode("utf-8")

    return {"svg": svg, "base64": svg_b64, "error": ""}
