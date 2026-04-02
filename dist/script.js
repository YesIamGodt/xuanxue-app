const _b='https://xuanxue-app-production.up.railway.app';async function _t(u,o={}){const c=new AbortController(),t=setTimeout(()=>c.abort(),8000);try{const r=await fetch(u,{...o,signal:c.signal});clearTimeout(t);return r}catch(e){clearTimeout(t);if(e.name==='AbortError')throw new Error('网络超时');throw e}};

// 玄学互动平台 - 完全重构版

'use strict';

// ========== State ==========
const state = {
    userProfile: null,
    selectedHotspot: null,
    divineHistory: [],
    splashHidden: false,
    fortuneResult: null,
    todayDate: '',
    shichen: '',
    hotTopics: [],
    fateImpactTopics: [],
    fateAnalysis: '',
    systemReady: false,
    bannerLoaded: false, // 防止 banner 重复加载
};

// ========== PWA / Service Worker ==========
var deferredPrompt = null;

// 注册 Service Worker（PWA 离线能力 + 可安装）
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        navigator.serviceWorker.register('./sw.js').then(function(reg) {
            console.log('[PWA] Service Worker registered:', reg.scope);
        }).catch(function(err) {
            console.warn('[PWA] Service Worker registration failed:', err);
        });
    });

    // 监听可安装事件
    window.addEventListener('beforeinstallprompt', function(e) {
        e.preventDefault();
        deferredPrompt = e;
        // 显示安装提示条
        var banner = document.getElementById('pwa-install-banner');
        if (banner) {
            banner.style.display = 'flex';
        }
    });

    // App 已安装
    window.addEventListener('appinstalled', function() {
        var banner = document.getElementById('pwa-install-banner');
        if (banner) banner.style.display = 'none';
        deferredPrompt = null;
        // 提示用户
        setTimeout(function() {
            alert('✨ 玄学互动已安装到您的设备！\n在桌面或应用列表中找到「玄学互动」即可打开。');
        }, 500);
    });
}

function doPwaInstall() {
    if (!deferredPrompt) {
        // 如果没有 deferredPrompt，提示用户在浏览器菜单手动安装
        alert('请点击浏览器菜单（⋮ 或 ≡）\n选择「添加到主屏幕」或「安装」');
        return;
    }
    deferredPrompt.prompt();
    deferredPrompt.userChoice.then(function(choice) {
        if (choice.outcome === 'accepted') {
            console.log('[PWA] User accepted install');
        } else {
            console.log('[PWA] User dismissed install');
        }
        deferredPrompt = null;
        var banner = document.getElementById('pwa-install-banner');
        if (banner) banner.style.display = 'none';
    });
}

function dismissPwaBanner() {
    var banner = document.getElementById('pwa-install-banner');
    if (banner) banner.style.display = 'none';
    // 记住用户不喜欢提示（本次会话不再显示）
    sessionStorage.setItem('pwa_banner_dismissed', '1');
}

// ========== Utilities ==========
function $(id) { return document.getElementById(id); }
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}
function formatDate(isoString) {
    const d = new Date(isoString);
    return `${d.getMonth()+1}月${d.getDate()}日 ${d.getHours()}:${String(d.getMinutes()).padStart(2,'0')}`;
}
function generateId() { return Date.now().toString(36) + Math.random().toString(36).substr(2); }

// 去掉 think 标签和多余空白
function cleanAIResponse(text) {
    if (!text) return '';
    return text
        .replace(/<\/?think[^>]*>/gi, '')
        .replace(/<think>[\s\S]*?<\/think>/gi, '')
        .replace(/<think>/g, '')
        .replace(/<\/think>/g, '')
        .replace(/```[^`]*```/g, '')
        .replace(/```/g, '')
        .replace(/\n{3,}/g, '\n\n')
        .trim();
}

// ========== Boot ==========
// 绝对可靠的启动：5秒强制显示主屏，不管网络/错误/缓存任何情况
(function bootstrap() {
    var splash = document.getElementById('splash-screen');
    var mainScreen = document.getElementById('main-screen');

    // 1. 立即隐藏 Splash，显示主 DOM 容器（CSS 有 !important，必须用 setProperty）
    if (splash) {
        splash.style.setProperty('display', 'none', 'important');
        splash.style.setProperty('visibility', 'hidden', 'important');
    }
    if (mainScreen) {
        mainScreen.style.setProperty('display', 'flex', 'important');
        mainScreen.style.setProperty('visibility', 'visible', 'important');
    }

    // 2. 5秒兜底：任何情况5秒后必定完成初始化
    var failSafe = setTimeout(function() {
        checkUserProfile();
    }, 5000);

    // 3. 并行加载数据
    Promise.all([
        loadTodayDate(),
        loadUserProfile(),
    ]).then(function() {
        clearTimeout(failSafe);
        checkUserProfile();
    }).catch(function() {
        clearTimeout(failSafe);
        checkUserProfile();
    });
})();

function loadTodayDate() {
    return new Promise(function(resolve) {
        var xhr = new XMLHttpRequest();
        xhr.open('GET', '/api/date', true);
        xhr.timeout = 5000;
        xhr.onload = function() {
            if (xhr.status === 200) {
                try {
                    var data = JSON.parse(xhr.responseText);
                    state.todayDate = data.today || '';
                    state.shichen = data.shichen || '';
                } catch(e) {}
            }
            resolve();
        };
        xhr.onerror = resolve;
        xhr.ontimeout = resolve;
        xhr.send(null);
    });
}

function loadUserProfile() {
    return new Promise(function(resolve) {
        var saved = localStorage.getItem('userProfile');
        if (saved) {
            try {
                state.userProfile = JSON.parse(saved);
            } catch(e) {}
        }
        resolve();
    });
}

function hideSplash() {
    var splash = document.getElementById('splash-screen');
    if (splash) splash.style.display = 'none';
    checkUserProfile();
}

