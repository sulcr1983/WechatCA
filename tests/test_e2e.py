"""Playwright E2E 测试：核心用户流程

启动 Flask 后运行:
    python tests/test_e2e.py

或使用 pytest:
    pytest tests/test_e2e.py -v
"""

import os
import sys
import subprocess
import time
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def start_flask(port=5099):
    """在后台线程启动 Flask 测试服务器"""
    from app import app

    def run():
        app.run(host="127.0.0.1", port=port, debug=False, threaded=True)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    time.sleep(1.5)
    return f"http://127.0.0.1:{port}"


def run_tests():
    """运行 Playwright E2E 测试"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright 未安装。运行: pip install playwright && playwright install chromium")
        sys.exit(1)

    BASE = start_flask(5099)
    print(f"Flask 测试服务器: {BASE}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 900})

        errors = []

        def check(condition, msg):
            if not condition:
                errors.append(msg)
                print(f"  FAIL: {msg}")
            else:
                print(f"  OK: {msg}")

        # ── Test 1: 页面加载 ──
        print("\n=== Test 1: 页面加载 ===")
        page.goto(BASE, timeout=10000)
        page.wait_for_load_state("networkidle")
        check("SuperSu" in page.title(), "页面标题包含 'SuperSu'")

        # ── Test 2: 编辑器可见 ──
        print("\n=== Test 2: 编辑器可见 ===")
        editor = page.locator("#editor")
        check(editor.is_visible(), "编辑器可见")
        preview = page.locator("#preview")
        check(preview.is_visible(), "预览区可见")

        # ── Test 3: 输入 Markdown 触发预览 ──
        print("\n=== Test 3: Markdown 输入 → 实时预览 ===")
        editor.fill("# 测试标题\n\n这是**加粗**的测试内容。\n\n- 列表项1\n- 列表项2")
        page.wait_for_timeout(1000)  # 等待 debounce

        preview_html = preview.inner_html()
        check("测试标题" in preview_html or "<h1" in preview_html.lower(), "预览包含标题")
        check("加粗" in preview_html or "<strong" in preview_html.lower(), "预览包含加粗文本")

        # ── Test 4: 字数统计 ──
        print("\n=== Test 4: 字数统计 ===")
        word_count = page.locator("#word-count")
        check(word_count.is_visible(), "字数统计可见")
        count_text = word_count.text_content()
        check(int(count_text) > 0, f"字数大于 0: {count_text}")

        # ── Test 5: 主题切换下拉框 ──
        print("\n=== Test 5: 主题选择 ===")
        theme_select = page.locator("#theme-select")
        check(theme_select.is_visible(), "主题下拉框可见")
        options = theme_select.locator("option")
        option_count = options.count()
        check(option_count > 5, f"主题数量 > 5: {option_count}")

        # ── Test 6: 打开推送对话框 ──
        print("\n=== Test 6: 推送对话框 ===")
        publish_btn = page.locator("button:has-text('推送到公众号')")
        check(publish_btn.is_visible(), "推送按钮可见")
        publish_btn.click()
        page.wait_for_timeout(500)

        modal = page.locator("#publish-modal")
        check(modal.is_visible(), "推送对话框已打开")
        overlay = page.locator("#publish-modal")
        check("active" in overlay.evaluate("el => el.className"),
              "modal-overlay active 类已添加")

        # ── Test 7: 关闭推送对话框 ──
        print("\n=== Test 7: 关闭推送对话框 ===")
        close_btn = page.locator("#publish-modal .modal-close")
        close_btn.click()
        page.wait_for_timeout(300)
        check(not overlay.is_visible(), "推送对话框已关闭")

        # ── Test 8: 切换到设置页 ──
        print("\n=== Test 8: 切换到设置 ===")
        settings_tab = page.locator("button.nav-tab:has-text('设置')")
        settings_tab.click()
        page.wait_for_timeout(500)
        settings_panel = page.locator("#tab-settings")
        check(settings_panel.is_visible(), "设置面板可见")

        # ── Test 9: 切换到主题画廊 ──
        print("\n=== Test 9: 切换到主题画廊 ===")
        gallery_tab = page.locator("button.nav-tab:has-text('主题画廊')")
        gallery_tab.click()
        page.wait_for_timeout(500)
        gallery = page.locator("#tab-gallery")
        check(gallery.is_visible(), "画廊面板可见")
        cards = page.locator(".theme-card")
        check(cards.count() > 5, f"主题卡片数量 > 5: {cards.count()}")

        # ── Test 10: 切回编辑器 ──
        print("\n=== Test 10: 切回编辑器 ===")
        editor_tab = page.locator("button.nav-tab:has-text('编辑')")
        editor_tab.click()
        page.wait_for_timeout(300)
        editor_panel = page.locator("#tab-editor")
        check(editor_panel.is_visible(), "编辑器面板可见")
        # 内容应该还在
        editor_content = editor.input_value()
        check("测试标题" in editor_content, "编辑器内容保留")

        browser.close()

        # ── 报告 ──
        print(f"\n{'='*40}")
        if errors:
            print(f"E2E 测试完成: {len(errors)} 个失败")
            for e in errors:
                print(f"  - {e}")
            sys.exit(1)
        else:
            print("E2E 测试全部通过!")
            sys.exit(0)


if __name__ == "__main__":
    run_tests()
