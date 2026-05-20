"""SQLite 存储层，替代 config.json。

首次启动时自动从 config.json 迁移数据到 SQLite。
线程安全：每个线程获取独立连接。
"""

import json
import sqlite3
import threading
from pathlib import Path

PROJECT_DIR = Path(__file__).parent
DB_PATH = PROJECT_DIR / "data.db"
CONFIG_JSON_PATH = PROJECT_DIR / "config.json"

_local = threading.local()

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


def _get_conn() -> sqlite3.Connection:
    """获取当前线程的数据库连接（自动创建）。"""
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        _local.conn = conn
    return conn


def init_db() -> None:
    """创建数据库表（如果不存在）并执行迁移。"""
    conn = _get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS accounts (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            app_id TEXT NOT NULL,
            app_secret TEXT NOT NULL,
            author TEXT DEFAULT '',
            avatar_color TEXT DEFAULT '#07c160',
            is_default INTEGER DEFAULT 0,
            sort_order INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS ai_config (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            url TEXT DEFAULT '',
            api_key TEXT DEFAULT '',
            model TEXT DEFAULT '',
            image_model TEXT DEFAULT '',
            platform_id TEXT DEFAULT ''
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)
    conn.commit()
    _migrate_from_json()


def _migrate_from_json() -> None:
    """如果 data.db 为空且 config.json 存在，自动迁移数据。"""
    conn = _get_conn()
    row = conn.execute("SELECT COUNT(*) as cnt FROM accounts").fetchone()
    if row["cnt"] > 0:
        return  # 已有数据，不覆盖

    if not CONFIG_JSON_PATH.exists():
        return

    try:
        with open(CONFIG_JSON_PATH, encoding="utf-8") as f:
            config = json.load(f)
    except (json.JSONDecodeError, OSError):
        return

    # 迁移 settings
    settings = config.get("settings", {})
    if settings:
        for k, v in settings.items():
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (k, str(v)),
            )

    # 迁移 AI 配置
    ai = config.get("ai", {})
    if ai:
        conn.execute(
            "INSERT OR REPLACE INTO ai_config (id, url, api_key, model, image_model, platform_id) "
            "VALUES (1, ?, ?, ?, ?, ?)",
            (
                ai.get("url", ""),
                ai.get("api_key", ""),
                ai.get("model", ""),
                ai.get("image_model", ""),
                ai.get("platform_id", ""),
            ),
        )

    # 迁移账号
    for i, acc in enumerate(config.get("accounts", [])):
        conn.execute(
            "INSERT OR REPLACE INTO accounts (id, name, app_id, app_secret, author, avatar_color, is_default, sort_order) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                acc["id"],
                acc["name"],
                acc["app_id"],
                acc["app_secret"],
                acc.get("author", acc["name"]),
                acc.get("avatar_color", AVATAR_COLORS[i % len(AVATAR_COLORS)]),
                1 if acc.get("is_default") else 0,
                i,
            ),
        )

    conn.commit()

    # 迁移成功后重命名旧文件
    try:
        CONFIG_JSON_PATH.rename(CONFIG_JSON_PATH.with_suffix(".json.bak"))
    except OSError:
        pass


# ── 账号 CRUD ──────────────────────────────────────────────────────────

def get_accounts() -> list[dict]:
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM accounts ORDER BY sort_order").fetchall()
    return [dict(r) for r in rows]


def get_account(account_id: str) -> dict | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
    return dict(row) if row else None


def add_account(name: str, app_id: str, app_secret: str, author: str,
                avatar_color: str | None = None) -> dict:
    conn = _get_conn()
    # 生成 id
    rows = conn.execute("SELECT id FROM accounts").fetchall()
    existing_ids = {r["id"] for r in rows}
    index = 1
    while f"account_{index}" in existing_ids:
        index += 1
    account_id = f"account_{index}"

    is_default = len(rows) == 0
    if avatar_color is None:
        avatar_color = AVATAR_COLORS[len(rows) % len(AVATAR_COLORS)]

    conn.execute(
        "INSERT INTO accounts (id, name, app_id, app_secret, author, avatar_color, is_default, sort_order) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (account_id, name, app_id, app_secret, author, avatar_color, 1 if is_default else 0, len(rows)),
    )
    conn.commit()
    return dict(conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone())