function checkUserProfile() {
    // URL参数跳过模式：直接进入主屏
    if (new URLSearchParams(location.search).get('skip') === '1') {
        loadMainScreen();
        return;
    }
    const saved = localStorage.getItem('userProfile');
    if (saved) {
        try {
            state.userProfile = JSON.parse(saved);
            loadMainScreen();
        } catch (e) {
            showSetupScreen();
        }
    } else {
        showSetupScreen();
    }
}

// ========== Setup Screen ==========
function showSetupScreen() {
    showScreen('setup-screen');
}

async function saveUserProfile() {
    const name = $('user-name').value.trim();
    const birthday = $('user-birthday').value;
    const time = $('user-time').value;
    const location = $('user-location').value.trim();

    if (!name) { alert('请输入姓名'); return; }
    if (!birthday) { alert('请选择出生日期'); return; }

    const [year, month, day] = birthday.split('-').map(Number);
    const profile = {
        name, year, month, day,
        time_str: time || '00:00',
        gender: document.querySelector('.gender-btn.active')?.dataset.gender || '男',
        location: location || '未知',
    };

    localStorage.setItem('userProfile', JSON.stringify(profile));
    state.userProfile = profile;

    // 必须 await，等后端真正保存完毕再进行占卜
    try {
        await _t('https://xuanxue-app-production.up.railway.app/api/profile/set', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(profile),
        });
    } catch(e) {
        console.warn('Profile API failed, continuing anyway:', e);
    }

    // 重新加载日期（更新八字）
    await loadTodayDate();

    // 立即显示欢迎卦屏，同时拉取今日运势
    showScreen('welcome-card');
    doWelcomeDivine();
}

async function doWelcomeDivine() {
    const card = $('welcome-divine-card');
    const footer = $('welcome-footer');
    if (!card || !footer) return;

    // 检查是否要跳过（URL参数或localStorage）
    if (new URLSearchParams(location.search).get('skip') === '1') {
        enterMainFromWelcome();
        return;
    }

    // 显示加载状态
    card.innerHTML = '<div class="wdc-level">命盘运转中...</div>' +
        '<div class="wdc-date">' + (state.todayDate || '') + ' ' + (state.shichen || '') + '</div>' +
        '<div class="wdc-divine-text loading-text">解读命运中，请稍候...</div>' +
        '<button class="btn btn-secondary btn-full" style="margin-top:16px;font-size:13px" onclick="enterMainFromWelcome()">跳过，直接进入</button>';

    try {
        const res = await _t('https://xuanxue-app-production.up.railway.app/api/divination/daily', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: null }),
        });
        const data = await res.json();
        if (!data.success) { renderWelcomeError(); return; }

        const f = data.data;
        const level = f.fortune_level || '平';
        const tags = [];
        if (f.lucky_directions?.length) tags.push('\u5409\u65b9\uff1a' + f.lucky_directions.join('\u00b7'));
        if (f.lucky_color) tags.push('\u5e78\u8fd0\u8272\uff1a' + f.lucky_color);
        if (f.lucky_number) tags.push('\u5e78\u8fd0\u6570\uff1a' + f.lucky_number);

        card.innerHTML =
            '<div class="wdc-level ' + level + '">' + level + '</div>' +
            '<div class="wdc-date">' + (f.today || '') + ' ' + (f.shichen || '') + '</div>' +
            '<div class="wdc-divine-text">' + escapeHtml(f.day_fortune || '\u4eca\u65e5\u547d\u6570\u5df2\u663e\u73b0\uff0c\u9759\u5f85\u6709\u7f18\u4eba\u3002') + '</div>' +
            (tags.length ? '<div class="wdc-tags">' + tags.map(function(t) { return '<span class="wdc-tag">' + escapeHtml(t) + '</span>'; }).join('') + '</div>' : '');

        // 保存记录
        _t('https://xuanxue-app-production.up.railway.app/api/divination/record', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                record_type: 'daily',
                bazi_summary: f.bazi_summary || '',
                ai_response: f.ai_full_response || '',
                daily_fortune: f,
            }),
        }).catch(function() {});

        footer.style.setProperty('display', 'block', 'important');
    } catch (e) {
        renderWelcomeError();
    }
}

function renderWelcomeError() {
    const card = $('welcome-divine-card');
    const footer = $('welcome-footer');
    if (card) {
        card.innerHTML = `
            <div class="wdc-level 平">平</div>
            <div class="wdc-date">${state.todayDate || new Date().toLocaleDateString('zh-CN')}</div>
            <div class="wdc-divine-text">命盘已锁定，大师稍后将为您指点迷津。命格已存，稍后可随时占卜。</div>
        `;
    }
    if (footer) footer.style.setProperty('display', 'block', 'important');
}

function enterMainFromWelcome() {
    loadMainScreen();
}

// ========== Main Screen ==========
function loadMainScreen() {
    // 确保欢迎卦屏隐藏（用 !important 覆盖 CSS）
    var wc = document.getElementById('welcome-card');
    if (wc) {
        wc.style.setProperty('display', 'none', 'important');
        wc.style.setProperty('visibility', 'hidden', 'important');
    }
    showScreen('main-screen');
    initializeTabs();
    initializeHotspots();
    initializeDivine();
    initializeHepan();
    initializeCrystal();
    initializeProfile();

    // 老用户：自动加载今日运势Banner（只加载一次）
    if (state.userProfile && !state.bannerLoaded) {
        state.bannerLoaded = true;
        autoLoadFortuneBanner();
    }
}

