// DOM 元素
const textInput = document.getElementById('textInput');
const voiceSelect = document.getElementById('voiceSelect');
const resolutionSelect = document.getElementById('resolutionSelect');
const bgmSelect = document.getElementById('bgmSelect');
const subtitleStyleSelect = document.getElementById('subtitleStyleSelect');
const fontSelect = document.getElementById('fontSelect');
const generateBtn = document.getElementById('generateBtn');
const feedContainer = document.getElementById('progressFeed');
const emptyState = document.getElementById('emptyState');
const resultSection = document.getElementById('resultSection');
const resultVideo = document.getElementById('resultVideo');
const downloadBtn = document.getElementById('downloadBtn');
const globalProgressWrapper = document.getElementById('globalProgressWrapper');
const globalProgressFill = document.getElementById('globalProgressFill');
const globalProgressText = document.getElementById('globalProgressText');
const headerStatus = document.getElementById('headerStatus');
const statusPulse = document.getElementById('statusPulse');
const previewBgmBtn = document.getElementById('previewBgmBtn');
const abortBtn = document.getElementById('abortBtn');

// 设置面板相关
const openSettingsBtn = document.getElementById('openSettingsBtn');
const closeSettingsBtn = document.getElementById('closeSettingsBtn');
const settingsPanel = document.getElementById('settingsPanel');
const settingsOverlay = document.getElementById('settingsOverlay');
const saveSettingsBtn = document.getElementById('saveSettingsBtn');
const imgProviderSelect = document.getElementById('imgProviderSelect');
const imgApiConfigFields = document.getElementById('imgApiConfigFields');
const imgLocalConfigFields = document.getElementById('imgLocalConfigFields');
const imgBaseUrlInput = document.getElementById('imgBaseUrlInput');
const imgApiKeyInput = document.getElementById('imgApiKeyInput');
const imgModelIdInput = document.getElementById('imgModelIdInput');
const imgLocalPathInput = document.getElementById('imgLocalPathInput');

let currentAudio = null;

// 初始化
async function init() {
  updateTime();
  setInterval(updateTime, 60000);
  await loadVoices();
  await loadResolutions();
  await loadBGM();
  await loadSubtitlePresets();
  loadConfigFromStorage();
  checkExistingTask();

  // BGM 试听逻辑
  previewBgmBtn.addEventListener('click', () => {
    if (currentAudio) {
      currentAudio.pause();
      if (currentAudio.src.includes(bgmSelect.value)) {
        currentAudio = null;
        previewBgmBtn.innerHTML = '<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path d="M4.5 3.5v13l11-6.5-11-6.5z"/></svg>';
        return;
      }
    }

    if (bgmSelect.value === 'none') return;

    currentAudio = new Audio(`/assets/bgm/${bgmSelect.value}.mp3`);
    currentAudio.play();
    previewBgmBtn.innerHTML = '<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path d="M6 4h4v12H6zM11 4h4v12h-4z"/></svg>';

    currentAudio.onended = () => {
      previewBgmBtn.innerHTML = '<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path d="M4.5 3.5v13l11-6.5-11-6.5z"/></svg>';
      currentAudio = null;
    };
  });

  // 中止逻辑
  abortBtn.addEventListener('click', async () => {
    const taskId = localStorage.getItem('activeTaskId');
    if (!taskId) return;
    if (confirm('确定要中止当前视频生成吗？')) {
      try {
        await fetch(`/api/abort/${taskId}`, { method: 'POST' });
        localStorage.removeItem('activeTaskId');
        setRunningUI(false);
        addFeedItem('sys', { text: '系统通知', step: '🛑 任务已手动中止', done: false });
      } catch (e) { console.error(e); }
    }
  });

  // 设置面板逻辑
  openSettingsBtn.addEventListener('click', () => {
    settingsPanel.classList.remove('translate-x-full');
    settingsOverlay.classList.remove('hidden');
  });

  const closeSettings = () => {
    settingsPanel.classList.add('translate-x-full');
    settingsOverlay.classList.add('hidden');
  };

  closeSettingsBtn.addEventListener('click', closeSettings);
  settingsOverlay.addEventListener('click', closeSettings);

  // 厂商选择切换逻辑
  imgProviderSelect.addEventListener('change', () => {
    const isLocal = imgProviderSelect.value === 'local_zimage';
    imgApiConfigFields.classList.toggle('hidden', isLocal);
    imgLocalConfigFields.classList.toggle('hidden', !isLocal);

    // 自动填充默认端点
    if (imgProviderSelect.value === 'openai' && !imgBaseUrlInput.value) {
      imgBaseUrlInput.value = 'https://api.openai.com/v1/images/generations';
      imgModelIdInput.value = 'dall-e-3';
    } else if (imgProviderSelect.value === 'volcengine' && !imgBaseUrlInput.value) {
      imgBaseUrlInput.value = 'https://ark.cn-beijing.volces.com/api/v3/images/generations';
    }
  });

  saveSettingsBtn.addEventListener('click', () => {
    const config = {
      provider: imgProviderSelect.value,
      baseUrl: imgBaseUrlInput.value.trim(),
      apiKey: imgApiKeyInput.value.trim(),
      modelId: imgModelIdInput.value.trim(),
      localPath: imgLocalPathInput.value.trim()
    };
    localStorage.setItem('model_config', JSON.stringify(config));

    // 视觉反馈
    const originalText = saveSettingsBtn.textContent;
    saveSettingsBtn.textContent = '✅ 配置已保存';
    saveSettingsBtn.classList.replace('bg-black', 'bg-green-600');

    setTimeout(() => {
      saveSettingsBtn.textContent = originalText;
      saveSettingsBtn.classList.replace('bg-green-600', 'bg-black');
      closeSettings();
    }, 1000);
  });
}

