# WechatCA 项目开发规范

## 技术栈

- 后端：Flask (Python), Jinja2 模板
- 前端：原生 HTML/CSS/JS，无框架
- AI：OpenAI 兼容 API (chat/completions + images/generations)
- 排版引擎：xiaohu-wechat-format (git submodule)
- 微信接口：公众号 access_token / 草稿箱 / 素材管理

## 架构

```
app.py (路由层) → formatter.py (排版) / ai_enhancer.py (AI) / publisher.py (推送)
                  ↓                          ↓                        ↓
         xiaohu-wechat-format       OpenAI-compatible API        微信 API
```

- `config_manager.py`：所有配置读写，首次启动从 `.env` 初始化 `config.json`
- `ai_enhancer.py`：`image_model` 优先用于生图，回退 `model`
- `publisher.py`：TokenCache 全局单例，access_token 自动缓存/刷新

## 启动

```bash
pip install flask requests markdown
git clone https://github.com/xiaohuailabs/xiaohu-wechat-format.git
cp .env.example .env  # 编辑填入真实凭证
python app.py
```

## 不可提交

- `.env` / `config.json` — 含 API Key 和 AppSecret
- `__pycache__/` / `*.pyc`
- `xiaohu-wechat-format/` — 需用户自行克隆

## 代码风格

- Python：类型标注用 `str | None`（3.10+ 语法）
- 前端：原生 JS，无框架依赖，玻璃拟态 UI
- 注释：只写 WHY 不写 WHAT
- API 返回：统一 `{"success": bool, "error": str, ...}`