async function autoLoadFortuneBanner() {
    const profile = state.userProfile;
    if (!profile) return;

    // 设置问候语
    const helloEl = $('fb-hello');
    const nameEl = $('fb-name');
    if (helloEl) {
        const hour = new Date().getHours();
        if (hour < 12) helloEl.textContent = '早安 ✦';
        else if (hour < 18) helloEl.textContent = '午安 ✦';
        else helloEl.textContent = '晚安 ✦';
    }
    if (nameEl) nameEl.textContent = profile.name + '\uff0c\u5927\u5e08\u6709\u793c';

    try {
        const res = await _t('https://xuanxue-app-production.up.railway.app/api/divination/daily', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: null }),
        });
        const data = await res.json();
        if (!data.success) { renderBannerError(); return; }

        const f = data.data;
        const levelEl = $('fb-level-badge');
        if (levelEl) {
            levelEl.textContent = f.fortune_level || '\u5e73';
            levelEl.className = 'fb-level-badge ' + (f.fortune_level || '\u5e73');
        }
        const textEl = $('fb-divine-text');
        if (textEl) textEl.textContent = f.day_fortune || '\u4eca\u65e5\u547d\u6570\u5df2\u663e\u73b0\uff0c\u9759\u5f85\u6709\u7f18\u4eba\u3002';

        const metaEl = $('fb-meta');
        const dirEl = $('fb-dir');
        const colorEl = $('fb-color');
        const numEl = $('fb-num');
        if (metaEl) {
            if (f.lucky_directions?.length) {
                dirEl.textContent = '\u5409\u65b9 ' + f.lucky_directions.join('\u00b7');
                dirEl.style.display = '';
            }
            if (f.lucky_color) {
                colorEl.textContent = '\u5e78\u8fd0 ' + f.lucky_color;
                colorEl.style.display = '';
            }
            if (f.lucky_number) {
                numEl.textContent = '\u5e78\u8fd0\u6570 ' + f.lucky_number;
                numEl.style.display = '';
            }
            metaEl.style.display = 'flex';
        }
    } catch (e) {
        renderBannerError();
    }
}

function renderBannerError() {
    const textEl = $('fb-divine-text');
    const levelEl = $('fb-level-badge');
    if (textEl) textEl.textContent = '\u4eca\u65e5\u547d\u6570\u5df2\u9501\u5b9a\uff0c\u9759\u5f85\u6709\u7f18\u4eba\u3002';
    if (levelEl) { levelEl.textContent = '\u2716'; levelEl.className = 'fb-level-badge \u5e73'; }
}

// ========== Navigation ==========
let currentTab = 'trending';

function initializeTabs() {
    document.querySelectorAll('.nav-item').forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.dataset.tab;
            switchTab(tab);
        });
    });
}

function switchTab(tabId) {
    currentTab = tabId;

    // 更新 nav
    document.querySelectorAll('.nav-item').forEach(b => {
        b.classList.toggle('active', b.dataset.tab === tabId);
    });

    // 更新 tab 内容
    document.querySelectorAll('.tab-content').forEach(t => {
        // 用 style 直接控制，不用 class，避免冲突
        t.style.display = (t.id === `tab-${tabId}`) ? 'flex' : 'none';
    });

    // 加载 tab 数据
    if (tabId === 'crystal') {
        loadHistory();
    } else if (tabId === 'trending') {
        // 已自动加载
    }
}

// ========== Screen Management ==========
function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(function(s) {
        if (s.id === screenId) {
            s.style.setProperty('display', 'flex', 'important');
            s.style.setProperty('visibility', 'visible', 'important');
        } else {
            s.style.setProperty('display', 'none', 'important');
            s.style.setProperty('visibility', 'hidden', 'important');
        }
    });
}

// ========== Hotspot / Trending ==========
function initializeHotspots() {
    loadHotspots();
}

async function loadHotspots() {
    const list = $('hotspot-list');
    if (!list) return;
    list.innerHTML = `
        <div class="loading-indicator">
            <div class="loading-spinner"></div>
            <span>命理师解读中...</span>
        </div>`;

    let topics = [];

    // 优先尝试直连 API（绕过 Railway 出站限制）
    try {
        const res = await _t('https://xuanxue-app-production.up.railway.app/api/trending/direct');
        const data = await res.json();
        if (data.success && data.topics && data.topics.length) {
            topics = data.topics;
        }
    } catch (e) {}

    // 如果直连失败，尝试原 API
    if (!topics.length) {
        try {
            const res = await _t('https://xuanxue-app-production.up.railway.app/api/trending?source=baidu&limit=20');
            const data = await res.json();
            topics = data.topics || [];
        } catch (e) {}
    }

    if (!topics.length) {
        list.innerHTML = '<div class="loading-indicator"><span>热点加载中，请稍候...</span></div>';
        return;
    }

    // 保存到state，供命运联动使用
    state.hotTopics = topics;

    // 并行：渲染热点列表 + 调用命运联动API
    renderHotspotList(topics);
    loadFateImpact(topics);
    loadFortuneTrend();
}

function renderHotspotList(topics) {
    const list = $('hotspot-list');
    if (!list) return;

    // 从命中热点中找出有impact的标题
    const impactTitles = new Set(state.fateImpactTopics ? state.fateImpactTopics.map(t => t.title) : []);

    list.innerHTML = topics.map(t => {
        const hasImpact = impactTitles.has(t.title);
        const impactTag = hasImpact ? '<span class="hotspot-impact-tag">命格相关</span>' : '';
        return `
            <div class="hotspot-card${hasImpact ? ' has-impact' : ''}" onclick="showHotspotDetail(${JSON.stringify(t.title).replace(/"/g, '&quot;')}, ${JSON.stringify(t).replace(/"/g, '&quot;')})">
                <div class="hotspot-rank">${t.rank}</div>
                <div class="hotspot-body">
                    <div class="hotspot-title">${escapeHtml(t.title)}</div>
                </div>
                ${impactTag}
            </div>`;
    }).join('');
}

async function loadFateImpact(topics) {
    if (!state.userProfile || !topics.length) return;

    try {
        const res = await _t('https://xuanxue-app-production.up.railway.app/api/fate/impact', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic: '热点分析', topic_data: { topics } }),
        });
        const data = await res.json();
        if (!data.success) return;

        // 保存命格相关热点
        state.fateImpactTopics = data.top_topics || [];
        state.fateAnalysis = data.analysis || '';

        // 重新渲染热点列表（加标签）
        renderHotspotList(topics);

        // 显示命运联动区域
        renderFateImpactCards(data.top_topics || []);
    } catch(e) {
        console.warn('Fate impact failed:', e);
    }
}

