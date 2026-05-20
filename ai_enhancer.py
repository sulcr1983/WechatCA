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

1. 加标题：识别文章的逻辑段落和主题转换点，在转换处插入 ## 标题。标题从内容中提炼，不编造。三段内容不硬拆五个标题——尊重原文信息密度
2. 分段落：确保段落之间有空行分隔，长段落在语义转换处拆分
3. 加列表：识别并列/枚举性质的内容，加 - 或 1. 标记
4. 加强调：识别关键词、产品名、核心概念，加 **加粗**
5. 清理格式：去除多余空行、修正缩进、统一标点
6. 不改措辞：不调语序、不增删内容、不润色文字。用户写什么就是什么，只加结构标记

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
    """通过 AI 生成公众号封面图（PNG/JPG 格式）。

    直接将标题和全文交给 AI 生图，让 AI 生成带标题文字的封面图，
    背景根据文章内容风格生成。系统只负责拿到返回的图片推送到公众号。

    支持自动切换文生图模型：
    - 通义千问平台使用 DashScope 原生 API 调用 wan2.1-t2i-turbo
    - 其他平台使用 OpenAI 兼容接口

    Args:
        title (str): 文章标题
        subtitle (str): 副标题或摘要
        content (str): 文章全文
        ai_config (dict): AI 配置

    Returns:
        dict: {"base64": str, "error": str}
    """
    if not ai_config or not ai_config.get("api_key"):
        return {"base64": "", "error": "未配置 AI 服务"}

    base_url = ai_config.get("url", "").rstrip("/")
    api_key = ai_config.get("api_key", "")
    model = ai_config.get("image_model") or ai_config.get("model", "")
    platform_id = ai_config.get("platform_id", "")

    # 封面提示词：参照 xiaohu-wechat-format SKILL.md 的 Notion 插画风格模板
    topic = subtitle[:100] if subtitle else title
    image_prompt = (
        f"请根据提供的内容创建一张吸引眼球的公众号封面图，遵循以下规范：\n\n"
        f"视觉风格\n"
        f"- Notion插画风格，比例为 2.35:1（公众号封面标准尺寸）\n"
        f"- 色彩鲜明、对比强烈，确保在小尺寸预览时依然醒目\n"
        f"- 风格统一，避免写实元素，保持整体手绘质感\n\n"
        f"构图要求\n"
        f"- 主视觉元素居中或偏左（右侧预留标题区域）\n"
        f"- 添加 1-2 个简洁的卡通形象、图标或剪影，增强记忆点\n"
        f"- 大量留白，突出核心信息，避免画面拥挤\n\n"
        f"文字处理\n"
        f"- 标题文字大而醒目，控制在 8 字以内\n"
        f"- 可添加 1 行副标题或关键词标签\n"
        f"- 字体风格与手绘插画协调统一\n\n"
        f"吸引力法则\n"
        f"- 使用悬念、数字、痛点等钩子元素激发点击欲望\n"
        f"- 视觉元素夸张有反差\n"
        f"- 色彩搭配参考爆款封面：橙黄、蓝紫、红黑等高对比组合\n\n"
        f"语言\n"
        f"- 使用中文\n"
        f"- 画面内所有可读文字必须使用简体中文，英文只能作为点缀出现\n\n"
        f"内容主题：{topic}。{content[:200]}"
    )

    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    # 通义千问平台使用 DashScope 原生 API
    if platform_id in ("qwen", "baiLian"):
        return _generate_cover_dashscope(api_key, image_prompt)

    # 其他平台使用 OpenAI 兼容接口
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

    for endpoint in image_endpoints:
        url = f"{base_url}{endpoint}"
        try:
            response = requests.post(url, json=img_payload, headers=headers, timeout=120)
            response.raise_for_status()
            data = response.json()

            if "data" in data and len(data["data"]) > 0:
                img_data = data["data"][0]
                if "b64_json" in img_data:
                    return {"base64": img_data["b64_json"], "error": ""}
                if "url" in img_data:
                    img_resp = requests.get(img_data["url"], timeout=30)
                    img_resp.raise_for_status()
                    img_b64 = base64.b64encode(img_resp.content).decode("utf-8")
                    return {"base64": img_b64, "error": ""}

        except requests.exceptions.HTTPError as e:
            return {"base64": "", "error": f"图片生成失败: {e.response.status_code}"}
        except requests.exceptions.Timeout:
            return {"base64": "", "error": "图片生成超时（120秒），请重试"}
        except requests.exceptions.ConnectionError:
            return {"base64": "", "error": "无法连接到 AI 服务，请检查网络或 API 配置"}
        except Exception as e:
            return {"base64": "", "error": f"图片生成异常: {str(e)}"}

    return {"base64": "", "error": "图片生成不可用，当前 AI 模型不支持图片生成功能"}


def _generate_cover_dashscope(api_key, prompt):
    """通过 DashScope 原生 API 生成封面图（通义万相文生图）。

    Args:
        api_key (str): DashScope API Key
        prompt (str): 生图提示词

    Returns:
        dict: {"base64": str, "error": str}
    """
    # DashScope 文生图异步接口
    url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }
    payload = {
        "model": "wanx2.1-t2i-turbo",
        "input": {"prompt": prompt},
        "parameters": {
            "size": "1024*1024",
            "n": 1,
        },
    }

    try:
        # 1. 提交异步任务
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        if "output" not in data or "task_id" not in data["output"]:
            return {"base64": "", "error": f"任务提交失败: {data.get('message', '未知错误')}"}

        task_id = data["output"]["task_id"]

        # 2. 轮询任务状态
        task_url = f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"
        task_headers = {"Authorization": f"Bearer {api_key}"}

        for _ in range(60):  # 最多轮询 60 次
            import time
            time.sleep(2)
            task_resp = requests.get(task_url, headers=task_headers, timeout=15)
            task_resp.raise_for_status()
            task_data = task_resp.json()

            task_status = task_data.get("output", {}).get("task_status", "")
            if task_status == "SUCCEEDED":
                # 获取图片 URL
                results = task_data.get("output", {}).get("results", [])
                if results and "url" in results[0]:
                    img_resp = requests.get(results[0]["url"], timeout=30)
                    img_resp.raise_for_status()
                    img_b64 = base64.b64encode(img_resp.content).decode("utf-8")
                    return {"base64": img_b64, "error": ""}
                return {"base64": "", "error": "未获取到图片 URL"}
            elif task_status == "FAILED":
                error_msg = task_data.get("output", {}).get("message", "任务失败")
                return {"base64": "", "error": f"图片生成失败: {error_msg}"}
            # PENDING / RUNNING 继续轮询

        return {"base64": "", "error": "图片生成超时（120秒），请重试"}

    except requests.exceptions.Timeout:
        return {"base64": "", "error": "图片生成超时，请重试"}
    except requests.exceptions.ConnectionError:
        return {"base64": "", "error": "无法连接到 DashScope 服务"}
    except Exception as e:
        return {"base64": "", "error": f"图片生成异常: {str(e)}"}


