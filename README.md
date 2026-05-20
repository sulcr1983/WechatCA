# WechatCA — 公众号文章 AI 排版推送助手

一键将 Markdown 文本自动排版、AI 增强、生成封面图，推送到微信公众号草稿箱。

## 功能

- **Markdown 排版**：33 个主题可选，实时预览
- **AI 增强**：自动添加标题层级、关键词加粗、段落优化
- **封面生成**：gpt-image-2 / 通义万相 文生图，标题大字居中
- **AI 摘要**：80-100 字自然推荐语，无套话
- **多账号管理**：支持多个公众号切换
- **一键推送**：直接推送到微信草稿箱

## 快速开始

```bash
# 1. 克隆
git clone https://github.com/sulcr1983/WechatCA.git
cd WechatCA

# 2. 安装依赖
pip install -r requirements.txt

# 3. 克隆排版引擎
git clone https://github.com/xiaohuailabs/xiaohu-wechat-format.git

# 4. 配置 .env（复制 .env.example 修改）
cp .env.example .env
# 编辑 .env 填入 API Key 和公众号 AppID/AppSecret

# 5. 启动
python app.py
```

浏览器自动打开 `http://127.0.0.1:5000`。

## .env 配置说明

```env
AI_API_KEY=sk-your-key          # AI API Key
AI_URL=https://api.tokenpool.co/v1  # API 地址
AI_MODEL=gpt-4o-mini            # 文本模型
AI_IMAGE_MODEL=gpt-image-2      # 生图模型
AI_PLATFORM_ID=tokenpool        # 平台 ID

WECHAT_ACCOUNT_1_NAME=公众号名称
WECHAT_ACCOUNT_1_APPID=wxAPPID
WECHAT_ACCOUNT_1_APPSECRET=appsecret
# 多个公众号依次递增编号
```

首次启动时自动从 `.env` 生成 `config.json`。

## 支持的 AI 平台

| 平台 | 文本 | 生图 |
|------|------|------|
| TokenPool 中转站 | gpt-4o / gpt-4o-mini / deepseek-chat | gpt-image-2 |
| 阿里云百炼 | qwen-plus / qwen-max | wanx2.1-t2i-turbo |
| OpenAI | gpt-4o | dall-e-3 |
| 其他 16 个平台 | 各平台模型 | 需平台支持 |

## 项目结构

```
WechatCA/
├── app.py               # Flask Web 应用
├── ai_enhancer.py       # AI 增强、封面生成、摘要
├── config_manager.py    # 配置管理（多账号 CRUD）
├── formatter.py         # 排版引擎封装
├── publisher.py         # 微信推送（token / 图片上传 / 草稿箱）
├── templates/
│   └── index.html       # 前端 UI
├── xiaohu-wechat-format/  # 排版引擎（需单独克隆）
├── .env.example         # 环境变量模板
└── requirements.txt
```

## 注意

- 微信推送需将服务器 IP 加入公众号后台 IP 白名单
- `config.json` 和 `.env` 含敏感信息，已在 `.gitignore` 中排除
- 首次启动确保 `.env` 已正确配置