function renderFateImpactCards(topTopics) {
    const section = $('fate-impact-section');
    const list = $('fate-impact-list');
    if (!section || !list) return;

    if (!topTopics.length) {
        section.style.display = 'none';
        return;
    }

    section.style.display = 'block';
    list.innerHTML = topTopics.slice(0, 3).map((t, i) => {
        const arrow = t.direction === '有利' ? '↑' : t.direction === '不利' ? '↓' : '→';
        const arrowClass = t.direction === '有利' ? 'good' : t.direction === '不利' ? 'bad' : 'neutral';
        return `
            <div class="fate-impact-card" onclick="showHotspotDetail(${JSON.stringify(t.title || '').replace(/"/g, '&quot;')}, ${JSON.stringify(t).replace(/"/g, '&quot;')})">
                <div class="fic-rank">${i + 1}</div>
                <div class="fic-body">
                    <div class="fic-title">${escapeHtml(t.title || '')}</div>
                    <div class="fic-impact">🎯 ${escapeHtml(t.impact || '')}</div>
                </div>
                <div class="fic-arrow ${arrowClass}">${arrow}</div>
            </div>`;
    }).join('');
}

async function loadFortuneTrend() {
    try {
        const res = await _t('https://xuanxue-app-production.up.railway.app/api/fate/trend');
        const data = await res.json();
        if (!data.success) return;

        const bar = $('fortune-trend-bar');
        const arrow = $('trend-arrow');
        const msg = $('trend-msg');
        if (!bar) return;

        const trend = data.trend || '→';
        const arrowTxt = trend === '↑' ? '↑' : trend === '↓' ? '↓' : '→';
        const arrowClass = trend === '↑' ? 'up' : trend === '↓' ? 'down' : 'stable';

        if (arrow) {
            arrow.textContent = arrowTxt;
            arrow.className = 'trend-arrow ' + arrowClass;
        }
        if (msg) {
            msg.textContent = data.message || '运势平稳';
        }
        bar.style.display = 'flex';
    } catch(e) {}
}

function openTimingAdvisor() {
    const modal = $('timing-modal');
    if (modal) {
        modal.style.display = 'flex';
        const result = $('timing-result');
        if (result) {
            result.style.display = 'none';
            result.innerHTML = '';
        }
    }
}

function closeTimingModal() {
    const modal = $('timing-modal');
    if (modal) modal.style.display = 'none';
}

async function doTimingAdvice() {
    const input = $('timing-question');
    const result = $('timing-result');
    if (!input || !result) return;

    const question = input.value.trim();
    if (!question) { alert('请输入您想做的事情'); return; }

    result.innerHTML = '<div class="loading-spinner small"></div><span style="color:#a78bfa;font-size:13px">命理师推演中...</span>';
    result.style.display = 'block';

    try {
        const res = await _t('https://xuanxue-app-production.up.railway.app/api/fate/timing', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: question }),
        });
        const data = await res.json();
        result.style.display = 'block';
        result.innerHTML = '<div style="font-size:14px;color:#fcd9b6;line-height:1.7">' + escapeHtml(data.response || '天机难测，请稍后再试。') + '</div>';
    } catch(e) {
        result.innerHTML = '<div style="color:#f87171;font-size:13px">网络错误，请重试</div>';
    }
}

// ========== Hotspot Detail ==========
function showHotspotDetail(title, topic) {
    state.selectedHotspot = topic;
    $('modal-title').textContent = title;
    $('hotspot-detail').textContent = `热度：${topic.hot_value || '未知'}`;

    // 显示内容摘要加载状态
    $('content-summary').innerHTML = '<div class="loading-spinner small"></div><span>正在获取内容摘要...</span>';
    $('content-summary').classList.add('loading');

    // 显示命理解读加载状态
    $('hotspot-analysis').innerHTML = '<div class="loading-spinner small"></div><span>命理师解读中...</span>';
    $('hotspot-analysis').classList.add('loading');
    $('hotspot-modal').style.display = 'flex';

    // 并行请求内容摘要 + 命理解读
    Promise.all([
        fetchHotspotContent(title, topic),
        analyzeHotspot(title, topic),
    ]);
}

function closeHotspotModal() {
    $('hotspot-modal').style.display = 'none';
}

async function doPredictFuture() {
    const btn = $('btn-predict-future');
    if (!btn) return;
    const topic = state.selectedHotspot;
    const title = $('modal-title')?.textContent || '';
    if (!topic || !title) return;

    btn.disabled = true;
    btn.textContent = '⏱ 命运推演中...';

    try {
        const res = await _t('https://xuanxue-app-production.up.railway.app/api/hotspot/predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic: title, topic_data: topic }),
        });
        const data = await res.json();

        // 显示预测结果
        const analysisEl = $('hotspot-analysis');
        if (analysisEl && data.success) {
            const f = data.data;
            const levelColor = { '大吉': '🟢', '吉': '🟣', '平': '⚪', '凶': '🟠', '大凶': '🔴' }[f.level] || '⚪';
            analysisEl.innerHTML = `
                <div class="prediction-result">
                    <div class="pred-badge ${f.level}">${levelColor} ${f.level}</div>
                    <div class="pred-section">
                        <div class="pred-label">📅 明日预测</div>
                        <div class="pred-text">${escapeHtml(f.prediction)}</div>
                    </div>
                    <div class="pred-section">
                        <div class="pred-label">💡 命理提示</div>
                        <div class="pred-text">${escapeHtml(f.advice)}</div>
                    </div>
                </div>
            `;
            btn.textContent = '✓ 预测完成';
        } else {
            btn.textContent = '⏱ 预测未来';
            btn.disabled = false;
        }
    } catch(e) {
        btn.textContent = '⏱ 预测未来';
        btn.disabled = false;
    }
}

