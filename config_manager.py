"""配置管理模块：负责 config.json 的读写，支持多公众号账号 CRUD。"""

import json
import os
import threading
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
CONFIG_PATH = PROJECT_DIR / "config.json"
_ENV_PATH = PROJECT_DIR / ".env"


def _parse_env() -> dict:
    """读取 .env 文件，返回 key-value 字典（不依赖 python-dotenv）。"""
    env = {}
    if not _ENV_PATH.exists():
        return env
    with open(_ENV_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and value:
                env[key] = value
    return env


def _init_from_env() -> None:
    """从 .env 初始化 config.json（仅当 config.json 不存在时）。"""
    if CONFIG_PATH.exists():
        return
    env = _parse_env()
    if not env:
        return

    config = _deep_copy(DEFAULT_CONFIG)

    # AI 配置
    api_key = env.get("AI_API_KEY", env.get("DASHSCOPE_API_KEY", ""))
    ai_url = env.get("AI_URL", config["ai"]["url"])
    ai_model = env.get("AI_MODEL", config["ai"]["model"])
    ai_platform = env.get("AI_PLATFORM_ID", config["ai"]["platform_id"])
    ai_image_model = env.get("AI_IMAGE_MODEL", config["ai"].get("image_model", ""))
    config["ai"] = {
        "url": ai_url,
        "api_key": api_key,
        "model": ai_model,
        "image_model": ai_image_model,
        "platform_id": ai_platform,
    }

    # 公众号账号
    accounts = []
    index = 1
    while True:
        name = env.get(f"WECHAT_ACCOUNT_{index}_NAME", "")
        app_id = env.get(f"WECHAT_ACCOUNT_{index}_APPID", "")
        app_secret = env.get(f"WECHAT_ACCOUNT_{index}_APPSECRET", "")
        if not name or not app_id or not app_secret:
            break
        accounts.append({
            "id": f"account_{index}",
            "name": name,
            "app_id": app_id,
            "app_secret": app_secret,
            "author": name,
            "avatar_color": AVATAR_COLORS[(index - 1) % len(AVATAR_COLORS)],
            "is_default": index == 1,
        })
        index += 1

    if accounts:
        config["accounts"] = accounts

    save_config(config)


AVATAR_COLORS = ["#07c160", "#576b95", "#FA9D3B", "#5B9BD5", "#ED7D31", "#70AD47"]

AI_PLATFORMS = [
    {"id": "openrouter", "name": "OpenRouter", "url": "https://openrouter.ai/api/v1", "models": ["anthropic/claude-sonnet-4", "openai/gpt-4o", "google/gemini-2.0-flash", "deepseek/deepseek-chat"]},
    {"id": "openai", "name": "OpenAI", "url": "https://api.openai.com/v1", "models": ["gpt-4o", "gpt-4o-mini", "gpt-4.5-preview", "o3-mini"]},
    {"id": "claude", "name": "Claude (Anthropic)", "url": "https://api.anthropic.com/v1", "models": ["claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"]},
    {"id": "gemini", "name": "Google Gemini", "url": "https://generativelanguage.googleapis.com/v1beta/openai", "models": ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-2.5-pro"]},
    {"id": "deepseek", "name": "DeepSeek", "url": "https://api.deepseek.com/v1", "models": ["deepseek-chat", "deepseek-reasoner"]},
    {"id": "zhipu", "name": "智谱 AI (GLM)", "url": "https://open.bigmodel.cn/api/paas/v4", "models": ["glm-4-plus", "glm-4-flash", "glm-4-air"]},
    {"id": "moonshot", "name": "Moonshot (Kimi)", "url": "https://api.moonshot.cn/v1", "models": ["moonshot-v1-8k", "moonshot-v1-32k", "moonshot-v1-128k"]},
    {"id": "qwen", "name": "通义千问", "url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "models": ["qwen-turbo", "qwen-plus", "qwen-max", "qwen-long"]},
    {"id": "doubao", "name": "豆包 (字节跳动)", "url": "https://ark.cn-beijing.volces.com/api/v3", "models": ["doubao-pro-4k", "doubao-pro-32k", "doubao-pro-128k"]},
    {"id": "hunyuan", "name": "腾讯混元", "url": "https://api.hunyuan.cloud.tencent.com/v1", "models": ["hunyuan-lite", "hunyuan-standard", "hunyuan-pro"]},
    {"id": "spark", "name": "讯飞星火", "url": "https://spark-api-open.xf-yun.com/v1", "models": ["generalv3.5", "generalv3", "4.0Ultra"]},
    {"id": "siliconflow", "name": "硅基流动", "url": "https://api.siliconflow.cn/v1", "models": ["deepseek-ai/DeepSeek-V3", "Qwen/Qwen2.5-72B-Instruct", "Pro/deepseek-ai/DeepSeek-R1"]},
    {"id": "baiLian", "name": "阿里云百炼", "url": "https://dashscope.aliyuncs.com/compatible-mode/v1", "models": ["qwen-turbo", "qwen-plus", "qwen-max"]},
    {"id": "yi", "name": "零一万物 (Yi)", "url": "https://api.lingyiwanwu.com/v1", "models": ["yi-lightning", "yi-large", "yi-medium"]},
    {"id": "minimax", "name": "MiniMax", "url": "https://api.minimax.chat/v1", "models": ["MiniMax-Text-01", "abab6.5s-chat"]},
    {"id": "tokenpool", "name": "TokenPool 中转站", "url": "https://api.tokenpool.co/v1", "models": ["gpt-4o", "gpt-4o-mini", "deepseek-chat", "gemini-2.5-flash"], "image_model": "gpt-image-2"},
    {"id": "custom", "name": "自定义平台", "url": "", "models": []},
]

DEFAULT_CONFIG = {
    "output_dir": "output",
    "vault_root": "",
    "image_search_paths": [],
    "settings": {
        "default_theme": "newspaper",
        "auto_open_browser": True,
    },
    "wechat": {
        "app_id": "",
        "app_secret": "",
        "author": "",
    },
    "cover": {
        "output_dir": "covers",
        "image_generation_script": "",
    },
    "ai": {
        "url": "https://openrouter.ai/api/v1",
        "api_key": "",
        "model": "anthropic/claude-sonnet-4",
        "image_model": "",
        "platform_id": "openrouter",
    },
    "accounts": [],
}

_lock = threading.Lock()


def load_config() -> dict:
    """读取 config.json，返回 dict。文件不存在时返回默认配置。"""
    with _lock:
        if not CONFIG_PATH.exists():
            return _deep_copy(DEFAULT_CONFIG)
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        # 确保缺少的字段有默认值
        for key, value in DEFAULT_CONFIG.items():
            if key not in data:
                data[key] = _deep_copy(value)
        return data


def save_config(config: dict) -> None:
    """保存 config 到 config.json。"""
    with _lock:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)


def get_accounts() -> list:
    """获取所有公众号账号列表。"""
    return load_config().get("accounts", [])


def add_account(name: str, app_id: str, app_secret: str, author: str,
                avatar_color: str | None = None) -> dict:
    """添加新账号，自动生成 id，第一个账号自动设为默认。

    Returns:
        新创建的账号 dict。
    """
    config = load_config()
    accounts = config.get("accounts", [])

    # 自动生成 id
    existing_ids = {acc["id"] for acc in accounts}
    index = 1
    while f"account_{index}" in existing_ids:
        index += 1
    account_id = f"account_{index}"

    # 第一个账号自动设为默认
    is_default = len(accounts) == 0

    # avatar_color 从色板循环选取
    if avatar_color is None:
        avatar_color = AVATAR_COLORS[(len(accounts)) % len(AVATAR_COLORS)]

    account = {
        "id": account_id,
        "name": name,
        "app_id": app_id,
        "app_secret": app_secret,
        "author": author,
        "avatar_color": avatar_color,
        "is_default": is_default,
    }

    accounts.append(account)
    config["accounts"] = accounts
    save_config(config)
    return account


def update_account(account_id: str, **kwargs) -> dict | None:
    """更新账号信息，返回更新后的账号 dict，未找到返回 None。"""
    config = load_config()
    accounts = config.get("accounts", [])

    for acc in accounts:
        if acc["id"] == account_id:
            for key, value in kwargs.items():
                if key in acc and key != "id":
                    acc[key] = value
            save_config(config)
            return acc
    return None


def delete_account(account_id: str) -> bool:
    """删除账号，返回是否成功。"""
    config = load_config()
    accounts = config.get("accounts", [])

    original_len = len(accounts)
    accounts = [acc for acc in accounts if acc["id"] != account_id]

    if len(accounts) == original_len:
        return False

    # 如果删除的是默认账号，将第一个账号设为默认
    was_default = any(acc["id"] == account_id and acc.get("is_default") for acc in config["accounts"])
    if was_default and accounts:
        accounts[0]["is_default"] = True

    config["accounts"] = accounts
    save_config(config)
    return True


def set_default_account(account_id: str) -> bool:
    """设置默认账号（其他账号 is_default 设为 false），返回是否成功。"""
    config = load_config()
    accounts = config.get("accounts", [])

    found = False
    for acc in accounts:
        if acc["id"] == account_id:
            acc["is_default"] = True
            found = True
        else:
            acc["is_default"] = False

    if not found:
        return False

    save_config(config)
    return True


def get_account(account_id: str) -> dict | None:
    """获取单个账号信息，未找到返回 None。"""
    accounts = get_accounts()
    for acc in accounts:
        if acc["id"] == account_id:
            return acc
    return None


def get_default_account() -> dict | None:
    """获取默认账号，没有返回 None。"""
    accounts = get_accounts()
    for acc in accounts:
        if acc.get("is_default"):
            return acc
    # 没有默认账号时返回第一个
    return accounts[0] if accounts else None


def get_ai_platforms() -> list:
    """获取 AI 平台预设列表"""
    return AI_PLATFORMS


def get_ai_config() -> dict:
    """获取 AI 配置。"""
    config = load_config()
    ai = config.get("ai", _deep_copy(DEFAULT_CONFIG["ai"]))
    if "platform_id" not in ai:
        ai["platform_id"] = ""
    if "image_model" not in ai:
        ai["image_model"] = ""
    return ai


def save_ai_config(url: str | None = None, api_key: str | None = None,
                   model: str | None = None, platform_id: str | None = None,
                   image_model: str | None = None) -> None:
    """保存 AI 配置，仅更新传入的非 None 字段。"""
    config = load_config()
    ai = config.get("ai", {})
    if platform_id is not None:
        ai["platform_id"] = platform_id
        # 根据 platform_id 自动填充 url 和 image_model
        for p in AI_PLATFORMS:
            if p["id"] == platform_id:
                if p["url"]:
                    ai["url"] = p["url"]
                if p.get("image_model"):
                    ai["image_model"] = p["image_model"]
                break
    if url is not None:
        ai["url"] = url
    if api_key is not None:
        ai["api_key"] = api_key
    if model is not None:
        ai["model"] = model
    if image_model is not None:
        ai["image_model"] = image_model
    if "image_model" not in ai:
        ai["image_model"] = ""
    config["ai"] = ai
    save_config(config)


def mask_app_id(app_id: str) -> str:
    """脱敏显示 AppID，如 "wx1234567890" → "wx1***890"。

    - 长度 <= 5：保留首尾各 1 位，中间用 *** 替代
    - 长度 > 5：保留前 3 位和后 3 位，中间用 *** 替代
    - 空字符串直接返回
    """
    if not app_id:
        return ""
    if len(app_id) <= 5:
        return app_id[0] + "***" + app_id[-1]
    return app_id[:3] + "***" + app_id[-3:]


def _deep_copy(d: dict) -> dict:
    """简单的深拷贝，用于默认配置。"""
    return json.loads(json.dumps(d))


# 模块加载时自动从 .env 初始化 config.json
_init_from_env()