def update_account(account_id: str, **kwargs) -> dict | None:
    conn = _get_conn()
    existing = conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone()
    if not existing:
        return None

    allowed = {"name", "app_id", "app_secret", "author", "avatar_color"}
    for key, value in kwargs.items():
        if key in allowed:
            conn.execute(f"UPDATE accounts SET {key} = ? WHERE id = ?", (value, account_id))
    conn.commit()
    return dict(conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,)).fetchone())


def delete_account(account_id: str) -> bool:
    conn = _get_conn()
    row = conn.execute("SELECT is_default FROM accounts WHERE id = ?", (account_id,)).fetchone()
    if not row:
        return False
    was_default = row["is_default"]
    conn.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
    # 如果删除的是默认账号，将第一个设为默认
    if was_default:
        first = conn.execute("SELECT id FROM accounts ORDER BY sort_order LIMIT 1").fetchone()
        if first:
            conn.execute("UPDATE accounts SET is_default = 1 WHERE id = ?", (first["id"],))
    conn.commit()
    return True


def set_default_account(account_id: str) -> bool:
    conn = _get_conn()
    existing = conn.execute("SELECT id FROM accounts WHERE id = ?", (account_id,)).fetchone()
    if not existing:
        return False
    conn.execute("UPDATE accounts SET is_default = 0")
    conn.execute("UPDATE accounts SET is_default = 1 WHERE id = ?", (account_id,))
    conn.commit()
    return True


def get_default_account() -> dict | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM accounts WHERE is_default = 1").fetchone()
    if not row:
        row = conn.execute("SELECT * FROM accounts ORDER BY sort_order LIMIT 1").fetchone()
    return dict(row) if row else None


# ── AI 配置 ────────────────────────────────────────────────────────────

def get_ai_config() -> dict:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM ai_config WHERE id = 1").fetchone()
    if not row:
        return {"url": "", "api_key": "", "model": "", "image_model": "", "platform_id": ""}
    return dict(row)


def save_ai_config(url: str | None = None, api_key: str | None = None,
                   model: str | None = None, platform_id: str | None = None,
                   image_model: str | None = None) -> None:
    conn = _get_conn()
    # Ensure row exists
    conn.execute("INSERT OR IGNORE INTO ai_config (id) VALUES (1)")

    if platform_id is not None:
        conn.execute("UPDATE ai_config SET platform_id = ? WHERE id = 1", (platform_id,))
        for p in AI_PLATFORMS:
            if p["id"] == platform_id:
                if p["url"]:
                    conn.execute("UPDATE ai_config SET url = ? WHERE id = 1", (p["url"],))
                if p.get("image_model"):
                    conn.execute("UPDATE ai_config SET image_model = ? WHERE id = 1", (p["image_model"],))
                break

    if url is not None:
        conn.execute("UPDATE ai_config SET url = ? WHERE id = 1", (url,))
    if api_key is not None:
        conn.execute("UPDATE ai_config SET api_key = ? WHERE id = 1", (api_key,))
    if model is not None:
        conn.execute("UPDATE ai_config SET model = ? WHERE id = 1", (model,))
    if image_model is not None:
        conn.execute("UPDATE ai_config SET image_model = ? WHERE id = 1", (image_model,))

    conn.commit()


# ── Settings ───────────────────────────────────────────────────────────

def get_setting(key: str, default: str = "") -> str:
    conn = _get_conn()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    conn = _get_conn()
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()


# ── 辅助函数 ───────────────────────────────────────────────────────────

def mask_app_id(app_id: str) -> str:
    if not app_id:
        return ""
    if len(app_id) <= 5:
        return app_id[0] + "***" + app_id[-1]
    return app_id[:3] + "***" + app_id[-3:]


# 模块加载时初始化
init_db()
