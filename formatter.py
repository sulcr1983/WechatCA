"""微信公众号排版 API 模块

封装 xiaohu-wechat-format/scripts/format.py 的核心排版功能，
提供可编程调用的 API，支持文章排版、主题查询和画廊渲染。
"""

import importlib
import json
import os
import re
import shutil
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# 项目根目录
_SKILL_DIR = Path(__file__).parent / "xiaohu-wechat-format"
_THEMES_DIR = _SKILL_DIR / "themes"
_SCRIPTS_DIR = _SKILL_DIR / "scripts"

# 确保 config.json 存在（format.py 导入时会读取它）
_CONFIG_PATH = _SKILL_DIR / "config.json"
if not _CONFIG_PATH.exists():
    _EXAMPLE_PATH = _SKILL_DIR / "config.example.json"
    if _EXAMPLE_PATH.exists():
        shutil.copy2(_EXAMPLE_PATH, _CONFIG_PATH)
    else:
        # 兜底：写入最小默认配置
        _CONFIG_PATH.write_text(json.dumps({
            "output_dir": "output",
            "vault_root": "",
            "image_search_paths": [],
            "settings": {"default_theme": "newspaper", "auto_open_browser": False},
        }, ensure_ascii=False, indent=2), encoding="utf-8")

# 将 format.py 所在目录加入模块搜索路径
_scripts_dir_str = str(_SCRIPTS_DIR)
if _scripts_dir_str not in sys.path:
    sys.path.insert(0, _scripts_dir_str)

# 使用 importlib 导入 format 模块，避免与标准库或其他模块名冲突
_format_mod = importlib.import_module("format")

# 读取 config.json 获取默认配置
with open(_CONFIG_PATH, encoding="utf-8") as _f:
    _CONFIG = json.load(_f)

_DEFAULT_OUTPUT_DIR = _CONFIG["output_dir"]
_DEFAULT_VAULT_ROOT = _CONFIG.get("vault_root", "")


def format_article(markdown_text, theme_name, output_dir=None):
    """将 Markdown 文本转为微信兼容 HTML

    Args:
        markdown_text: Markdown 格式的文章内容
        theme_name: 主题名称，如 "newspaper"、"elegant" 等
        output_dir: 输出目录路径，默认使用 config.json 中的 output_dir

    Returns:
        dict: {
            "html": str,           # 排版后的文章 HTML
            "footnote_html": str,  # 脚注 HTML
            "title": str,          # 文章标题
            "word_count": int      # 字数统计
        }
    """
    # 确定输出目录
    if output_dir is None:
        output_dir = _DEFAULT_OUTPUT_DIR
    out_path = Path(output_dir)

    # 加载主题
    theme = _format_mod.load_theme(theme_name)

    # 将 markdown_text 写入临时文件，以便调用 format_for_output
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", encoding="utf-8", delete=False
    ) as tmp:
        tmp.write(markdown_text)
        tmp_path = Path(tmp.name)

    try:
        vault_root = Path(_DEFAULT_VAULT_ROOT) if _DEFAULT_VAULT_ROOT else out_path
        result = _format_mod.format_for_output(
            content=markdown_text,
            input_path=tmp_path,
            theme=theme,
            output_dir=out_path,
            vault_root=vault_root,
            output_format="wechat",
        )
    finally:
        # 清理临时文件
        tmp_path.unlink(missing_ok=True)

    return result


def get_available_themes():
    """获取所有可用主题列表

    扫描 themes 目录下的 .json 文件，读取每个主题的 name 和 colors.accent。

    Returns:
        list[dict]: 主题信息列表，每项包含:
            - id: 主题文件名（不含扩展名）
            - name: 主题中文名
            - accent: 主题强调色
    """
    themes = []
    for theme_file in sorted(_THEMES_DIR.glob("*.json")):
        try:
            with open(theme_file, encoding="utf-8") as f:
                data = json.load(f)
            themes.append({
                "id": theme_file.stem,
                "name": data.get("name", theme_file.stem),
                "accent": data.get("colors", {}).get("accent", "#333"),
            })
        except (json.JSONDecodeError, KeyError):
            # 跳过无法解析的主题文件
            continue
    return themes


def get_gallery_themes():
    """获取画廊主题列表

    Returns:
        list[str]: 画廊主题 ID 列表
    """
    return list(_format_mod.GALLERY_THEMES)


def render_gallery(markdown_text, recommended=None):
    """渲染主题画廊

    对同一篇 Markdown 内容用多个主题并行渲染，生成画廊 HTML 页面，
    方便用户对比选择最合适的主题。

    Args:
        markdown_text: Markdown 格式的文章内容
        recommended: 推荐主题 ID 列表，在画廊中会高亮显示

    Returns:
        str: 画廊页面的完整 HTML
    """
    if recommended is None:
        recommended = []

    # 将 markdown 写入临时文件
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", encoding="utf-8", delete=False
    ) as tmp:
        tmp.write(markdown_text)
        tmp_path = Path(tmp.name)

    try:
        # 预处理：提取标题和字数
        title = _format_mod.extract_title(markdown_text, tmp_path)
        word_count = _format_mod.count_words(markdown_text)

        # 预处理 Markdown 内容
        content = _format_mod.strip_frontmatter(markdown_text)
        content = _format_mod.fix_cjk_spacing(content)
        content = _format_mod.fix_cjk_bold_punctuation(content)
        content = _format_mod.process_callouts(content)
        content = _format_mod.process_manual_footnotes(content)
        content = _format_mod.process_fenced_containers(content)
        content = re.sub(r'~~(.+?)~~', r'<del>\1</del>', content)

        # 转为 HTML
        html = _format_mod.md_to_html(content)
        html, footnote_html = _format_mod.extract_links_as_footnotes(html)

        # 加载画廊主题
        theme_map = {}
        for tid in _format_mod.GALLERY_THEMES:
            tp = _THEMES_DIR / f"{tid}.json"
            if tp.exists():
                with open(tp, encoding="utf-8") as f:
                    theme_map[tid] = json.load(f)

        theme_ids = [tid for tid in _format_mod.GALLERY_THEMES if tid in theme_map]

        if not theme_ids:
            return "<p>没有找到任何可用的画廊主题</p>"

        # 并行渲染各主题
        rendered_map = {}
        with ThreadPoolExecutor(max_workers=min(8, len(theme_ids))) as executor:
            futures = {
                executor.submit(
                    _format_mod._render_single_theme,
                    tid, theme_map[tid], html, footnote_html
                ): tid
                for tid in theme_ids
            }
            for future in as_completed(futures):
                tid, rendered = future.result()
                rendered_map[tid] = rendered

        # 生成画廊 HTML（写入临时目录再读取内容）
        output_dir = Path(tempfile.mkdtemp(prefix="wechat-gallery-"))
        gallery_path = _format_mod.generate_gallery(
            rendered_map, theme_map, theme_ids,
            title, word_count, output_dir,
            recommended=recommended,
        )
        gallery_html = gallery_path.read_text(encoding="utf-8")

        # 清理临时目录
        shutil.rmtree(output_dir, ignore_errors=True)

    finally:
        tmp_path.unlink(missing_ok=True)

    return gallery_html