function loadConfigFromStorage() {
  const saved = localStorage.getItem('model_config');
  if (saved) {
    const config = JSON.parse(saved);
    imgProviderSelect.value = config.provider || 'volcengine';
    imgBaseUrlInput.value = config.baseUrl || '';
    imgApiKeyInput.value = config.apiKey || '';
    imgModelIdInput.value = config.modelId || '';
    imgLocalPathInput.value = config.localPath || '';

    // 触发 UI 刷新
    imgProviderSelect.dispatchEvent(new Event('change'));
  }
}

function updateTime() {
  const now = new Date();
  document.getElementById('currentTime').textContent = now.toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false
  }).replace(/\//g, '-');
}

function checkExistingTask() {
  const taskId = localStorage.getItem('activeTaskId');
  if (taskId) {
    setRunningUI(true);
    trackProgress(taskId).catch(() => {
      localStorage.removeItem('activeTaskId');
      setRunningUI(false);
    });
  }
}

async function loadVoices() {
  try {
    const res = await fetch('/api/voices');
    const voices = await res.json();
    voiceSelect.innerHTML = voices.map(v => `<option value="${v.id}">${v.name}</option>`).join('');
  } catch (e) { console.error(e); }
}

async function loadResolutions() {
  try {
    const res = await fetch('/api/resolutions');
    const resolutions = await res.json();
    resolutionSelect.innerHTML = resolutions.map(r => `<option value="${r.id}">${r.name}</option>`).join('');
  } catch (e) { console.error(e); }
}

async function loadBGM() {
  try {
    const res = await fetch('/api/bgm');
    const bgmList = await res.json();
    bgmSelect.innerHTML = bgmList.map(b => `<option value="${b.id}">${b.name}</option>`).join('');
  } catch (e) { console.error(e); }
}

async function loadSubtitlePresets() {
  try {
    const res = await fetch('/api/subtitle_presets');
    const data = await res.json();
    subtitleStyleSelect.innerHTML = data.presets.map(p => `<option value="${p.id}">${p.name}</option>`).join('');
    fontSelect.innerHTML = data.fonts.map(f => `<option value="${f}">${f}</option>`).join('');
  } catch (e) { console.error(e); }
}

function setRunningUI(isRunning) {
  generateBtn.disabled = isRunning;
  generateBtn.querySelector('.btn-text').textContent = isRunning ? '视频生产中...' : '开始生成视频';
  if (isRunning) {
    emptyState.classList.add('hidden');
    globalProgressWrapper.classList.remove('hidden');
    headerStatus.textContent = '生产中';
    statusPulse.classList.replace('bg-slate-300', 'bg-green-500');
    statusPulse.classList.add('animate-pulse');
  } else {
    globalProgressWrapper.classList.add('hidden');
    headerStatus.textContent = '就绪';
    statusPulse.classList.replace('bg-green-500', 'bg-slate-300');
    statusPulse.classList.remove('animate-pulse');
  }
}