async function fetchHotspotContent(title, topic) {
    const el = $('content-summary');
    try {
        const res = await _t('https://xuanxue-app-production.up.railway.app/api/hotspot/content', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic: title, url: topic.url || null }),
        });
        const data = await res.json();
        el.classList.remove('loading');
        if (data.summary) {
            el.textContent = data.summary;
        } else if (data.content) {
            // 没有 AI 摘要就用抓取到的原始内容（截断显示）
            const text = data.content.length > 300
                ? data.content.substring(0, 300) + '…'
                : data.content;
            el.textContent = text;
        } else {
            el.textContent = '暂无内容摘要，请查看下方命理师的解读';
        }
    } catch (e) {
        el.classList.remove('loading');
        el.textContent = '无法获取内容摘要，请查看下方命理师的解读';
    }
}

async function analyzeHotspot(title, topic) {
    const el = $('hotspot-analysis');
    try {
        const res = await _t('https://xuanxue-app-production.up.railway.app/api/hotspot/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ topic: title, url: topic.url || null }),
        });
        const data = await res.json();
        const text = cleanAIResponse(data.analysis || '暂无解读');
        el.classList.remove('loading');
        el.textContent = text;
    } catch (e) {
        el.classList.remove('loading');
        el.textContent = '解读暂时无法获取，请稍后再试。';
    }
}

// ========== Divine Master Chat ==========
function initializeDivine() {
    const input = $('divine-input');
    const sendBtn = $('divine-send-btn');

    if (sendBtn) {
        sendBtn.addEventListener('click', sendDivineMessage);
    }
    if (input) {
        input.addEventListener('keydown', e => {
            if (e.key === 'Enter') sendDivineMessage();
        });
    }
}

async function sendDivineMessage() {
    const input = $('divine-input');
    if (!input) return;
    const text = input.value.trim();
    if (!text) return;

    input.value = '';
    appendChatMessage(text, 'user');

    const thinkingId = appendChatMessage('✦ 命理运转中...', 'ai', true);

    // 获取当前实时时间（秒级）
    const now = new Date();
    const currentDate = now.getFullYear() + '年' + String(now.getMonth()+1).padStart(2,'0') + '月' + String(now.getDate()).padStart(2,'0') + '日';
    const currentTime = String(now.getHours()).padStart(2,'0') + ':' + String(now.getMinutes()).padStart(2,'0') + ':' + String(now.getSeconds()).padStart(2,'0');
    const currentHour = now.getHours();

    // 时辰计算
    const shichenMap = {
        23: "子时", 0: "子时", 1: "丑时", 2: "丑时",
        3: "寅时", 4: "寅时", 5: "卯时", 6: "卯时",
        7: "辰时", 8: "辰时", 9: "巳时", 10: "巳时",
        11: "午时", 12: "午时", 13: "未时", 14: "未时",
        15: "申时", 16: "申时", 17: "酉时", 18: "酉时",
        19: "戌时", 20: "戌时", 21: "亥时", 22: "亥时",
    };
    const currentShichen = shichenMap[currentHour] || "子时";

    try {
        const res = await _t('https://xuanxue-app-production.up.railway.app/api/fate/dialogue', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: text,
                conversation_history: state.divineHistory.slice(-10),
                today_date: currentDate + ' ' + currentTime,
                shichen: currentShichen + '（' + currentTime + '）',
            }),
        });
        const data = await res.json();

        if (thinkingId) $(thinkingId)?.remove();

        const response = cleanAIResponse(data.response || '大师暂时无法回应，请稍后再试。');
        appendChatMessage(response, 'ai');

        state.divineHistory.push({ role: 'user', content: text });
        state.divineHistory.push({ role: 'assistant', content: response });
    } catch (e) {
        if (thinkingId) $(thinkingId)?.remove();
        appendChatMessage('大师暂时无法回应，请稍后再试。', 'ai');
    }
}

function appendChatMessage(text, role, isThinking = false) {
    const container = $('divine-chat');
    if (!container) return;

    // Remove welcome on first real message
    const welcome = $('divine-welcome');
    if (welcome && role === 'user') welcome.remove();

    const id = 'msg-' + generateId();
    const avatar = role === 'ai' ? '🔮' : '👤';
    const displayText = escapeHtml(text);

    const html = `
        <div class="chat-message ${role}" id="${id}">
            <div class="msg-avatar">${avatar}</div>
            <div class="msg-bubble${isThinking ? ' fading' : ''}">${displayText}</div>
        </div>`;
    container.insertAdjacentHTML('beforeend', html);

    // 确保输入框可见
    requestAnimationFrame(() => {
        container.scrollTop = container.scrollHeight;
        const input = $('divine-input');
        if (input) input.focus();
    });
    return id;
}

// ========== Hepan (双人合盘) ==========
function initializeHepan() {
    // 绑定性别按钮
    document.querySelectorAll('.hepan-gender .gender-btn').forEach(function(btn) {
        btn.addEventListener('click', function() {
            var person = this.dataset.person;
            document.querySelectorAll('.hepan-gender[data-person="' + person + '"] .gender-btn').forEach(function(b) {
                b.classList.remove('active');
            });
            this.classList.add('active');
        });
    });
}

