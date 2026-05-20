"""微信公众号推送模块

封装公众号推送功能，支持多账号。提供 access_token 缓存管理、
图片上传、HTML 图片替换、草稿箱推送等完整流程。
"""

import html as html_module
import json
import os
import re
import tempfile
import threading
import time
from pathlib import Path

import requests


# ── access_token 缓存管理 ─────────────────────────────────────────────

class TokenCache:
    """access_token 缓存管理，每个账号独立缓存，线程安全。

    token 有效期 2 小时，过期自动刷新。
    用法:
        cache = TokenCache()
        token_info = cache.get("app_id_xxx", "app_secret_xxx")
        # token_info = {"token": "...", "expires_at": 1700000000.0}
    """

    def __init__(self):
        # {app_id: {"token": str, "expires_at": float, "app_secret": str}}
        self._cache: dict = {}
        self._lock = threading.Lock()

    def get(self, app_id: str, app_secret: str) -> dict:
        """获取缓存的 token，过期则自动刷新。

        参数:
            app_id: 公众号 app_id
            app_secret: 公众号 app_secret
        返回:
            dict: {"token": str, "expires_at": float}
        """
        with self._lock:
            entry = self._cache.get(app_id)
            # 缓存存在且未过期（提前 5 分钟视为过期，留出安全余量）
            if entry and entry["expires_at"] > time.time() + 300:
                return {"token": entry["token"], "expires_at": entry["expires_at"]}

        # 释放锁后再请求网络，避免长时间持锁
        token_info = get_access_token(app_id, app_secret)

        with self._lock:
            self._cache[app_id] = {
                "token": token_info["token"],
                "expires_at": token_info["expires_at"],
                "app_secret": app_secret,
            }

        return token_info

    def invalidate(self, app_id: str):
        """手动使某个账号的缓存失效。"""
        with self._lock:
            self._cache.pop(app_id, None)

    def clear(self):
        """清空所有缓存。"""
        with self._lock:
            self._cache.clear()


# 全局单例缓存
_token_cache = TokenCache()


# ── 微信 API 接口 ─────────────────────────────────────────────────────

def get_access_token(app_id: str, app_secret: str) -> dict:
    """获取微信 API access_token。

    参数:
        app_id: 公众号 app_id
        app_secret: 公众号 app_secret
    返回:
        dict: {"token": str, "expires_at": float}
    异常:
        RuntimeError: 获取失败时抛出，包含错误码和错误信息
    """
    url = (
        "https://api.weixin.qq.com/cgi-bin/token"
        f"?grant_type=client_credential&appid={app_id}&secret={app_secret}"
    )
    resp = requests.get(url, timeout=15)
    data = resp.json()

    if "access_token" in data:
        expires_in = data.get("expires_in", 7200)
        return {
            "token": data["access_token"],
            "expires_at": time.time() + expires_in,
        }

    # 错误处理
    errcode = data.get("errcode", -1)
    errmsg = data.get("errmsg", "未知错误")

    if errcode == 40164:
        raise RuntimeError(
            f"获取 access_token 失败 (errcode={errcode}): "
            f"IP 不在白名单中，请到公众号后台添加当前 IP。{errmsg}"
        )
    elif errcode in (40001, 40125):
        raise RuntimeError(
            f"获取 access_token 失败 (errcode={errcode}): "
            f"AppSecret 无效，请检查配置。{errmsg}"
        )
    else:
        raise RuntimeError(
            f"获取 access_token 失败 (errcode={errcode}: {errmsg})"
        )


def _get_content_type(image_path: str) -> str:
    """根据文件扩展名推断 Content-Type。"""
    ext = Path(image_path).suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
    }.get(ext, "image/jpeg")


