/* API 通信层 */

async function api(url, options = {}) {
  try {
    const res = await fetch(url, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
      body: options.body ? JSON.stringify(options.body) : undefined,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || '请求失败');
    return data;
  } catch (err) {
    throw err;
  }
}

async function pollTask(taskId, { onPending, onDone, onFailed, intervalMs = 2000, timeoutMs = 180000 }) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    await new Promise(r => setTimeout(r, intervalMs));
    const t = await api('/api/task/' + taskId);
    if (t.status === 'done') { onDone(t.result); return; }
    if (t.status === 'failed') { onFailed(t.error || '任务失败'); return; }
    if (onPending) onPending();
  }
  onFailed('任务超时（超过 ' + (timeoutMs / 1000) + ' 秒）');
}