async function doHepan() {
    var name1 = $('hepan-name1')?.value.trim();
    var name2 = $('hepan-name2')?.value.trim();
    var birthday1 = $('hepan-birthday1')?.value;
    var birthday2 = $('hepan-birthday2')?.value;

    if (!name1) { alert('请输入甲方姓名'); return; }
    if (!name2) { alert('请输入乙方姓名'); return; }
    if (!birthday1) { alert('请选择甲方出生日期'); return; }
    if (!birthday2) { alert('请选择乙方出生日期'); return; }

    var time1 = $('hepan-time1')?.value || '00:00';
    var time2 = $('hepan-time2')?.value || '00:00';
    var gender1 = document.querySelector('.hepan-gender[data-person="1"] .gender-btn.active')?.dataset.gender || '男';
    var gender2 = document.querySelector('.hepan-gender[data-person="2"] .gender-btn.active')?.dataset.gender || '男';

    var btn = $('hepan-submit-btn');
    var resultEl = $('hepan-result');
    if (btn) {
        btn.disabled = true;
        btn.textContent = '命盘运算中...';
    }

    // 显示加载状态
    if (resultEl) {
        resultEl.style.display = 'block';
        resultEl.innerHTML = '<div class="hepan-loading"><div class="loading-spinner large"></div><p class="hepan-loading-text">合盘解读中<span class="hepan-loading-dots"><span>.</span><span>.</span><span>.</span></span></p></div>';
    }

    try {
        var res = await _t('https://xuanxue-app-production.up.railway.app/api/hepan', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name1: name1,
                year1: parseInt(birthday1.split('-')[0]),
                month1: parseInt(birthday1.split('-')[1]),
                day1: parseInt(birthday1.split('-')[2]),
                time_str1: time1,
                gender1: gender1,
                name2: name2,
                year2: parseInt(birthday2.split('-')[0]),
                month2: parseInt(birthday2.split('-')[1]),
                day2: parseInt(birthday2.split('-')[2]),
                time_str2: time2,
                gender2: gender2,
            }),
        });

        var data = await res.json();
        if (!data.success) {
            throw new Error(data.detail || '合盘失败');
        }

        renderHepanResult(data.data);
    } catch (e) {
        if (resultEl) {
            resultEl.innerHTML = '<div class="hepan-loading"><p class="hepan-loading-text">合盘暂时无法进行，请稍后重试</p></div>';
        }
        console.error('Hepan error:', e);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.textContent = '☯ 开始合盘';
        }
    }
}

function renderHepanResult(data) {
    var resultEl = $('hepan-result');
    if (!resultEl) return;

    var level = data.level || '平';
    var levelClass = '';
    if (level === '上吉' || level === '吉') levelClass = 'success';
    else if (level === '小凶' || level === '大凶') levelClass = 'warning';

    // 分析项
    var items = [
        { icon: '🎯', title: '性格相性', text: data.性格相性 || '' },
        { icon: '💰', title: '财运协同', text: data.财运协同 || '' },
        { icon: '💕', title: '感情匹配', text: data.感情匹配 || '' },
        { icon: '⚠️', title: '冲突预警', text: data.冲突预警 || '暂无明显冲突', isWarning: data.冲突预警 && data.冲突预警.indexOf('暂无') === -1 },
        { icon: '🤝', title: '最佳相处', text: data.最佳相处 || '' },
        { icon: '☯', title: '互补五行', text: data.互补五行 || '' },
    ];

    var itemsHtml = items.filter(function(item) {
        return item.text;
    }).map(function(item) {
        var cls = item.isWarning ? 'warning' : (item.text.indexOf('暂无') !== -1 ? '' : (levelClass === 'success' ? 'success' : ''));
        return '<div class="hepan-analysis-item">' +
            '<div class="hepan-analysis-title">' + item.icon + ' ' + item.title + '</div>' +
            '<div class="hepan-analysis-text ' + cls + '">' + escapeHtml(item.text) + '</div>' +
        '</div>';
    }).join('');

    resultEl.innerHTML = '' +
        '<div class="hepan-level-badge ' + escapeHtml(level) + '">' + escapeHtml(level) + '</div>' +
        '<div class="hepan-summary">' + escapeHtml(data.summary || '') + '</div>' +
        '<div class="hepan-cards">' +
            '<div class="hepan-card">' +
                '<div class="hepan-card-title">' + escapeHtml(data.p1?.split('：')[0] || name1 || '甲方') + '</div>' +
                '<div class="hepan-card-bazi">' + escapeHtml(data.p1 || '') + '</div>' +
            '</div>' +
            '<div class="hepan-card">' +
                '<div class="hepan-card-title">' + escapeHtml(data.p2?.split('：')[0] || name2 || '乙方') + '</div>' +
                '<div class="hepan-card-bazi">' + escapeHtml(data.p2 || '') + '</div>' +
            '</div>' +
        '</div>' +
        '<div class="hepan-analysis">' + itemsHtml + '</div>' +
        '<button class="hepan-share-btn" onclick="shareHepanResult()">📤 分享给朋友</button>';
}

function shareHepanResult() {
    var resultEl = $('hepan-result');
    if (!resultEl) return;

    var level = $('hepan-level-badge')?.textContent || '';
    var summary = $('hepan-summary')?.textContent || '';
    var p1 = $('hepan-p1-title')?.textContent || '';
    var p2 = $('hepan-p2-title')?.textContent || '';

    var text = '☯ 我的命缘合盘\n' +
        p1 + ' × ' + p2 + '\n' +
        '契合等级：' + level + '\n' +
        summary.substring(0, 100);

    // 尝试复制到剪贴板
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(function() {
            alert('合盘结果已复制到剪贴板，可直接粘贴分享！');
        }).catch(function() {
            alert(text);
        });
    } else {
        alert(text);
    }
}

// ========== Crystal Ball / Divination ==========
function initializeCrystal() {
    const ball = $('crystal-ball');
    if (ball) {
        ball.addEventListener('click', () => doCrystalDivination(null));
    }

    const reBtn = $('re-divine-btn');
    if (reBtn) {
        reBtn.addEventListener('click', () => {
            const q = $('divine-question-input')?.value?.trim() || null;
            doCrystalDivination(q);
        });
    }
}

