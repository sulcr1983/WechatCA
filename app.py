"""SuperSu 公众号文章AI排版推送助手 Flask Web 应用"""

import threading
import webbrowser

from flask import Flask, jsonify, render_template, request

import config_manager
import formatter
import publisher
import ai_enhancer
import tasks

app = Flask(__name__)


# ── 页面路由 ──────────────────────────────────────────────────────────

@app.route("/")
def index():
    """主编辑页"""
    return render_template("index.html")


# ── 排版 API ─────────────────────────────────────────────────────────

@app.route("/api/format", methods=["POST"])
def api_format():
    """排版文章，参数: {content, theme}，返回 {html, title, word_count}"""
    data = request.get_json(force=True)
    content = data.get("content", "")
    theme = data.get("theme", "newspaper")

    if not content.strip():
        return jsonify({"html": "", "title": "", "word_count": 0})

    try:
        result = formatter.format_article(content, theme)
        return jsonify({
            "html": result.get("html", ""),
            "title": result.get("title", ""),
            "word_count": result.get("word_count", 0),
        })
    except Exception as e:
        return jsonify({"html": "", "title": "", "word_count": 0, "error": str(e)})


@app.route("/api/enhance", methods=["POST"])
def api_enhance():
    """AI 增强文章，参数: {content}，返回 {enhanced, error}"""
    data = request.get_json(force=True)
    content = data.get("content", "")

    if not content.strip():
        return jsonify({"enhanced": "", "error": "内容为空"})

    ai_config = config_manager.get_ai_config()
    result = ai_enhancer.enhance_text(content, ai_config)
    return jsonify(result)


@app.route("/api/themes")
def api_themes():
    """获取主题列表"""
    themes = formatter.get_available_themes()
    return jsonify(themes)


# ── 公众号管理 API ───────────────────────────────────────────────────

@app.route("/api/accounts")
def api_get_accounts():
    """获取公众号列表"""
    accounts = config_manager.get_accounts()
    # 脱敏 app_secret，对 app_id 做脱敏显示
    safe_accounts = []
    for acc in accounts:
        safe_accounts.append({
            "id": acc["id"],
            "name": acc["name"],
            "app_id": acc["app_id"],
            "app_id_masked": config_manager.mask_app_id(acc.get("app_id", "")),
            "author": acc.get("author", ""),
            "avatar_color": acc.get("avatar_color", "#07c160"),
            "is_default": acc.get("is_default", False),
        })
    return jsonify(safe_accounts)


@app.route("/api/accounts", methods=["POST"])
def api_add_account():
    """添加公众号，参数: {name, app_id, app_secret, author}"""
    data = request.get_json(force=True)
    name = data.get("name", "").strip()
    app_id = data.get("app_id", "").strip()
    app_secret = data.get("app_secret", "").strip()
    author = data.get("author", "").strip()

    if not name or not app_id or not app_secret:
        return jsonify({"error": "名称、AppID、AppSecret 不能为空"}), 400

    account = config_manager.add_account(name, app_id, app_secret, author)
    return jsonify({
        "id": account["id"],
        "name": account["name"],
        "app_id_masked": config_manager.mask_app_id(account["app_id"]),
        "author": account["author"],
        "avatar_color": account["avatar_color"],
        "is_default": account["is_default"],
    })


@app.route("/api/accounts/<account_id>", methods=["PUT"])
def api_update_account(account_id):
    """更新公众号"""
    data = request.get_json(force=True)
    kwargs = {}
    for key in ("name", "app_id", "app_secret", "author"):
        if key in data:
            kwargs[key] = data[key].strip() if isinstance(data[key], str) else data[key]

    account = config_manager.update_account(account_id, **kwargs)
    if account is None:
        return jsonify({"error": "账号不存在"}), 404

    return jsonify({
        "id": account["id"],
        "name": account["name"],
        "app_id_masked": config_manager.mask_app_id(account["app_id"]),
        "author": account.get("author", ""),
        "avatar_color": account.get("avatar_color", "#07c160"),
        "is_default": account.get("is_default", False),
    })


@app.route("/api/accounts/<account_id>", methods=["DELETE"])
def api_delete_account(account_id):
    """删除公众号"""
    success = config_manager.delete_account(account_id)
    if not success:
        return jsonify({"error": "账号不存在"}), 404
    return jsonify({"success": True})


@app.route("/api/accounts/<account_id>/default", methods=["POST"])
def api_set_default_account(account_id):
    """设置默认公众号"""
    success = config_manager.set_default_account(account_id)
    if not success:
        return jsonify({"error": "账号不存在"}), 404
    return jsonify({"success": True})


# ── AI 配置 API ──────────────────────────────────────────────────────

@app.route("/api/ai-config")
def api_get_ai_config():
    """获取 AI 配置"""
    ai_config = config_manager.get_ai_config()
    # 脱敏 api_key
    api_key = ai_config.get("api_key", "")
    if api_key:
        masked = api_key[:4] + "***" + api_key[-4:] if len(api_key) > 8 else "***"
    else:
        masked = ""
    return jsonify({
        "url": ai_config.get("url", ""),
        "api_key_masked": masked,
        "api_key_set": bool(api_key),
        "model": ai_config.get("model", ""),
    })


@app.route("/api/ai-config", methods=["POST"])
def api_save_ai_config():
    """保存 AI 配置，参数: {url, api_key, model, platform_id}"""
    data = request.get_json(force=True)
    url = data.get("url")
    api_key = data.get("api_key")
    model = data.get("model")
    platform_id = data.get("platform_id")

    # 如果 api_key 是 "***" 或空字符串，表示用户未修改，不更新
    if api_key and ("*" in api_key or not api_key.strip()):
        api_key = None

    config_manager.save_ai_config(url=url, api_key=api_key, model=model, platform_id=platform_id)
    return jsonify({"success": True})


