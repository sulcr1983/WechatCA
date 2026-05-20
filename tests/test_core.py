"""核心模块单元测试：database、tasks、config_manager"""

import os
import sys
import time

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestDatabase:
    """database.py 的 CRUD 操作测试"""

    def setup_method(self):
        import database
        self.db = database
        # 清空测试前数据
        conn = self.db._get_conn()
        conn.execute("DELETE FROM accounts")
        conn.execute("DELETE FROM ai_config")
        conn.execute("DELETE FROM settings")
        conn.commit()

    def test_add_account(self):
        acc = self.db.add_account("测试号", "wxTEST001", "secret1", "测试作者")
        assert acc["name"] == "测试号"
        assert acc["app_id"] == "wxTEST001"
        assert acc["is_default"] == 1  # 第一个账号自动默认
        assert acc["id"].startswith("account_")

    def test_get_accounts(self):
        self.db.add_account("号1", "wx1", "s1", "作者1")
        self.db.add_account("号2", "wx2", "s2", "作者2")
        accounts = self.db.get_accounts()
        assert len(accounts) == 2

    def test_get_account(self):
        self.db.add_account("号1", "wx1", "s1", "作者1")
        acc = self.db.get_account("account_1")
        assert acc is not None
        assert acc["name"] == "号1"
        assert self.db.get_account("non-existent") is None

    def test_update_account(self):
        self.db.add_account("号1", "wx1", "s1", "作者1")
        updated = self.db.update_account("account_1", name="改名")
        assert updated["name"] == "改名"
        assert self.db.update_account("non-existent", name="x") is None

    def test_delete_account(self):
        self.db.add_account("号1", "wx1", "s1", "作者1")
        assert self.db.delete_account("account_1") is True
        assert self.db.delete_account("account_1") is False
        assert len(self.db.get_accounts()) == 0

    def test_set_default_account(self):
        self.db.add_account("号1", "wx1", "s1", "作者1")
        self.db.add_account("号2", "wx2", "s2", "作者2")
        assert self.db.set_default_account("account_2") is True
        acc1 = self.db.get_account("account_1")
        acc2 = self.db.get_account("account_2")
        assert acc1["is_default"] == 0
        assert acc2["is_default"] == 1
        assert self.db.set_default_account("non-existent") is False

    def test_delete_default_reassigns(self):
        self.db.add_account("号1", "wx1", "s1", "作者1")
        self.db.add_account("号2", "wx2", "s2", "作者2")
        self.db.delete_account("account_1")  # 删除默认号
        remaining = self.db.get_accounts()
        assert len(remaining) == 1
        assert remaining[0]["is_default"] == 1

    def test_ai_config_crud(self):
        self.db.save_ai_config(url="https://test.api/v1", api_key="sk-test", model="gpt-4")
        config = self.db.get_ai_config()
        assert config["url"] == "https://test.api/v1"
        assert config["api_key"] == "sk-test"
        assert config["model"] == "gpt-4"

    def test_ai_config_partial_update(self):
        self.db.save_ai_config(url="https://a.com", api_key="sk-a")
        self.db.save_ai_config(model="gpt-4o")  # 部分更新
        config = self.db.get_ai_config()
        assert config["url"] == "https://a.com"  # 不变
        assert config["model"] == "gpt-4o"  # 更新

    def test_settings(self):
        assert self.db.get_setting("theme", "default") == "default"
        self.db.set_setting("theme", "newspaper")
        assert self.db.get_setting("theme") == "newspaper"

    def test_mask_app_id(self):
        assert self.db.mask_app_id("") == ""
        assert self.db.mask_app_id("wx") == "w***x"
        assert self.db.mask_app_id("wxe2bd55ee50e1b7c5") == "wxe***7c5"


class TestConfigManager:
    """config_manager.py 公共 API 兼容性测试"""

    def setup_method(self):
        import database
        import config_manager
        self.cm = config_manager
        conn = database._get_conn()
        conn.execute("DELETE FROM accounts")
        conn.execute("DELETE FROM ai_config")
        conn.commit()

    def test_get_accounts_removes_secret(self):
        import database
        database.add_account("测试", "wxT", "secret", "作者")
        accounts = self.cm.get_accounts()
        assert len(accounts) == 1
        assert "app_secret" not in accounts[0]
        assert accounts[0]["name"] == "测试"

    def test_get_account_has_secret(self):
        import database
        database.add_account("测试", "wxT", "secret", "作者")
        acc = self.cm.get_account("account_1")
        assert acc["app_secret"] == "secret"

    def test_mask_app_id(self):
        assert self.cm.mask_app_id("wxe2bd55ee50e1b7c5") == "wxe***7c5"

    def test_default_account(self):
        import database
        database.add_account("号1", "wx1", "s1", "a1")
        database.add_account("号2", "wx2", "s2", "a2")
        default = self.cm.get_default_account()
        assert default["name"] == "号1"


class TestTasks:
    """tasks.py 异步任务系统测试"""

    def test_submit_and_poll_done(self):
        import tasks

        def add(a, b):
            return a + b

        task_id = tasks.submit(add, 1, 2)
        result = None
        for _ in range(20):
            t = tasks.get(task_id)
            if t["status"] in ("done", "failed"):
                result = t
                break
            time.sleep(0.1)

        assert result is not None
        assert result["status"] == "done"
        assert result["result"] == 3

    def test_submit_and_poll_failed(self):
        import tasks

        def fail():
            raise ValueError("test error")

        task_id = tasks.submit(fail)
        result = None
        for _ in range(20):
            t = tasks.get(task_id)
            if t["status"] in ("done", "failed"):
                result = t
                break
            time.sleep(0.1)

        assert result is not None
        assert result["status"] == "failed"
        assert "test error" in result["error"]

    def test_get_non_existent(self):
        import tasks
        assert tasks.get("nonexistent1234") is None

    def test_multiple_tasks(self):
        import tasks

        def slow_add(a, b):
            time.sleep(0.3)
            return a + b

        ids = [tasks.submit(slow_add, i, i) for i in range(5)]
        assert len(ids) == 5
        assert len(set(ids)) == 5  # 每个 ID 唯一

        # 等待全部完成
        for _ in range(40):
            all_done = all(
                tasks.get(tid)["status"] in ("done", "failed")
                for tid in ids
            )
            if all_done:
                break
            time.sleep(0.1)

        for tid in ids:
            t = tasks.get(tid)
            assert t["status"] == "done"