async function doCrystalDivination(userQuestion = null) {
    const container = $('crystal-container');
    const loading = $('crystal-loading');
    const result = $('fortune-result');

    if (container) container.style.display = 'none';
    if (result) result.style.display = 'none';
    if (loading) loading.style.display = 'flex';

    try {
        const res = await _t('https://xuanxue-app-production.up.railway.app/api/divination/daily', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ question: userQuestion }),
        });

        if (!res.ok && res.status !== 200) {
            throw new Error('\u8bf7\u5148\u8bbe\u7f6e\u60a8\u7684\u51fa\u751f\u4fe1\u606f');
        }

        const data = await res.json();
        if (!data.success) {
            throw new Error(data.detail || '\u5360\u5355\u4e34\u65f6\u65e0\u6cd5\u8fdb\u884c');
        }

        state.fortuneResult = data.data;
        if (loading) loading.style.display = 'none';
        if (result) result.style.display = 'block';
        renderFortuneResult(data.data);
        loadHistory();
    } catch (e) {
        if (loading) loading.style.display = 'none';
        if (container) container.style.display = 'flex';
        alert('\u5360\u5355\u4e34\u65f6\u65e0\u6cd5\u8fdb\u884c\uff1a' + (e.message || '\u8bf7\u5148\u8bbe\u7f6e\u60a8\u7684\u51fa\u751f\u4fe1\u606f'));
    }
}

function renderFortuneResult(f) {
    if (!f) return;

    // 运势等级
    const levelEl = $('fortune-level');
    if (levelEl) {
        levelEl.textContent = f.fortune_level || '平';
        levelEl.className = 'fortune-level ' + (f.fortune_level || '平');
    }

    const dateEl = $('fortune-date');
    if (dateEl) dateEl.textContent = `${f.today || ''} ${f.shichen || ''}`;

    const baziEl = $('bazi-brief');
    if (baziEl) {
        baziEl.textContent = f.bazi_summary
            ? f.bazi_summary.replace(/【用户玄学画像】/g, '').trim()
            : '';
    }

    const yearEl = $('year-fortune');
    if (yearEl) yearEl.textContent = f.year_fortune || '';

    const monthEl = $('month-fortune');
    if (monthEl) monthEl.textContent = f.month_fortune || '';

    const dayEl = $('day-fortune');
    if (dayEl) dayEl.textContent = f.day_fortune || '';

    const dirsEl = $('lucky-directions');
    if (dirsEl) dirsEl.textContent = (f.lucky_directions || []).join('、') || '东、南';

    const colorEl = $('lucky-color');
    if (colorEl) colorEl.textContent = f.lucky_color || '金色';

    const numEl = $('lucky-number');
    if (numEl) numEl.textContent = f.lucky_number || '8';

    const healthEl = $('health-advice');
    if (healthEl) healthEl.textContent = f.health_advice || '注意休息';

    // 大师解答
    const qaBlock = $('question-answer-block');
    const qaText = $('qa-text');
    const q = cleanAIResponse(f.question_answer || '');
    if (q && qaBlock && qaText) {
        qaBlock.style.display = 'block';
        qaText.textContent = q;
    } else if (qaBlock) {
        qaBlock.style.display = 'none';
    }
}

// ========== Divination History ==========
async function loadHistory() {
    const list = $('history-list');
    if (!list) return;

    try {
        const res = await _t('https://xuanxue-app-production.up.railway.app/api/divination/history?limit=20');
        const data = await res.json();
        const records = data.records || [];

        if (!records.length) {
            list.innerHTML = '<div class="history-empty">暂无占卜记录</div>';
            return;
        }

        list.innerHTML = records.map(r => {
            const preview = cleanAIResponse(r.question || r.ai_response || '').substring(0, 60);
            return `
                <div class="history-item" onclick="showHistoryDetail(${JSON.stringify(r).replace(/"/g, '&quot;')})">
                    <div class="history-header">
                        <span class="history-type">${r.type === 'daily' ? '✨ 今日运势' : '💬 占卜问答'}</span>
                        <span class="history-time">${formatDate(r.timestamp)}</span>
                    </div>
                    <div class="history-preview">${escapeHtml(preview)}</div>
                </div>`;
        }).join('');
    } catch (e) {
        list.innerHTML = '<div class="history-empty">无法加载历史记录</div>';
    }
}

function showHistoryDetail(record) {
    const container = $('crystal-container');
    const result = $('fortune-result');

    if (container) container.style.display = 'none';
    if (result) result.style.display = 'block';

    if (record.type === 'daily' && record.daily_fortune) {
        renderFortuneResult(record.daily_fortune);
    } else {
        const levelEl = $('fortune-level');
        if (levelEl) {
            levelEl.textContent = record.type === 'daily' ? '✨' : '💬';
            levelEl.className = 'fortune-level 平';
        }
        const dateEl = $('fortune-date');
        if (dateEl) dateEl.textContent = formatDate(record.timestamp);
        const baziEl = $('bazi-brief');
        if (baziEl) baziEl.textContent = record.bazi_summary || '';

        const yearEl = $('year-fortune');
        if (yearEl) yearEl.textContent = '';
        const monthEl = $('month-fortune');
        if (monthEl) monthEl.textContent = '';
        const dayEl = $('day-fortune');
        if (dayEl) dayEl.textContent = cleanAIResponse(record.ai_response || '');

        const dirsEl = $('lucky-directions');
        if (dirsEl) dirsEl.textContent = '—';
        const colorEl = $('lucky-color');
        if (colorEl) colorEl.textContent = '—';
        const numEl = $('lucky-number');
        if (numEl) numEl.textContent = '—';
        const healthEl = $('health-advice');
        if (healthEl) healthEl.textContent = '—';

        const qaBlock = $('question-answer-block');
        const qaText = $('qa-text');
        if (record.question && qaBlock && qaText) {
            qaBlock.style.display = 'block';
            qaText.textContent = `问：${cleanAIResponse(record.question)}\n答：${cleanAIResponse(record.ai_response || '')}`;
        } else if (qaBlock) {
            qaBlock.style.display = 'none';
        }
    }
}