@app.route("/api/ai-platforms")
def api_ai_platforms():
    """获取 AI 平台预设列表"""
    platforms = config_manager.get_ai_platforms()
    return jsonify(platforms)


@app.route("/api/test-ai", methods=["POST"])
def api_test_ai():
    """测试 AI API 连接，参数: {url, api_key, model}"""
    data = request.get_json(force=True)
    ai_config = {
        "url": data.get("url", ""),
        "api_key": data.get("api_key", ""),
        "model": data.get("model", ""),
    }
    result = ai_enhancer.test_ai_connection(ai_config)
    return jsonify(result)


@app.route("/api/generate-summary", methods=["POST"])
def api_generate_summary():
    """AI 生成文章摘要，参数: {content}"""
    data = request.get_json(force=True)
    content = data.get("content", "")
    if not content.strip():
        return jsonify({"summary": "", "error": "内容为空"})
    ai_config = config_manager.get_ai_config()
    result = ai_enhancer.generate_summary(content, ai_config)
    return jsonify(result)


@app.route("/api/generate-cover", methods=["POST"])
def api_generate_cover():
    """AI 生成公众号封面图，参数: {title, subtitle, content}"""
    data = request.get_json(force=True)
    title = data.get("title", "未命名文章")
    subtitle = data.get("subtitle", "")
    content = data.get("content", "")
    ai_config = config_manager.get_ai_config()
    result = ai_enhancer.generate_cover(title, subtitle, content, ai_config)
    return jsonify(result)


# ── 推送 API ─────────────────────────────────────────────────────────

@app.route("/api/publish", methods=["POST"])
def api_publish():
    """推送到公众号，参数: {account_id, html, title, cover_path, author, digest, cover_base64}"""
    data = request.get_json(force=True)
    account_id = data.get("account_id", "")
    html_content = data.get("html", "")
    title = data.get("title", "")
    cover_path = data.get("cover_path", "")
    author = data.get("author", "")
    digest = data.get("digest", "")
    cover_base64 = data.get("cover_base64", "")

    if not account_id:
        return jsonify({"success": False, "error": "未选择公众号"})

    account = config_manager.get_account(account_id)
    if not account:
        return jsonify({"success": False, "error": "公众号不存在"})

    result = publisher.publish_to_account(
        account, html_content, title,
        cover_path=cover_path or None,
        author=author,
        digest=digest,
        cover_base64=cover_base64,
    )
    return jsonify(result)


@app.route("/api/copy-html", methods=["POST"])
def api_copy_html():
    """返回排版后的 HTML（用于剪贴板复制）"""
    data = request.get_json(force=True)
    content = data.get("content", "")
    theme = data.get("theme", "newspaper")

    if not content.strip():
        return jsonify({"html": ""})

    try:
        result = formatter.format_article(content, theme)
        return jsonify({"html": result.get("html", "")})
    except Exception as e:
        return jsonify({"html": "", "error": str(e)})


# ── 异步任务 API（后台执行长耗时操作）────────────────────────────────

@app.route("/api/async/generate-cover", methods=["POST"])
def api_async_generate_cover():
    """异步生成封面图，立即返回 task_id，前端轮询 /api/task/<task_id>"""
    data = request.get_json(force=True)
    title = data.get("title", "未命名文章")
    subtitle = data.get("subtitle", "")
    content = data.get("content", "")
    ai_config = config_manager.get_ai_config()

    task_id = tasks.submit(ai_enhancer.generate_cover, title, subtitle, content, ai_config)
    return jsonify({"task_id": task_id})


@app.route("/api/async/publish", methods=["POST"])
def api_async_publish():
    """异步推送到公众号，立即返回 task_id"""
    data = request.get_json(force=True)
    account_id = data.get("account_id", "")
    html_content = data.get("html", "")
    title = data.get("title", "")
    cover_path = data.get("cover_path", "")
    author = data.get("author", "")
    digest = data.get("digest", "")
    cover_base64 = data.get("cover_base64", "")

    if not account_id:
        return jsonify({"task_id": "", "error": "未选择公众号"})

    account = config_manager.get_account(account_id)
    if not account:
        return jsonify({"task_id": "", "error": "公众号不存在"})

    task_id = tasks.submit(
        publisher.publish_to_account,
        account, html_content, title,
        cover_path=cover_path or None,
        author=author, digest=digest,
        cover_base64=cover_base64,
    )
    return jsonify({"task_id": task_id})


@app.route("/api/task/<task_id>")
def api_task_status(task_id):
    """轮询任务状态，返回 {status, result, error}"""
    t = tasks.get(task_id)
    if t is None:
        return jsonify({"status": "not_found", "result": None, "error": "任务不存在或已过期"})
    return jsonify({
        "status": t["status"],
        "result": t["result"],
        "error": t["error"],
    })


# ── 启动逻辑 ─────────────────────────────────────────────────────────

def find_available_port(start=5000, end=5010):
    """自动检测可用端口"""
    import socket
    for port in range(start, end + 1):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return port
        except OSError:
            continue
    return start  # 兜底返回起始端口


if __name__ == "__main__":
    port = find_available_port()
    url = f"http://127.0.0.1:{port}"
    # 延迟 1 秒后自动打开浏览器
    threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    print(f"公众号排版助手已启动: {url}")
    app.run(host="127.0.0.1", port=port, debug=False)
