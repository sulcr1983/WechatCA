"""配置管理模块：使用 SQLite 存储配置和账号数据。

首次启动时自动从 .env 初始化数据库（如果账号表为空）。
公共 API 与之前兼容，调用者无需修改。
"""

from pathlib import Path

import database

PROJECT_DIR = Path(__file__).parent
_ENV_PATH = PROJECT_DIR / ".env"


def _parse_env() -> dict:
    """读取 .env 文件，返回 key-value 字典。"""
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
    """如果账号表为空，从 .env 初始化数据。"""
    accounts = database.get_accounts()
    if accounts:
        return

    env = _parse_env()
    if not env:
        return

    # AI 配置
    api_key = env.get("AI_API_KEY", env.get("DASHSCOPE_API_KEY", ""))
    ai_url = env.get("AI_URL", "")
    ai_model = env.get("AI_MODEL", "")
    ai_platform = env.get("AI_PLATFORM_ID", "")
    ai_image_model = env.get("AI_IMAGE_MODEL", "")
    database.save_ai_config(
        url=ai_url or None,
        api_key=api_key or None,
        model=ai_model or None,
        platform_id=ai_platform or None,
        image_model=ai_image_model or None,
    )

    # 公众号账号
    index = 1
    while True:
        name = env.get(f"WECHAT_ACCOUNT_{index}_NAME", "")
        app_id = env.get(f"WECHAT_ACCOUNT_{index}_APPID", "")
        app_secret = env.get(f"WECHAT_ACCOUNT_{index}_APPSECRET", "")
        if not name or not app_id or not app_secret:
            break
        database.add_account(name, app_id, app_secret, name)
        index += 1


# ── 账号 API（与旧版兼容）─────────────────────────────────────────────

def get_accounts() -> list:
    """获取所有公众号账号列表（脱敏 app_secret）。"""
    accounts = database.get_accounts()
    for acc in accounts:
        acc.pop("app_secret", None)
        acc.pop("sort_order", None)
    return accounts


def get_account(account_id: str) -> dict | None:
    """获取单个账号（含 app_secret，用于推送）。"""
    return database.get_account(account_id)


def add_account(name: str, app_id: str, app_secret: str, author: str,
                avatar_color: str | None = None) -> dict:
    return database.add_account(name, app_id, app_secret, author, avatar_color)


def update_account(account_id: str, **kwargs) -> dict | None:
    return database.update_account(account_id, **kwargs)


def delete_account(account_id: str) -> bool:
    return database.delete_account(account_id)


def set_default_account(account_id: str) -> bool:
    return database.set_default_account(account_id)


def get_default_account() -> dict | None:
    return database.get_default_account()


# ── AI 配置 API ───────────────────────────────────────────────────────

def get_ai_platforms() -> list:
    return database.AI_PLATFORMS


def get_ai_config() -> dict:
    return database.get_ai_config()


def save_ai_config(url: str | None = None, api_key: str | None = None,
                   model: str | None = None, platform_id: str | None = None,
                   image_model: str | None = None) -> None:
    database.save_ai_config(url=url, api_key=api_key, model=model,
                            platform_id=platform_id, image_model=image_model)


# ── 工具函数 ──────────────────────────────────────────────────────────

def mask_app_id(app_id: str) -> str:
    return database.mask_app_id(app_id)


# 模块加载时自动从 .env 初始化
_init_from_env()