// ========== Profile ==========
function initializeProfile() {
    const profile = state.userProfile;
    const info = $('profile-info');
    if (!info) return;

    if (!profile) {
        info.innerHTML = '<div class="profile-empty">未设置个人信息</div>';
        return;
    }

    info.innerHTML = `
        <div class="profile-name">${escapeHtml(profile.name)}</div>
        <div class="profile-row"><span class="profile-label">性别</span><span>${escapeHtml(profile.gender)}</span></div>
        <div class="profile-row"><span class="profile-label">出生</span><span>${profile.year}年${profile.month}月${profile.day}日 ${profile.time_str}</span></div>
        <div class="profile-row"><span class="profile-label">地点</span><span>${escapeHtml(profile.location || '未知')}</span></div>`;

    $('edit-profile-btn')?.addEventListener('click', () => {
        showSetupScreen();
        $('user-name').value = profile.name || '';
        $('user-birthday').value = `${profile.year}-${String(profile.month).padStart(2,'0')}-${String(profile.day).padStart(2,'0')}`;
        $('user-time').value = profile.time_str || '00:00';
        $('user-location').value = profile.location || '';
        document.querySelectorAll('.gender-btn').forEach(b => {
            b.classList.toggle('active', b.dataset.gender === profile.gender);
        });
    });
}

// ========== Setup DOMContentLoaded ==========
document.addEventListener('DOMContentLoaded', () => {
    // Gender buttons
    document.querySelectorAll('.gender-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.gender-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
        });
    });

    $('setup-btn')?.addEventListener('click', async () => {
        await saveUserProfile();
    });

    // Default date
    const today = new Date();
    today.setFullYear(today.getFullYear() - 20);
    const def = `${today.getFullYear()}-${String(today.getMonth()+1).padStart(2,'0')}-${String(today.getDate()).padStart(2,'0')}`;
    const bd = $('user-birthday');
    if (bd) bd.value = def;

    // Modal close on overlay click
    $('hotspot-modal')?.querySelector('.modal-overlay')?.addEventListener('click', closeHotspotModal);
});

// ========== Logout ==========
async function doLogout() {
    if (!confirm('确定要退出登录吗？\n退出后本地信息将被清除。')) return;

    // 清除前端 localStorage
    localStorage.removeItem('userProfile');
    localStorage.removeItem('cloud_token');
    localStorage.removeItem('cloud_user_id');
    state.userProfile = null;
    state.divineHistory = [];
    state.fortuneResult = null;

    // 通知后端清除服务端数据
    try {
        await _t('https://xuanxue-app-production.up.railway.app/api/profile/logout', { method: 'POST' });
    } catch(e) {}

    // 重置状态，回到设置页
    showSetupScreen();
    // 清空设置表单
    var nameEl = $('user-name');
    var bdEl = $('user-birthday');
    var timeEl = $('user-time');
    var locEl = $('user-location');
    if (nameEl) nameEl.value = '';
    if (bdEl) bdEl.value = '';
    if (timeEl) timeEl.value = '00:00';
    if (locEl) locEl.value = '';
    // 重置性别按钮
    document.querySelectorAll('.gender-btn').forEach(function(b) {
        b.classList.remove('active');
    });
}
let loginMode = 'login'; // 'login' | 'register'

function showCloudLogin() {
    loginMode = 'login';
    $('cloud-login-modal').style.display = 'flex';
    $('login-email').value = '';
    $('login-password').value = '';
    const errorEl = $('login-error');
    if (errorEl) { errorEl.style.display = 'none'; errorEl.textContent = ''; }
    const btn = $('login-submit-btn');
    if (btn) btn.textContent = '登录';
}

function closeCloudLogin() {
    $('cloud-login-modal').style.display = 'none';
}

function toggleLoginMode(e) {
    e.preventDefault();
    loginMode = loginMode === 'login' ? 'register' : 'login';
    const btn = $('login-submit-btn');
    const toggle = document.querySelector('.login-register-toggle');
    if (btn) btn.textContent = loginMode === 'login' ? '登录' : '注册';
    if (toggle) {
        if (loginMode === 'login') {
            toggle.innerHTML = '没有账号？<a href="#" onclick="toggleLoginMode(event)">立即注册</a>';
        } else {
            toggle.innerHTML = '已有账号？<a href="#" onclick="toggleLoginMode(event)">立即登录</a>';
        }
    }
}

async function doCloudLogin() {
    const email = $('login-email').value.trim();
    const password = $('login-password').value;
    const errorEl = $('login-error');
    const btn = $('login-submit-btn');

    if (!email || !password) {
        if (errorEl) { errorEl.style.display = 'block'; errorEl.textContent = '请填写邮箱和密码'; }
        return;
    }
    if (password.length < 6) {
        if (errorEl) { errorEl.style.display = 'block'; errorEl.textContent = '密码至少6位'; }
        return;
    }

    if (btn) { btn.disabled = true; btn.textContent = '处理中...'; }
    if (errorEl) { errorEl.style.display = 'none'; }

    try {
        const endpoint = loginMode === 'login' ? '/api/auth/signin' : '/api/auth/signup';
        const res = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password }),
        });
        const data = await res.json();

        if (data.success) {
            // 保存 token
            if (data.access_token) {
                localStorage.setItem('cloud_token', data.access_token);
                localStorage.setItem('cloud_user_id', data.user_id || '');
            }
            closeCloudLogin();
            if (loginMode === 'register') {
                alert('注册成功！请查收验证邮件（可能需要几分钟）。');
            } else {
                alert('登录成功！您的数据已同步云端。');
            }
            location.reload();
        } else {
            if (errorEl) { errorEl.style.display = 'block'; errorEl.textContent = data.error || '操作失败，请重试'; }
            if (btn) { btn.disabled = false; btn.textContent = loginMode === 'login' ? '登录' : '注册'; }
        }
    } catch (e) {
        if (errorEl) { errorEl.style.display = 'block'; errorEl.textContent = '网络错误，请检查网络连接'; }
        if (btn) { btn.disabled = false; btn.textContent = loginMode === 'login' ? '登录' : '注册'; }
    }
}