async function startGeneration() {
  const text = textInput.value.trim();
  if (!text) { alert('请输入文案内容'); return; }

  setRunningUI(true);
  resultSection.classList.add('hidden');
  feedContainer.innerHTML = '';

  const resVal = resolutionSelect.value;
  const videoContainer = resultSection.querySelector('.bg-black.rounded-2xl');
  if (videoContainer) {
    videoContainer.className = 'bg-black rounded-2xl overflow-hidden relative group transition-all duration-500 mx-auto';
    if (resVal === '9:16') videoContainer.classList.add('aspect-[9/16]', 'max-w-[350px]');
    else if (resVal === '1:1') videoContainer.classList.add('aspect-square', 'max-w-[500px]');
    else videoContainer.classList.add('aspect-video', 'w-full');
  }

  // 获取模型配置
  const modelConfig = JSON.parse(localStorage.getItem('model_config') || '{}');

  try {
    const res = await fetch('/api/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text,
        voice: voiceSelect.value,
        resolution: resolutionSelect.value,
        bgm: bgmSelect.value,
        subtitle_style: subtitleStyleSelect.value,
        font_name: fontSelect.value,
        image_config: {
          provider: modelConfig.provider,
          api_key: modelConfig.apiKey,
          model_id: modelConfig.modelId,
          base_url: modelConfig.baseUrl,
          local_path: modelConfig.localPath
        }
      })
    });
    const data = await res.json();
    if (data.error) throw new Error(data.error);
    localStorage.setItem('activeTaskId', data.task_id);
    await trackProgress(data.task_id);
  } catch (e) {
    addFeedItem('err', { text: '系统告警', step: e.message, done: false });
    setRunningUI(false);
  }
}

function addFeedItem(sceneId, data) {
  let item = document.getElementById(`scene-card-${sceneId}`);
  const isCompleted = data.done;
  const isError = data.step && data.step.includes('❌');
  const isSystem = sceneId === '0' || sceneId === 'sys' || sceneId === 'err';

  if (!item) {
    item = document.createElement('div');
    item.id = `scene-card-${sceneId}`;
    item.className = 'feed-item bg-white border border-[#E5E5E3] p-5 rounded-2xl shadow-sm flex items-start gap-4 transition-all duration-300';
    feedContainer.prepend(item);
  }

  const iconColor = (isError || sceneId === 'err') ? 'bg-red-100 text-red-600' :
    isCompleted ? 'bg-green-100 text-green-600' :
      'bg-slate-100 text-slate-600 animate-pulse';

  const icon = isCompleted ? '✓' : (isError || sceneId === 'err') ? '!' : (isSystem ? '⚙️' : sceneId);

  item.innerHTML = `
    <div class="w-10 h-10 rounded-full flex-shrink-0 flex items-center justify-center text-xs font-bold ${iconColor}">
        ${icon}
    </div>
    <div class="flex-1 min-w-0">
        <div class="flex justify-between items-center mb-1">
            <span class="text-xs font-bold uppercase tracking-widest text-[#A0A09A]">
                ${isSystem ? '系统引擎' : '场景 ' + sceneId}
            </span>
            <div class="flex items-center gap-2">
                ${data.step ? `<span class="text-[10px] px-1.5 py-0.5 rounded-md bg-[#F5F5F3] text-[#70706B] font-medium">${data.step}</span>` : ''}
                <span class="text-[10px] text-[#D0D0CC]">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
            </div>
        </div>
        <p class="text-sm leading-relaxed break-words text-[#1A1A1A] font-medium">${data.text || ''}</p>
    </div>
  `;

  if (isCompleted) {
    item.classList.remove('animate-pulse');
    item.classList.add('border-green-100', 'bg-green-50/10');
  }
}

function trackProgress(taskId) {
  return new Promise((resolve, reject) => {
    const eventSource = new EventSource(`/api/progress/${taskId}`);
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.error) {
        eventSource.close();
        localStorage.removeItem('activeTaskId');
        addFeedItem('err', { text: '系统告警', step: data.error, done: false });
        reject(new Error(data.error));
        return;
      }

      globalProgressFill.style.width = `${data.progress}%`;
      globalProgressText.textContent = `${data.progress}%`;

      if (data.scenes_status) {
        Object.entries(data.scenes_status).forEach(([sId, sData]) => {
          addFeedItem(sId, sData);
        });
      }

      if (data.status === 'completed') {
        eventSource.close();
        localStorage.removeItem('activeTaskId');
        onGenerationComplete(taskId);
        resolve();
      } else if (data.status === 'error') {
        eventSource.close();
        localStorage.removeItem('activeTaskId');
        setRunningUI(false);
        reject(new Error(data.error || '生成失败'));
      }
    };
    eventSource.onerror = () => {
      eventSource.close();
      headerStatus.textContent = '连接中断';
    };
  });
}

function onGenerationComplete(taskId) {
  resultSection.classList.remove('hidden');
  resultVideo.src = `/api/download/${taskId}`;
  downloadBtn.href = `/api/download/${taskId}`;
  setRunningUI(false);
  document.getElementById('feedContainer').scrollTo({ top: 0, behavior: 'smooth' });
}

generateBtn.addEventListener('click', startGeneration);
init();
