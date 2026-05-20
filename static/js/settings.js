/* 设置管理 */

async function loadAiPlatforms() {
  try {
    aiPlatforms = await api('/api/ai-platforms');
    const sel = document.getElementById('ai-platform');
    sel.innerHTML = '<option value="">选择平台</option>' + aiPlatforms.map(p =>
      `<option value="${p.id}">${p.name}</option>`
    ).join('');
  } catch (err) {
    console.error('加载平台列表失败:', err);
  }
}

function onPlatformChange() {
  const sel = document.getElementById('ai-platform');
  const platformId = sel.value;
  const customField = document.getElementById('custom-url-field');
  const modelSel = document.getElementById('ai-model');

  if (platformId === 'custom') {
    customField.classList.add('visible');
    modelSel.innerHTML = '<option value="">选择模型</option>';
    return;
  }

  customField.classList.remove('visible');
  const platform = aiPlatforms.find(p => p.id === platformId);
  if (platform) {
    if (platform.url) document.getElementById('ai-custom-url').value = platform.url;
    if (platform.models) {
      modelSel.innerHTML = platform.models.map(m =>
        `<option value="${m}">${m}</option>`
      ).join('');
    }
  }
}

async function testAiConnection() {
  const platformId = document.getElementById('ai-platform').value;
  const apiKey = document.getElementById('ai-api-key').value;
  const model = document.getElementById('ai-model').value;
  const url = document.getElementById('ai-custom-url').value;
  const statusEl = document.getElementById('test-status');

  if (!apiKey || !model) {
    statusEl.className = 'test-status error';
    statusEl.textContent = '请填写 API Key 和模型';
    return;
  }

  if (!url) {
    statusEl.className = 'test-status error';
    statusEl.textContent = '请选择平台或填写自定义 URL';
    return;
  }

  statusEl.className = 'test-status';
  statusEl.style.display = 'block';
  statusEl.innerHTML = '<span class="spinner"></span> 测试中...';

  try {
    const data = await api('/api/test-ai', { method: 'POST', body: { api_key: apiKey, model, url, platform_id: platformId } });
    if (data.success) {
      statusEl.className = 'test-status success';
      statusEl.textContent = '✓ 连接成功' + (data.model ? ' — 模型: ' + data.model : '');
    } else {
      statusEl.className = 'test-status error';
      statusEl.textContent = '✗ 连接失败: ' + (data.error || '未知错误');
    }
  } catch (err) {
    statusEl.className = 'test-status error';
    statusEl.textContent = '✗ 连接失败: ' + err.message;
  }
}

async function saveAiConfig() {
  const platformId = document.getElementById('ai-platform').value;
  const url = document.getElementById('ai-custom-url').value;
  const apiKey = document.getElementById('ai-api-key').value;
  const model = document.getElementById('ai-model').value;

  const body = { platform_id: platformId, model };
  if (apiKey) body.api_key = apiKey;
  if (platformId === 'custom' && url) body.url = url;
  else if (platformId !== 'custom') {
    const platform = aiPlatforms.find(p => p.id === platformId);
    if (platform) body.url = platform.url;
  }

  try {
    await api('/api/ai-config', { method: 'POST', body });
    showToast('AI 配置已保存', 'success');
  } catch (err) {
    showToast('保存失败: ' + err.message, 'error');
  }
}

async function loadAiConfig() {
  try {
    const data = await api('/api/ai-config');
    if (data.platform_id) {
      document.getElementById('ai-platform').value = data.platform_id;
      onPlatformChange();
    }
    if (data.url) document.getElementById('ai-custom-url').value = data.url;
    if (data.api_key_masked) document.getElementById('ai-api-key').placeholder = data.api_key_masked;
    if (data.model) document.getElementById('ai-model').value = data.model;
  } catch (err) {
    console.error('加载AI配置失败:', err);
  }
}

function toggleApiKey() {
  const input = document.getElementById('ai-api-key');
  input.type = input.type === 'password' ? 'text' : 'password';
}

function toggleAppSecret() {
  const input = document.getElementById('account-appsecret');
  input.type = input.type === 'password' ? 'text' : 'password';
}

/* 公众号 CRUD */

async function loadAccounts() {
  try {
    accounts = await api('/api/accounts');
    renderAccounts();
  } catch (err) {
    console.error('加载公众号列表失败:', err);
  }
}

function renderAccounts() {
  const list = document.getElementById('account-list');
  if (!accounts.length) {
    list.innerHTML = '<p style="color:#9ca3af;font-size:13px;text-align:center;padding:20px;">暂无公众号</p>';
    return;
  }
  list.innerHTML = accounts.map(a => `
    <div class="account-card">
      <div class="account-avatar" style="background:${a.avatar_color || '#6366f1'};">${(a.name || '?')[0]}</div>
      <div class="account-info">
        <div class="account-name">${a.name}</div>
        <div class="account-meta">
          <span>${a.app_id_masked || ''}</span>
          <span>${a.author || ''}</span>
          ${a.is_default ? '<span style="color:#6366f1;">默认</span>' : ''}
        </div>
      </div>
      <div class="account-actions">
        <button onclick="editAccount('${a.id}')">编辑</button>
        <button class="delete-btn" onclick="deleteAccount('${a.id}')">删除</button>
      </div>
    </div>
  `).join('');
}

function openAccountModal(id) {
  document.getElementById('account-edit-id').value = '';
  document.getElementById('account-modal-title').textContent = '新增公众号';
  document.getElementById('account-name').value = '';
  document.getElementById('account-appid').value = '';
  document.getElementById('account-appsecret').value = '';
  document.getElementById('account-author').value = '';
  document.getElementById('account-modal').classList.add('active');
}

function closeAccountModal() {
  document.getElementById('account-modal').classList.remove('active');
}

async function editAccount(id) {
  const account = accounts.find(a => a.id === id);
  if (!account) return;
  document.getElementById('account-edit-id').value = id;
  document.getElementById('account-modal-title').textContent = '编辑公众号';
  document.getElementById('account-name').value = account.name || '';
  document.getElementById('account-appid').value = '';
  document.getElementById('account-appsecret').value = '';
  document.getElementById('account-author').value = account.author || '';
  document.getElementById('account-modal').classList.add('active');
}

async function saveAccount() {
  const editId = document.getElementById('account-edit-id').value;
  const body = {
    name: document.getElementById('account-name').value,
    app_id: document.getElementById('account-appid').value,
    app_secret: document.getElementById('account-appsecret').value,
    author: document.getElementById('account-author').value,
  };

  try {
    if (editId) {
      await api('/api/accounts/' + editId, { method: 'PUT', body });
      showToast('公众号已更新', 'success');
    } else {
      await api('/api/accounts', { method: 'POST', body });
      showToast('公众号已添加', 'success');
    }
    closeAccountModal();
    loadAccounts();
  } catch (err) {
    showToast('保存失败: ' + err.message, 'error');
  }
}

async function deleteAccount(id) {
  if (!confirm('确定删除此公众号？')) return;
  try {
    await api('/api/accounts/' + id, { method: 'DELETE' });
    showToast('公众号已删除', 'success');
    loadAccounts();
  } catch (err) {
    showToast('删除失败: ' + err.message, 'error');
  }
}

async function loadSettings() {
  await Promise.all([loadAiPlatforms(), loadAiConfig(), loadAccounts()]);
}
