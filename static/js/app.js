/* 应用主入口 — 状态、导航、编辑、主题 */

/* ===== State ===== */
let currentTab = 'editor';
let currentTheme = '';
let themes = [];
let accounts = [];
let aiPlatforms = [];
let formatTimer = null;
let coverBase64 = '';
let selectedPublishAccountId = null;

/* ===== Tab Switching ===== */
function switchTab(tab) {
  currentTab = tab;
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.toggle('active', t.dataset.tab === tab));
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.getElementById('tab-' + tab).classList.add('active');
  if (tab === 'gallery') loadThemes();
  if (tab === 'settings') loadSettings();
}

/* ===== Toast ===== */
function showToast(msg, type = 'info') {
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = 'toast ' + type;
  toast.textContent = msg;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.animation = 'toastOut 0.3s ease forwards';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

/* ===== Plain Text Detection ===== */
function isPlainText(content) {
  // Count Markdown structure markers
  let count = 0;
  count += (content.match(/^#+\s/gm) || []).length;     // headings
  count += (content.match(/\*\*/g) || []).length / 2;    // bold
  count += (content.match(/^-\s/gm) || []).length;        // unordered lists
  count += (content.match(/^>\s/gm) || []).length;        // blockquotes
  count += (content.match(/`/g) || []).length / 2;         // inline code
  count += (content.match(/^---+$/gm) || []).length;       // horizontal rules
  return count < 2;
}

/* ===== Format Content (debounced) ===== */
function formatContent() {
  clearTimeout(formatTimer);
  formatTimer = setTimeout(async () => {
    const content = document.getElementById('editor').value;
    const theme = document.getElementById('theme-select').value;
    if (!content.trim()) {
      document.getElementById('preview').innerHTML = '<p style="color:#9ca3af;">预览区域</p>';
      document.getElementById('word-count').textContent = '0';
      return;
    }
    try {
      const data = await api('/api/format', { method: 'POST', body: { content, theme } });
      let html = data.html || '';
      // 检测纯文本，在预览顶部插入 AI 增强提示
      if (isPlainText(content)) {
        html = '<div style="background:#fef3c7;border:1px solid #f59e0b;border-radius:8px;padding:10px 14px;margin-bottom:16px;font-size:14px;color:#92400e;text-align:center;cursor:pointer" onclick="aiEnhance()">💡 检测到纯文本，点击 <b>AI 增强</b> 自动添加标题、加粗、列表等排版结构</div>' + html;
      }
      document.getElementById('preview').innerHTML = html;
      document.getElementById('word-count').textContent = data.word_count || 0;
    } catch (err) {
      document.getElementById('preview').innerHTML = '<p style="color:#ef4444;">排版失败: ' + err.message + '</p>';
    }
  }, 500);
}

/* ===== AI Enhance ===== */
async function aiEnhance() {
  const content = document.getElementById('editor').value;
  if (!content.trim()) { showToast('请先输入内容', 'error'); return; }
  const btn = event.target.closest('button');
  const origText = btn.innerHTML;
  btn.innerHTML = '<span class="spinner"></span> 增强中...';
  btn.disabled = true;
  try {
    const data = await api('/api/enhance', { method: 'POST', body: { content } });
    if (data.enhanced) {
      document.getElementById('editor').value = data.enhanced;
      formatContent();
      showToast('AI 增强完成', 'success');
    } else {
      showToast(data.error || '增强失败', 'error');
    }
  } catch (err) {
    showToast('AI 增强失败: ' + err.message, 'error');
  } finally {
    btn.innerHTML = origText;
    btn.disabled = false;
  }
}

/* ===== Copy to Clipboard ===== */
async function copyToClipboard() {
  const content = document.getElementById('editor').value;
  if (!content.trim()) { showToast('请先输入内容', 'error'); return; }
  const theme = document.getElementById('theme-select').value;
  try {
    const data = await api('/api/copy-html', { method: 'POST', body: { content, theme } });
    if (data.html) {
      const blob = new Blob([data.html], { type: 'text/html' });
      const textBlob = new Blob([data.html], { type: 'text/plain' });
      await navigator.clipboard.write([
        new ClipboardItem({
          'text/html': blob,
          'text/plain': textBlob,
        }),
      ]);
      showToast('已复制到剪贴板，可直接粘贴到微信编辑器', 'success');
    }
  } catch (err) {
    showToast('复制失败: ' + err.message, 'error');
  }
}

/* ===== Themes ===== */
async function loadThemes() {
  try {
    themes = await api('/api/themes');
    renderGallery();
    renderThemeSelect();
  } catch (err) {
    console.error('加载主题失败:', err);
  }
}

function renderGallery() {
  const grid = document.getElementById('gallery-grid');
  grid.innerHTML = themes.map(t => `
    <div class="theme-card ${currentTheme === t.id ? 'selected' : ''}" onclick="selectTheme('${t.id}')">
      <div class="theme-color-dot" style="background:${t.accent || '#6366f1'};"></div>
      <div class="theme-card-name">${t.name}</div>
    </div>
  `).join('');
}

function renderThemeSelect() {
  const sel = document.getElementById('theme-select');
  const val = sel.value;
  sel.innerHTML = '<option value="">选择主题</option>' + themes.map(t =>
    `<option value="${t.id}" ${t.id === val ? 'selected' : ''}>${t.name}</option>`
  ).join('');
}

function selectTheme(id) {
  currentTheme = id;
  document.getElementById('theme-select').value = id;
  renderGallery();
  formatContent();
  showToast('主题已切换', 'info');
}

function onThemeChange() {
  currentTheme = document.getElementById('theme-select').value;
  formatContent();
}

/* ===== Init ===== */
(async function init() {
  await loadThemes();
  await loadAccounts();
  await loadAiConfig();
  if (themes.length > 0 && !currentTheme) {
    currentTheme = themes[0].id;
    document.getElementById('theme-select').value = currentTheme;
  }
})();

/* ===== Glass Button Glow Effect ===== */
document.addEventListener('mousemove', (e) => {
  document.querySelectorAll('.glass-btn').forEach(btn => {
    const rect = btn.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * 100;
    const y = ((e.clientY - rect.top) / rect.height) * 100;
    btn.style.setProperty('--glow-x', x + '%');
    btn.style.setProperty('--glow-y', y + '%');
  });
});

/* ===== Editor Input ===== */
document.getElementById('editor').addEventListener('input', formatContent);