def upload_content_image(token: str, image_path: str, max_retries: int = 3) -> str | None:
    """上传正文图片到微信 CDN。

    参数:
        token: access_token
        image_path: 本地图片文件路径
        max_retries: 最大重试次数
    返回:
        str: CDN URL，失败返回 None
    """
    url = f"https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token={token}"
    filename = os.path.basename(image_path)
    content_type = _get_content_type(image_path)

    for attempt in range(1, max_retries + 1):
        try:
            with open(image_path, "rb") as f:
                files = {"media": (filename, f, content_type)}
                resp = requests.post(url, files=files, timeout=30)

            data = resp.json()
            if "url" in data:
                return data["url"]
            else:
                print(f"  ✗ 上传正文图片失败 ({attempt}/{max_retries}) - {filename}: {data}")
        except Exception as e:
            print(f"  ✗ 上传正文图片异常 ({attempt}/{max_retries}) - {filename}: {e}")

        if attempt < max_retries:
            time.sleep(2 * attempt)  # 递增等待

    print(f"  ✗ 上传正文图片彻底失败 - {filename}")
    return None


def upload_thumb_image(token: str, image_path: str) -> str | None:
    """上传封面图到永久素材库。

    参数:
        token: access_token
        image_path: 本地图片文件路径
    返回:
        str: media_id，失败返回 None
    """
    url = (
        "https://api.weixin.qq.com/cgi-bin/material/add_material"
        f"?access_token={token}&type=image"
    )
    filename = os.path.basename(image_path)
    content_type = _get_content_type(image_path)

    with open(image_path, "rb") as f:
        files = {"media": (filename, f, content_type)}
        resp = requests.post(url, files=files, timeout=30)

    data = resp.json()
    if "media_id" in data:
        return data["media_id"]
    else:
        print(f"错误: 上传封面图失败 - {data}")
        return None


