"""异步任务队列：ThreadPoolExecutor + 内存存储 + 轮询。

慢操作（生图、推送）提交到后台线程，前端通过 task_id 轮询结果。
"""

import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, Future

_executor = ThreadPoolExecutor(max_workers=4)
_lock = threading.Lock()
_tasks: dict[str, dict] = {}


def submit(fn, *args, **kwargs) -> str:
    """提交任务到后台线程，返回 task_id。

    Usage:
        task_id = tasks.submit(ai_enhancer.generate_cover, title, subtitle, content, config)
    """
    task_id = uuid.uuid4().hex[:12]

    with _lock:
        _tasks[task_id] = {
            "status": "pending",
            "result": None,
            "error": None,
            "created_at": time.time(),
        }

    def _wrapper():
        try:
            result = fn(*args, **kwargs)
            with _lock:
                _tasks[task_id]["status"] = "done"
                _tasks[task_id]["result"] = result
        except Exception as e:
            with _lock:
                _tasks[task_id]["status"] = "failed"
                _tasks[task_id]["error"] = str(e)

    _executor.submit(_wrapper)

    # 清理 10 分钟前的旧任务
    _cleanup()

    return task_id


def get(task_id: str) -> dict | None:
    """获取任务状态。返回 None 表示 task_id 不存在。"""
    with _lock:
        return _tasks.get(task_id)


def _cleanup():
    """清理超过 10 分钟的旧任务。"""
    now = time.time()
    expired = [tid for tid, t in _tasks.items() if now - t["created_at"] > 600]
    for tid in expired:
        del _tasks[tid]
