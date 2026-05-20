/* 发布工作流 */

async function generateSummaryForPublish() {
  const content = document.getElementById('editor').value;
  if (!content.trim()) { showToast('请先输入内容', 'error'); return; }
  try {
    const data = await api('/api/generate-summary', { method: 'POST', body: { content } });
    if (data.summary) {
      document.getElementById('publish-digest').value = data.summary;
      showToast('摘要生成完成', 'success');
    } else {
      showToast(data.error || '生成失败', 'error');
    }
  } catch (err) {
    showToast('摘要生成失败: ' + err.message, 'error');
  }
}

async function generateCoverForPublish() {
  const content = document.getElementById('editor').value;
  if (!content.trim()) { showToast('请先输入内容', 'error'); return; }
  const preview = document.getElementById('cover-preview');
  try {
    const formatData = await api('/api/format', { method: 'POST', body: { content, theme: currentTheme } });
    const title = formatData.title || '未命名';
    preview.innerHTML = '<span class="placeholder-text">封面生成中...</span>';
    const { task_id } = await api('/api/async/generate-cover', { method: 'POST', body: { title, subtitle: '', content } });
    await pollTask(task_id, {
      onDone: (result) => {
        if (result && result.base64) {
          coverBase64 = result.base64;
          preview.innerHTML = '<img src="data:image/png;base64,' + result.base64 + '" alt="封面">';
          showToast('封面图生成完成', 'success');
        } else {
          coverBase64 = null;
          showToast(result.error || '生成失败', 'error');
        }
      },
      onFailed: (err) => { coverBase64 = null; showToast('封面生成失败: ' + err, 'error'); }
    });
  } catch (err) {
    coverBase64 = null;
    showToast('封面生成失败: ' + err.message, 'error');
  }
}

function openPublishModal() {
  const content = document.getElementById('editor').value;
  if (!content.trim()) { showToast('请先输入内容', 'error'); return; }

  selectedPublishAccountId = null;
  coverBase64 = '';
  document.getElementById('publish-author').value = '';
  document.getElementById('publish-digest').value = '';
  document.getElementById('cover-preview').innerHTML = '<span class="placeholder-text">暂无封面图</span>';
  document.getElementById('publish-status').className = 'publish-status';
  document.getElementById('publish-status').style.display = 'none';

  renderPublishAccounts();
  document.getElementById('publish-modal').classList.add('active');
}

function closePublishModal() {
  document.getElementById('publish-modal').classList.remove('active');
}

function renderPublishAccounts() {
  const container = document.getElementById('publish-accounts');
  if (!accounts.length) {
    container.innerHTML = '<p style="color:#9ca3af;font-size:13px;text-align:center;padding:16px;">暂无公众号，请先在设置中添加</p>';
    return;
  }
  container.innerHTML = accounts.map(a => `
    <div class="publish-account-item ${selectedPublishAccountId === a.id ? 'selected' : ''}" onclick="selectPublishAccount('${a.id}')">
      <div class="account-avatar" style="background:${a.avatar_color || '#6366f1'};">${(a.name || '?')[0]}</div>
      <div>
        <div style="font-weight:600;font-size:14px;">${a.name}</div>
        <div style="font-size:12px;color:#6b7280;">${a.app_id_masked || ''}</div>
      </div>
    </div>
  `).join('');
}

function selectPublishAccount(id) {
  selectedPublishAccountId = id;
  const account = accounts.find(a => a.id === id);
  if (account && account.author) {
    document.getElementById('publish-author').value = account.author;
  }
  renderPublishAccounts();
}

async function confirmPublish() {
  if (!selectedPublishAccountId) { showToast('请选择公众号', 'error'); return; }

  const content = document.getElementById('editor').value;
  const theme = document.getElementById('theme-select').value;
  const author = document.getElementById('publish-author').value;
  const digest = document.getElementById('publish-digest').value;
  const statusEl = document.getElementById('publish-status');

  statusEl.className = 'publish-status loading';
  statusEl.style.display = 'block';
  statusEl.innerHTML = '<span class="spinner"></span> 排版中...';

  try {
    const formatData = await api('/api/format', { method: 'POST', body: { content, theme } });
    statusEl.innerHTML = '<span class="spinner"></span> 推送中...';
    const { task_id } = await api('/api/async/publish', { method: 'POST', body: {
      account_id: selectedPublishAccountId,
      html: formatData.html,
      title: formatData.title || '未命名',
      author,
      digest,
      cover_base64: coverBase64 || '',
    }});
    await pollTask(task_id, {
      onDone: (result) => {
        if (result && result.success) {
          statusEl.className = 'publish-status success';
          statusEl.textContent = '✓ 推送成功！';
          showToast('文章已推送到公众号', 'success');
        } else {
          throw new Error((result && result.error) || '推送失败');
        }
      },
      onFailed: (err) => {
        statusEl.className = 'publish-status error';
        statusEl.textContent = '✗ 推送失败: ' + err;
        showToast('推送失败: ' + err, 'error');
      }
    });
  } catch (err) {
    statusEl.className = 'publish-status error';
    statusEl.textContent = '✗ 推送失败: ' + err.message;
    showToast('推送失败: ' + err.message, 'error');
  }
}