def push_draft(token: str, title: str, content: str, thumb_media_id: str, author: str = "", digest: str = "") -> str | None:
    """推送文章到草稿箱。

    参数:
        token: access_token
        title: 文章标题
        content: 文章 HTML 内容
        thumb_media_id: 封面图 media_id
        author: 作者名
    返回:
        str: 草稿 media_id，失败返回 None
    """
    url = f"https://api.weixin.qq.com/cgi-bin/draft/add?access_token={token}"

    data = {
        "articles": [
            {
                "title": title,
                "author": author,
                "digest": digest,
                "content": content,
                "content_source_url": "",
                "thumb_media_id": thumb_media_id,
                "need_open_comment": 0,
                "only_fans_can_comment": 0,
            }
        ]
    }

    # 必须用 ensure_ascii=False，否则中文被转义为 \uXXXX 导致微信计算标题长度错误
    body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    resp = requests.post(
        url, data=body,
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    result = resp.json()

    if "media_id" in result:
        return result["media_id"]
    else:
        errcode = result.get("errcode", "?")
        errmsg = result.get("errmsg", "未知错误")
        print(f"错误: 推送草稿箱失败 (errcode={errcode}: {errmsg})")
        return None


# ── 图片替换 ──────────────────────────────────────────────────────────

def _download_external_image(url: str) -> str | None:
    """下载外部图片到临时文件，返回本地路径。"""
    try:
        # 还原 HTML 实体（&amp; → &）
        url = html_module.unescape(url)
        resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()

        # 从 Content-Type 推断扩展名
        content_type = resp.headers.get("Content-Type", "")
        if "png" in content_type:
            ext = ".png"
        elif "gif" in content_type:
            ext = ".gif"
        elif "webp" in content_type:
            ext = ".webp"
        else:
            ext = ".jpg"

        tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
        tmp.write(resp.content)
        tmp.close()
        return tmp.name
    except Exception as e:
        print(f"  ✗ 下载外部图片失败: {url[:60]}... ({e})")
        return None


def replace_html_images(html: str, image_dir: str, token: str) -> str:
    """替换 HTML 中的本地图片和外部 URL 图片为微信 CDN URL。

    参数:
        html: 原始 HTML 内容
        image_dir: 本地图片目录路径
        token: access_token
    返回:
        str: 替换后的 HTML 内容
    """
    image_dir_path = Path(image_dir)

    def replace_src(match):
        src = match.group(1)

        # 已经是微信 CDN 的图片，跳过
        if "mmbiz.qpic.cn" in src:
            return match.group(0)

        # 外部 URL：先下载再上传
        if src.startswith("http://") or src.startswith("https://"):
            local_path = _download_external_image(src)
            if local_path:
                cdn_url = upload_content_image(token, local_path)
                os.unlink(local_path)  # 清理临时文件
                if cdn_url:
                    print(f"  ✓ 外部图片: {src[:60]}...")
                    return f'src="{cdn_url}"'
            print(f"  ✗ 外部图片替换失败: {src[:60]}...")
            return match.group(0)

        # 本地图片
        local_path = image_dir_path / src
        if not local_path.exists():
            # 尝试直接用文件名在 image_dir 下查找
            local_path = image_dir_path / os.path.basename(src)

        if local_path.exists():
            cdn_url = upload_content_image(token, str(local_path))
            if cdn_url:
                print(f"  ✓ {os.path.basename(src)}")
                return f'src="{cdn_url}"'
            else:
                print(f"  ✗ 上传失败: {src}")
                return match.group(0)
        else:
            print(f"  ✗ 未找到本地图片: {src}")
            return match.group(0)

    html = re.sub(r'src="([^"]+)"', replace_src, html)
    return html


# ── 完整推送流程 ──────────────────────────────────────────────────────

def publish_to_account(
    account: dict,
    html_content: str,
    title: str,
    cover_path: str | None = None,
    author: str = "",
    digest: str = "",
    cover_base64: str = "",
) -> dict:
    """完整的推送流程：获取 token → 替换图片 → 上传封面 → 推送草稿。

    参数:
        account: 账号配置字典，需包含 app_id、app_secret，可选 author
        html_content: 文章 HTML 内容
        title: 文章标题
        cover_path: 封面图路径，可选
    返回:
        dict: {"success": bool, "media_id": str, "error": str}
    """
    app_id = account.get("app_id", "")
    app_secret = account.get("app_secret", "")
    if not author:
        author = account.get("author", "")

    # 1. 获取 token（优先使用缓存）
    try:
        token_info = _token_cache.get(app_id, app_secret)
        token = token_info["token"]
    except RuntimeError as e:
        return {"success": False, "media_id": "", "error": str(e)}

    # 2. 替换 HTML 中的图片为 CDN URL
    # 使用项目目录作为图片搜索基准（而非 cwd）
    image_dir = str(Path(__file__).parent)
    html_content = replace_html_images(html_content, image_dir, token)

    # 3. 上传封面图
    thumb_media_id = None
    # 处理 base64 封面图
    if not cover_path and cover_base64:
        try:
            import base64
            # 去掉 data:image/xxx;base64, 前缀
            if "," in cover_base64:
                cover_base64 = cover_base64.split(",", 1)[1]
            img_data = base64.b64decode(cover_base64)
            tmp_cover = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            tmp_cover.write(img_data)
            tmp_cover.close()
            cover_path = tmp_cover.name
        except Exception as e:
            return {"success": False, "media_id": "", "error": f"封面图解码失败: {str(e)}"}
    if cover_path and os.path.exists(cover_path):
        thumb_media_id = upload_thumb_image(token, cover_path)
        if not thumb_media_id:
            return {
                "success": False,
                "media_id": "",
                "error": "封面上传失败",
            }
    else:
        if cover_path:
            return {
                "success": False,
                "media_id": "",
                "error": f"封面图不存在: {cover_path}",
            }
        else:
            return {
                "success": False,
                "media_id": "",
                "error": "未提供封面图，微信要求必须有封面图",
            }

    # 4. 推送草稿箱
    media_id = push_draft(token, title, html_content, thumb_media_id, author, digest)
    if media_id:
        return {"success": True, "media_id": media_id, "error": ""}
    else:
        return {"success": False, "media_id": "", "error": "推送草稿箱失败"}
