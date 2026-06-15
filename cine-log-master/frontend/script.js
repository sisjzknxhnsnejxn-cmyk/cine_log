/* ============================
   CineLog v2.0 - 光影手账 脚本
   ============================ */

// ========== 全局状态 ==========
let records = [];
let currentFilter = 'all';
let currentMonth = new Date();
let editingId = null;
let deletingId = null;
let coverClickCount = 0;
let coverClickTimer = null;

// ========== API 配置 ==========
const API_BASE = 'http://localhost:5000';
const TOKEN_KEY = 'cinelog_token';
const USER_KEY = 'cinelog_user';

function getToken() { return localStorage.getItem(TOKEN_KEY); }
function getUser() { try { return JSON.parse(localStorage.getItem(USER_KEY)); } catch { return null; } }

// ========== 初始化 ==========
function initApp() {
    // 兼容：login页存储的是cinelog_user，也接受token
    if (!getToken() && !getUser()) { window.location.href = 'login.html'; return; }
    initTheme();
    initStarlight();
    initFloatingDecorations();
    loadRecords();
    updateGreeting();
    updateCoverDate();
    setupCoverEasterEgg();
    setInterval(updateGreeting, 60000);
}

// ========== 主题系统 ==========
function initTheme() {
    const theme = localStorage.getItem('cinelog_theme') || 'light';
    document.documentElement.setAttribute('data-theme', theme);
    updateThemeButton(theme);
}

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    
    // 翻页动画
    document.body.classList.add('theme-transitioning');
    setTimeout(() => document.body.classList.remove('theme-transitioning'), 600);
    
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('cinelog_theme', next);
    updateThemeButton(next);
    initStarlight();
}

function updateThemeButton(theme) {
    const icon = document.getElementById('themeIcon');
    const label = document.getElementById('themeLabel');
    if (icon) icon.textContent = theme === 'dark' ? '☀️' : '🌙';
    if (label) label.textContent = theme === 'dark' ? '日间模式' : '夜间模式';
}

// ========== 星光粒子 ==========
function initStarlight() {
    const container = document.getElementById('starlightParticles');
    if (!container) return;
    container.innerHTML = '';
    const theme = document.documentElement.getAttribute('data-theme');
    if (theme !== 'dark') return;
    
    for (let i = 0; i < 30; i++) {
        const star = document.createElement('div');
        star.className = 'star-particle';
        star.style.left = Math.random() * 100 + '%';
        star.style.top = Math.random() * 100 + '%';
        star.style.animationDelay = Math.random() * 3 + 's';
        star.style.animationDuration = (2 + Math.random() * 3) + 's';
        container.appendChild(star);
    }
}

// ========== 漂浮装饰 ==========
function initFloatingDecorations() {
    const container = document.getElementById('floatingDecorations');
    if (!container) return;
    const items = ['✦', '◇', '○', '△', '☆', '♡'];
    for (let i = 0; i < 6; i++) {
        const el = document.createElement('div');
        el.className = 'float-item';
        el.textContent = items[i % items.length];
        el.style.left = (10 + Math.random() * 80) + '%';
        el.style.top = (10 + Math.random() * 80) + '%';
        el.style.animationDelay = (Math.random() * 10) + 's';
        el.style.fontSize = (1 + Math.random() * 1.5) + 'rem';
        container.appendChild(el);
    }
}

// ========== 封面彩蛋 ==========
function setupCoverEasterEgg() {
    const cover = document.getElementById('journalCover');
    if (!cover) return;
    cover.addEventListener('click', () => {
        coverClickCount++;
        clearTimeout(coverClickTimer);
        coverClickTimer = setTimeout(() => { coverClickCount = 0; }, 2000);
        if (coverClickCount >= 5) {
            coverClickCount = 0;
            showToast('今天也要好好生活呀 ✨', 'info');
            triggerConfetti();
        }
    });
}

function triggerConfetti() {
    const container = document.getElementById('confettiContainer');
    if (!container) return;
    const colors = ['#A67C52', '#A8B2A1', '#D4A574', '#C9A0A0', '#B8A9C9', '#E8E1D5'];
    for (let i = 0; i < 50; i++) {
        const piece = document.createElement('div');
        piece.className = 'confetti-piece';
        piece.style.left = Math.random() * 100 + '%';
        piece.style.background = colors[Math.floor(Math.random() * colors.length)];
        piece.style.animationDelay = Math.random() * 0.5 + 's';
        piece.style.width = (6 + Math.random() * 8) + 'px';
        piece.style.height = (6 + Math.random() * 8) + 'px';
        piece.style.borderRadius = Math.random() > 0.5 ? '50%' : '2px';
        container.appendChild(piece);
    }
    setTimeout(() => { container.innerHTML = ''; }, 4000);
}

// ========== 数据加载 ==========
function mapBackendRecord(r) {
    // 后端字段 → 前端字段映射
    const typeMap = { 'movie': '电影', 'tv': '剧集', 'podcast': '播客' };
    return {
        id: r.id,
        title: r.title,
        type: typeMap[r.media_type] || r.media_type || r.type || '电影',
        date: r.watch_date || r.date,
        rating: r.rating ? Math.round(r.rating / 2) : (r.rating || 0), // 后端1-10 → 前端1-5
        mood: r.mood || '',
        comment: r.review || r.comment || '',
        tags: r.tags || []
    };
}

function mapFrontendToBackend(record) {
    // 前端字段 → 后端字段映射
    const typeMap = { '电影': 'movie', '剧集': 'tv', '播客': 'podcast', '纪录片': 'movie' };
    return {
        title: record.title,
        media_type: typeMap[record.type] || 'movie',
        watch_date: record.date,
        rating: record.rating ? record.rating * 2 : null, // 前端1-5 → 后端1-10
        review: record.comment || ''
    };
}

async function loadRecords() {
    try {
        const res = await fetch(`${API_BASE}/records`, {
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
        if (res.status === 401) { 
            localStorage.removeItem(TOKEN_KEY);
            window.location.href = 'login.html'; 
            return; 
        }
        if (res.ok) {
            const data = await res.json();
            records = Array.isArray(data) ? data.map(mapBackendRecord) : [];
        } else {
            records = [];
        }
    } catch {
        // 离线使用 mock 数据
        records = typeof mockRecords !== 'undefined' ? mockRecords : [];
    }
    renderAll();
}

function renderAll() {
    renderHomeStats();
    renderMovieTicket();
    renderMonthMemory();
    renderTodayRecommend();
    renderRecords();
    renderCalendar();
    renderAnalytics();
    renderFavorites();
    renderProfile();
}

// ========== 首页 ==========
function updateGreeting() {
    const h = new Date().getHours();
    let greeting = '晚上好';
    if (h < 6) greeting = '夜深了';
    else if (h < 12) greeting = '早上好';
    else if (h < 14) greeting = '中午好';
    else if (h < 18) greeting = '下午好';
    
    const user = getUser();
    const name = user?.username || '光影旅人';
    const el = document.getElementById('greetingTime');
    if (el) el.textContent = `${greeting}，${name}`;
    
    const dateEl = document.getElementById('greetingDate');
    if (dateEl) {
        const now = new Date();
        const weekdays = ['周日','周一','周二','周三','周四','周五','周六'];
        dateEl.textContent = `${now.getFullYear()}年${now.getMonth()+1}月${now.getDate()}日 ${weekdays[now.getDay()]}`;
    }
    
    const avatarEls = ['homeAvatar', 'profileAvatar'];
    avatarEls.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.textContent = name.charAt(0).toUpperCase();
    });
    
    const nameEls = { 'homeUsername': name, 'profileName': name };
    Object.entries(nameEls).forEach(([id, val]) => {
        const el = document.getElementById(id);
        if (el) el.textContent = val;
    });
}

function updateCoverDate() {
    const el = document.getElementById('coverDate');
    if (!el) return;
    const now = new Date();
    el.textContent = `${now.getFullYear()}.${String(now.getMonth()+1).padStart(2,'0')}.${String(now.getDate()).padStart(2,'0')}`;
}

function renderHomeStats() {
    const total = records.length;
    const now = new Date();
    const monthRecords = records.filter(r => {
        const d = new Date(r.date);
        return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear();
    });
    
    const streak = calculateStreak();
    const moods = monthRecords.map(r => r.mood).filter(Boolean);
    const topMood = moods.length ? getMostFrequent(moods) : '😊';
    
    setText('statTotalHome', total);
    setText('statMonthHome', monthRecords.length);
    setText('statStreakHome', streak);
    setText('statMoodHome', topMood);
}

function calculateStreak() {
    if (!records.length) return 0;
    const dates = [...new Set(records.map(r => r.date))].sort().reverse();
    let streak = 0;
    const today = new Date();
    today.setHours(0,0,0,0);
    
    for (let i = 0; i < dates.length; i++) {
        const d = new Date(dates[i]);
        d.setHours(0,0,0,0);
        const expected = new Date(today);
        expected.setDate(expected.getDate() - i);
        if (d.getTime() === expected.getTime()) {
            streak++;
        } else {
            break;
        }
    }
    return streak;
}

function renderMovieTicket() {
    const ticket = document.getElementById('movieTicket');
    if (!ticket || !records.length) return;
    
    const latest = [...records].sort((a, b) => new Date(b.date) - new Date(a.date))[0];
    const stars = '★'.repeat(latest.rating || 0) + '☆'.repeat(5 - (latest.rating || 0));
    const ticketNo = 'NO.' + String(latest.id || Math.floor(Math.random() * 999999)).padStart(6, '0');
    
    ticket.innerHTML = `
        <div class="ticket-left">
            <div class="ticket-title">${escHtml(latest.title)}</div>
            <div class="ticket-meta">
                <span class="ticket-date">${latest.date}</span>
                <span class="ticket-type">${latest.type || '电影'}</span>
            </div>
            <div class="ticket-rating">${stars}</div>
        </div>
        <div class="ticket-divider"></div>
        <div class="ticket-right">
            <div class="ticket-barcode"></div>
            <div class="ticket-number">${ticketNo}</div>
        </div>
    `;
}

function renderMonthMemory() {
    const el = document.getElementById('monthMemory');
    if (!el) return;
    
    const now = new Date();
    const monthRecords = records.filter(r => {
        const d = new Date(r.date);
        return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear();
    });
    
    if (!monthRecords.length) {
        el.innerHTML = '<p class="memory-text">这个月还没有记录，开始你的光影之旅吧...</p>';
        return;
    }
    
    const types = monthRecords.map(r => r.type || '电影');
    const topType = getMostFrequent(types);
    const typePercent = Math.round(types.filter(t => t === topType).length / types.length * 100);
    const moods = monthRecords.map(r => r.mood).filter(Boolean);
    const topMood = moods.length ? getMostFrequent(moods) : '😊';
    
    el.innerHTML = `<p class="memory-text">本月记录了<strong>${monthRecords.length}</strong>部作品，其中${topType}占${typePercent}%，最常出现的心情是${topMood}。</p>`;
}

function renderTodayRecommend() {
    const container = document.getElementById('todayRecommend');
    if (!container || !records.length) return;
    
    const highRated = records.filter(r => r.rating >= 4);
    const pool = highRated.length ? highRated : records;
    const item = pool[Math.floor(Math.random() * pool.length)];
    const typeEmoji = {'电影':'🎬','剧集':'📺','播客':'🎙️','纪录片':'📹'}[item.type] || '🎬';
    
    container.innerHTML = `
        <div class="polaroid-photo"><span class="photo-emoji">${typeEmoji}</span></div>
        <div class="polaroid-info">
            <div class="polaroid-title">${escHtml(item.title)}</div>
            <div class="polaroid-desc">${item.comment ? escHtml(item.comment.slice(0, 50)) : '回味这部作品的光影时刻'}</div>
        </div>
    `;
}

// ========== 记录页 ==========
function renderRecords() {
    const container = document.getElementById('recordsTimeline');
    if (!container) return;
    
    let filtered = currentFilter === 'all' ? records : records.filter(r => r.type === currentFilter);
    filtered = [...filtered].sort((a, b) => new Date(b.date) - new Date(a.date));
    
    if (!filtered.length) {
        container.innerHTML = `<div class="timeline-empty"><span class="empty-icon">📝</span><p>还没有记录</p><p style="font-size:0.8rem;margin-top:8px;">点击"写新的"开始你的手账之旅</p></div>`;
        return;
    }
    
    container.innerHTML = filtered.map((r, i) => {
        const stars = '★'.repeat(r.rating || 0) + '☆'.repeat(5 - (r.rating || 0));
        const tags = (r.tags || []).map(t => `<span class="tag">${escHtml(t)}</span>`).join('');
        const typeEmoji = {'电影':'🎬','剧集':'📺','播客':'🎙️','纪录片':'📹'}[r.type] || '🎬';
        
        return `<div class="timeline-item" style="animation-delay:${i*0.08}s">
            <div class="timeline-date">${r.date}</div>
            <div class="timeline-card">
                <div class="card-top">
                    <div class="card-title">${escHtml(r.title)}</div>
                    <div class="card-rating">${stars}</div>
                </div>
                <div class="card-meta-row">
                    <span class="meta-badge">${typeEmoji} ${r.type||'电影'}</span>
                    ${r.mood ? `<span class="meta-badge">${r.mood}</span>` : ''}
                </div>
                ${r.comment ? `<div class="card-comment">${escHtml(r.comment)}</div>` : ''}
                ${tags ? `<div class="card-tags">${tags}</div>` : ''}
                <div class="card-actions">
                    <button class="btn-icon" onclick="openEditModal(${r.id})">✏️ 编辑</button>
                    <button class="btn-icon btn-icon-danger" onclick="openDeleteModal(${r.id})">🗑️</button>
                </div>
            </div>
        </div>`;
    }).join('');
}

function setFilter(filter) {
    currentFilter = filter;
    document.querySelectorAll('.pill').forEach(p => p.classList.toggle('active', p.dataset.filter === filter));
    renderRecords();
}

// ========== 月历页 ==========
function renderCalendar() {
    const grid = document.getElementById('calendarGrid');
    const label = document.getElementById('calMonthLabel');
    if (!grid || !label) return;
    
    const year = currentMonth.getFullYear();
    const month = currentMonth.getMonth();
    label.textContent = `${year}年${month + 1}月`;
    
    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const today = new Date();
    
    const monthDates = records.reduce((acc, r) => {
        const d = new Date(r.date);
        if (d.getFullYear() === year && d.getMonth() === month) {
            const day = d.getDate();
            if (!acc[day]) acc[day] = [];
            acc[day].push(r);
        }
        return acc;
    }, {});
    
    let html = '';
    for (let i = 0; i < firstDay; i++) html += '<div class="cal-day empty"></div>';
    
    for (let d = 1; d <= daysInMonth; d++) {
        const isToday = d === today.getDate() && month === today.getMonth() && year === today.getFullYear();
        const hasRecord = monthDates[d];
        const cls = `cal-day ${isToday ? 'today' : ''} ${hasRecord ? 'has-record' : ''}`;
        html += `<div class="${cls}" onclick="showDayDetail(${year},${month},${d})">${d}</div>`;
    }
    
    grid.innerHTML = html;
}

function prevMonth() { currentMonth.setMonth(currentMonth.getMonth() - 1); renderCalendar(); }
function nextMonth() { currentMonth.setMonth(currentMonth.getMonth() + 1); renderCalendar(); }

function showDayDetail(year, month, day) {
    const panel = document.getElementById('dayDetailPanel');
    const dateEl = document.getElementById('dayDetailDate');
    const recordsEl = document.getElementById('dayDetailRecords');
    if (!panel) return;
    
    const dateStr = `${year}-${String(month+1).padStart(2,'0')}-${String(day).padStart(2,'0')}`;
    const dayRecords = records.filter(r => r.date === dateStr);
    
    dateEl.textContent = `${year}年${month+1}月${day}日`;
    
    if (!dayRecords.length) {
        recordsEl.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:16px;">这天没有记录</p>';
    } else {
        recordsEl.innerHTML = dayRecords.map(r => `
            <div class="day-record-item">
                <span class="item-title">${escHtml(r.title)}</span>
                <span class="item-rating">${'★'.repeat(r.rating||0)}</span>
            </div>
        `).join('');
    }
    
    panel.classList.add('active');
}

function closeDayDetail() {
    document.getElementById('dayDetailPanel')?.classList.remove('active');
}

// ========== 数据分析页 ==========
function renderAnalytics() {
    renderAnnualReport();
    renderWishingJars();
    renderGrowthTree();
    renderBookshelf();
    renderFilmScroll();
    renderMoodChart();
}

function renderAnnualReport() {
    const total = records.length;
    const types = records.map(r => r.type || '电影');
    const favType = types.length ? getMostFrequent(types) : '--';
    const avgRating = records.length ? (records.reduce((s,r) => s + (r.rating||0), 0) / records.length).toFixed(1) : '--';
    
    // 高光月份
    const monthCounts = {};
    records.forEach(r => {
        const m = new Date(r.date).getMonth() + 1;
        monthCounts[m] = (monthCounts[m] || 0) + 1;
    });
    const highMonth = Object.keys(monthCounts).length ? Object.entries(monthCounts).sort((a,b) => b[1]-a[1])[0][0] + '月' : '--';
    
    setText('reportTotal', total);
    setText('reportFavType', favType);
    setText('reportAvgRating', avgRating);
    setText('reportHighMonth', highMonth);
}

function renderWishingJars() {
    const container = document.getElementById('wishingJars');
    if (!container) return;
    
    const ratingCounts = {1:0, 2:0, 3:0, 4:0, 5:0};
    records.forEach(r => { if (r.rating) ratingCounts[r.rating]++; });
    
    container.innerHTML = [1,2,3,4,5].map(rating => {
        const count = ratingCounts[rating];
        const stars = Array(Math.min(count, 15)).fill('<div class="jar-star"></div>').join('');
        return `
            <div class="wishing-jar">
                <div class="jar-tooltip">你给${rating}星作品${count}部</div>
                <div class="jar-glass">
                    <div class="jar-lid"></div>
                    <div class="jar-stars">${stars}</div>
                </div>
                <div class="jar-rating-label">${'★'.repeat(rating)}</div>
                <div class="jar-count-label">${count}</div>
            </div>
        `;
    }).join('');
}

function renderGrowthTree() {
    const container = document.getElementById('growthTreeCanvas');
    const descEl = document.getElementById('treeDesc');
    if (!container) return;
    
    const total = records.length;
    let stage, stageEmoji, stageText;
    
    if (total === 0) {
        stage = 'seed'; stageEmoji = '🌱'; stageText = '播下第一颗种子吧';
    } else if (total <= 10) {
        stage = 'sprout'; stageEmoji = '🌱'; stageText = `小树苗已发芽（${total}片叶子）`;
    } else if (total <= 30) {
        stage = 'young'; stageEmoji = '🌿'; stageText = `小树正在成长（${total}片叶子）`;
    } else if (total <= 60) {
        stage = 'mature'; stageEmoji = '🌳'; stageText = `成长树枝繁叶茂（${total}片叶子）`;
    } else {
        stage = 'grand'; stageEmoji = '🌳'; stageText = `参天大树（${total}片叶子）`;
    }
    
    // 树干高度
    const trunkHeight = Math.min(60 + total * 2, 120);
    const trunkWidth = Math.min(8 + Math.floor(total / 10) * 2, 20);
    
    // 生成叶子
    const leaves = records.slice(0, 50).map((r, i) => {
        let cls = 'green';
        if (r.rating === 5) cls = 'gold';
        else if (r.rating === 4) cls = 'green';
        else if (r.rating === 3) cls = 'orange';
        else if (r.rating === 2) cls = 'gray-green';
        else if (r.rating === 1) cls = 'withered';
        
        return `<div class="tree-leaf-item ${cls}" style="animation-delay:${i*0.05}s" title="${escHtml(r.title)}">
            <div class="tree-leaf-tooltip">🍃 ${escHtml(r.title)}<br>${r.date} · ${'★'.repeat(r.rating||0)}</div>
        </div>`;
    }).join('');
    
    container.innerHTML = `
        <div class="tree-svg-container">
            <div class="tree-canopy">${leaves}</div>
            <svg class="tree-trunk-svg" width="${trunkWidth + 20}" height="${trunkHeight}" viewBox="0 0 ${trunkWidth + 20} ${trunkHeight}">
                <path d="M${(trunkWidth+20)/2} 0 Q${(trunkWidth+20)/2 - 3} ${trunkHeight*0.3} ${(trunkWidth+20)/2 - 2} ${trunkHeight*0.6} Q${(trunkWidth+20)/2 + 2} ${trunkHeight*0.8} ${(trunkWidth+20)/2} ${trunkHeight}" 
                      stroke="#8B6914" stroke-width="${trunkWidth}" fill="none" stroke-linecap="round"/>
                ${total > 15 ? `<path d="M${(trunkWidth+20)/2} ${trunkHeight*0.4} Q${(trunkWidth+20)/2 + 15} ${trunkHeight*0.3} ${(trunkWidth+20)/2 + 20} ${trunkHeight*0.25}" stroke="#8B6914" stroke-width="${Math.max(trunkWidth-4,3)}" fill="none" stroke-linecap="round"/>` : ''}
                ${total > 30 ? `<path d="M${(trunkWidth+20)/2} ${trunkHeight*0.5} Q${(trunkWidth+20)/2 - 12} ${trunkHeight*0.4} ${(trunkWidth+20)/2 - 18} ${trunkHeight*0.35}" stroke="#8B6914" stroke-width="${Math.max(trunkWidth-5,2)}" fill="none" stroke-linecap="round"/>` : ''}
            </svg>
        </div>
        <div class="tree-stage-label">${stageEmoji} ${stageText}</div>
    `;
    
    if (descEl) descEl.textContent = '每一条记录都是一片新叶，点击叶子查看详情';
}

function renderBookshelf() {
    const container = document.getElementById('realBookshelf');
    if (!container) return;
    
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    const colors = ['#A67C52','#7A9A6D','#9B7B9B','#6A8FAD','#C4956A','#8B7355','#6B8E7B','#AD7A7A','#7B8EAD','#A69B6B','#8E6B7B','#6BAD8E'];
    const year = new Date().getFullYear();
    
    const monthCounts = {};
    records.forEach(r => {
        const d = new Date(r.date);
        if (d.getFullYear() === year) {
            const m = d.getMonth();
            monthCounts[m] = (monthCounts[m] || 0) + 1;
        }
    });
    
    container.innerHTML = months.map((m, i) => {
        const count = monthCounts[i] || 0;
        const height = Math.max(20, Math.min(count * 15, 110));
        const color = colors[i];
        return `
            <div class="book-item">
                <div class="book-tooltip">${m}: ${count}条记录</div>
                <div class="book-spine-3d" style="height:${height}px;background:${color};">
                    <span class="book-spine-text">${m}</span>
                </div>
                <div class="book-month-label">${i+1}月</div>
            </div>
        `;
    }).join('');
}

function renderFilmScroll() {
    const container = document.getElementById('filmScroll');
    const countEl = document.getElementById('filmCount');
    if (!container) return;
    
    const films = records.filter(r => (r.type || '电影') === '电影');
    if (countEl) countEl.textContent = `${films.length} 部电影`;
    
    if (!films.length) {
        container.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:20px;width:100%;">还没有电影记录</p>';
        return;
    }
    
    container.innerHTML = films.slice(0, 20).map(r => {
        const stars = '★'.repeat(r.rating || 0);
        return `
            <div class="film-frame-card">
                <div class="film-poster">🎬</div>
                <div class="film-frame-title">${escHtml(r.title.slice(0,6))}</div>
                <div class="film-frame-rating">${stars}</div>
            </div>
        `;
    }).join('');
}

function renderMoodChart() {
    const container = document.getElementById('moodChart');
    if (!container) return;
    
    const moodValues = {'😊':4, '😍':5, '🥰':5, '😢':2, '🤔':3, '😴':2, '😤':1};
    const months = ['1月','2月','3月','4月','5月','6月','7月','8月','9月','10月','11月','12月'];
    const year = new Date().getFullYear();
    
    const monthMoods = {};
    records.forEach(r => {
        const d = new Date(r.date);
        if (d.getFullYear() === year && r.mood) {
            const m = d.getMonth();
            if (!monthMoods[m]) monthMoods[m] = [];
            monthMoods[m].push(r.mood);
        }
    });
    
    const bars = months.map((label, i) => {
        const moods = monthMoods[i] || [];
        if (!moods.length) return `<div class="mood-point"><div class="mood-bar" style="height:5px;background:var(--khaki);"></div><div class="mood-month-label">${i+1}</div></div>`;
        
        const avg = moods.reduce((s, m) => s + (moodValues[m] || 3), 0) / moods.length;
        const height = Math.max(10, avg * 18);
        const topMood = getMostFrequent(moods);
        const hue = avg > 3.5 ? '120' : avg > 2.5 ? '45' : '0';
        
        return `<div class="mood-point">
            <div class="mood-bar" style="height:${height}px;background:hsl(${hue},40%,65%);" data-emoji="${topMood}"></div>
            <div class="mood-month-label">${i+1}</div>
        </div>`;
    }).join('');
    
    container.innerHTML = `<div class="mood-line">${bars}</div>`;
}

// ========== 收藏页 ==========
function renderFavorites() {
    const wall = document.getElementById('collageWall');
    const empty = document.getElementById('emptyFavorites');
    if (!wall) return;
    
    const favorites = records.filter(r => r.rating === 5);
    
    if (!favorites.length) {
        wall.style.display = 'none';
        if (empty) empty.style.display = 'block';
        return;
    }
    
    wall.style.display = '';
    if (empty) empty.style.display = 'none';
    
    const rotations = [-2, 1.5, -1, 2, -0.5, 1];
    
    wall.innerHTML = favorites.map((r, i) => {
        const rotation = rotations[i % rotations.length];
        const typeEmoji = {'电影':'🎬','剧集':'📺','播客':'🎙️','纪录片':'📹'}[r.type] || '🎬';
        const tags = (r.tags || []).slice(0,3).map(t => `<span class="collage-tag">${escHtml(t)}</span>`).join('');
        
        return `<div class="collage-item" style="transform:rotate(${rotation}deg);animation-delay:${i*0.1}s">
            <div class="collage-photo">${typeEmoji}</div>
            <div class="collage-title">${escHtml(r.title)}</div>
            <div class="collage-rating">${'★'.repeat(5)} 珍藏</div>
            ${r.comment ? `<div class="collage-comment">${escHtml(r.comment)}</div>` : ''}
            ${tags ? `<div class="collage-tags">${tags}</div>` : ''}
            <div class="collage-stamp">${r.mood || '♡'}</div>
        </div>`;
    }).join('');
}

// ========== 个人页 ==========
function renderProfile() {
    const user = getUser();
    setText('profileTotal', records.length);
    setText('profileJoinDate', user?.created_at ? user.created_at.split('T')[0] : '--');
    
    const types = records.map(r => r.type || '电影');
    setText('profileFavType', types.length ? getMostFrequent(types) : '--');
    
    const avg = records.length ? (records.reduce((s,r) => s + (r.rating||0), 0) / records.length).toFixed(1) : '--';
    setText('profileAvgRating', avg + (avg !== '--' ? '★' : ''));
    
    renderKeywords();
    renderBadges();
}

function renderKeywords() {
    const container = document.getElementById('keywordCloud');
    if (!container) return;
    
    const keywords = {};
    records.forEach(r => {
        (r.tags || []).forEach(tag => {
            keywords[tag] = (keywords[tag] || 0) + 1;
        });
    });
    
    const sorted = Object.entries(keywords).sort((a,b) => b[1] - a[1]).slice(0, 12);
    
    if (!sorted.length) {
        container.innerHTML = '<span style="color:var(--text-muted);font-size:0.8rem;">记录更多，关键词自动生成</span>';
        return;
    }
    
    container.innerHTML = sorted.map(([word, count]) => 
        `<span class="keyword-item" onclick="openKeywordPage('${escHtml(word)}')" title="出现${count}次">${escHtml(word)}</span>`
    ).join('');
}

function renderBadges() {
    const container = document.getElementById('badgesGrid');
    if (!container) return;
    
    const streak = calculateStreak();
    const total = records.length;
    
    const badges = [
        { icon: '🌱', name: '初心者', unlocked: total >= 1 },
        { icon: '📚', name: '十部达成', unlocked: total >= 10 },
        { icon: '🌟', name: '五十部', unlocked: total >= 50 },
        { icon: '🔥', name: '连续7天', unlocked: streak >= 7 },
        { icon: '💪', name: '连续15天', unlocked: streak >= 15 },
        { icon: '👑', name: '连续30天', unlocked: streak >= 30 },
        { icon: '⭐', name: '严格评审', unlocked: records.some(r => r.rating === 1) },
        { icon: '💝', name: '完美作品', unlocked: records.filter(r => r.rating === 5).length >= 5 },
        { icon: '🎬', name: '影院常客', unlocked: records.filter(r => r.type === '电影').length >= 20 },
    ];
    
    container.innerHTML = badges.map(b => `
        <div class="badge-item ${b.unlocked ? 'unlocked' : 'locked'}">
            <span class="badge-icon">${b.icon}</span>
            <span class="badge-name">${b.name}</span>
        </div>
    `).join('');
}

// ========== 关键词故事页 ==========
function openKeywordPage(keyword) {
    const content = document.getElementById('keywordStoryContent');
    if (!content) return;
    
    // 找到相关记录
    const related = records.filter(r => (r.tags || []).includes(keyword));
    const count = related.length;
    
    // 时间轴
    const sorted = [...related].sort((a,b) => new Date(a.date) - new Date(b.date));
    const first = sorted[0];
    const last = sorted[sorted.length - 1];
    
    // 生成故事文本
    let storyText = '';
    if (count >= 3) {
        const titles = sorted.slice(0, 3).map(r => `《${r.title}》`).join('、');
        storyText = `这一年里，你最常提到"${keyword}"。从${titles}的故事中，"${keyword}"成为了你的年度主题词。`;
    } else if (count >= 1) {
        storyText = `"${keyword}"是你的观影关键词之一，共出现${count}次。每一次遇见，都是一段新的光影故事。`;
    }
    
    // 贴纸映射
    const stickerMap = {
        '成长': ['🌱','🌿','📖','⭐'],
        '治愈': ['☘️','🍃','☀️','🌸'],
        '科幻': ['🚀','🌌','⭐','🔭'],
        '悬疑': ['🔍','🗝️','🌙','💡'],
        '爱情': ['💕','🌹','💌','✨'],
        '喜剧': ['😄','🎉','🌈','🎪'],
        '恐怖': ['🌙','👻','🕯️','🦇'],
        '动画': ['🎨','✨','🌈','🦋'],
    };
    const stickers = stickerMap[keyword] || ['✨','📖','🎬','⭐'];
    
    // 记录列表
    const recordsList = related.map(r => `
        <div class="keyword-record-item">
            <span class="keyword-record-title">《${escHtml(r.title)}》</span>
            <span class="keyword-record-rating">${'★'.repeat(r.rating||0)}</span>
        </div>
    `).join('');
    
    // 时间轴
    const timelineHtml = sorted.map(r => `
        <div class="keyword-timeline-item">
            <div class="keyword-timeline-date">${r.date}</div>
            <div class="keyword-timeline-title">《${escHtml(r.title)}》</div>
        </div>
    `).join('');
    
    // 贴纸墙
    const stickerHtml = stickers.map((s, i) => `
        <div class="keyword-sticker" style="animation-delay:${i*0.1}s">
            <span style="font-size:1.5rem">${s}</span>
        </div>
    `).join('');
    
    content.innerHTML = `
        <div class="keyword-hero">
            <div class="keyword-hero-title">${escHtml(keyword)}</div>
            <div class="keyword-hero-count">出现 ${count} 次</div>
        </div>
        
        <div class="keyword-section">
            <div class="keyword-section-title">📚 相关记录</div>
            ${recordsList}
        </div>
        
        ${storyText ? `<div class="keyword-section">
            <div class="keyword-section-title">📝 我的关键词故事</div>
            <div class="keyword-story-text">${storyText}</div>
        </div>` : ''}
        
        <div class="keyword-section">
            <div class="keyword-section-title">📅 关键词时间轴</div>
            <div class="keyword-timeline">${timelineHtml}</div>
        </div>
        
        <div class="keyword-section">
            <div class="keyword-section-title">🎨 关键词贴纸墙</div>
            <div class="keyword-sticker-wall">${stickerHtml}</div>
        </div>
    `;
    
    // 导航到关键词页
    showPage('Keyword');
}

function goBackFromKeyword() {
    showPage('Profile');
}

// ========== 导航系统 ==========
function navigateTo(page) {
    document.querySelectorAll('.tab-item').forEach(t => t.classList.toggle('active', t.dataset.page === page));
    showPage(page);
}

function showPage(pageName) {
    document.querySelectorAll('.page').forEach(p => {
        p.classList.remove('active');
        p.style.display = 'none';
    });
    const target = document.getElementById('page' + pageName);
    if (target) {
        target.style.display = 'block';
        // 重新触发动画
        target.style.animation = 'none';
        target.offsetHeight; // reflow
        target.style.animation = '';
        target.classList.add('active');
    }
    
    // 隐藏tab bar在关键词页
    const tabBar = document.getElementById('tabBar');
    if (tabBar) tabBar.style.display = pageName === 'Keyword' ? 'none' : '';
}

// ========== 添加记录 ==========
function openAddModal() {
    document.getElementById('addModal')?.classList.add('active');
    document.getElementById('recordDate').value = new Date().toISOString().split('T')[0];
}

function closeAddModal() {
    document.getElementById('addModal')?.classList.remove('active');
    resetAddForm();
}

function resetAddForm() {
    document.getElementById('recordTitle').value = '';
    document.getElementById('recordComment').value = '';
    document.getElementById('recordTags').value = '';
    document.querySelectorAll('#addModal .mood-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('input[name="rating"]').forEach(r => r.checked = false);
}

async function addRecord() {
    const title = document.getElementById('recordTitle').value.trim();
    const type = document.getElementById('recordType').value;
    const date = document.getElementById('recordDate').value;
    const ratingEl = document.querySelector('input[name="rating"]:checked');
    const rating = ratingEl ? parseInt(ratingEl.value) : 0;
    const mood = document.querySelector('#addModal .mood-btn.active')?.dataset.mood || '';
    const comment = document.getElementById('recordComment').value.trim();
    const tagsStr = document.getElementById('recordTags').value.trim();
    const tags = tagsStr ? tagsStr.split(/\s+/) : [];
    
    if (!title || !date) { showToast('请填写名称和日期', 'error'); return; }
    
    const frontendRecord = { title, type, date, rating, mood, comment, tags };
    const backendPayload = mapFrontendToBackend(frontendRecord);
    
    // 先关闭弹窗，再异步保存
    closeAddModal();
    
    try {
        const res = await fetch(`${API_BASE}/records`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${getToken()}` },
            body: JSON.stringify(backendPayload)
        });
        if (res.ok) {
            const data = await res.json();
            // 后端返回 { id, message }，构造完整前端记录
            frontendRecord.id = data.id;
            records.push(frontendRecord);
        } else {
            frontendRecord.id = Date.now();
            records.push(frontendRecord);
        }
    } catch {
        frontendRecord.id = Date.now();
        records.push(frontendRecord);
    }
    
    renderAll();
    showToast('📌 已贴上新记录', 'success');
    checkStreakAchievement();
}

// ========== 编辑记录 ==========
function openEditModal(id) {
    editingId = id;
    const record = records.find(r => r.id === id);
    if (!record) return;
    
    document.getElementById('editTitle').value = record.title;
    document.getElementById('editType').value = record.type || '电影';
    document.getElementById('editDate').value = record.date;
    document.getElementById('editComment').value = record.comment || '';
    
    if (record.rating) {
        const radio = document.getElementById('editStar' + record.rating);
        if (radio) radio.checked = true;
    }
    
    document.getElementById('editModal')?.classList.add('active');
}

function closeEditModal() {
    document.getElementById('editModal')?.classList.remove('active');
    editingId = null;
}

async function saveEdit() {
    if (!editingId) return;
    
    const title = document.getElementById('editTitle').value.trim();
    const type = document.getElementById('editType').value;
    const date = document.getElementById('editDate').value;
    const ratingEl = document.querySelector('input[name="editRating"]:checked');
    const rating = ratingEl ? parseInt(ratingEl.value) : 0;
    const comment = document.getElementById('editComment').value.trim();
    
    if (!title || !date) { showToast('请填写名称和日期', 'error'); return; }
    
    const updates = { title, type, date, rating, comment };
    
    // 先关闭弹窗，再异步保存
    const id = editingId;
    closeEditModal();
    
    const idx = records.findIndex(r => r.id === id);
    if (idx !== -1) Object.assign(records[idx], updates);
    
    renderAll();
    showToast('✅ 已保存修改', 'success');
    
    try {
        const backendUpdates = mapFrontendToBackend(updates);
        await fetch(`${API_BASE}/records/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${getToken()}` },
            body: JSON.stringify(backendUpdates)
        });
    } catch {}
}

// ========== 删除记录 ==========
function openDeleteModal(id) {
    deletingId = id;
    document.getElementById('deleteModal')?.classList.add('active');
}

function closeDeleteModal() {
    document.getElementById('deleteModal')?.classList.remove('active');
    deletingId = null;
}

async function confirmDelete() {
    if (!deletingId) return;
    
    const id = deletingId;
    closeDeleteModal();
    
    records = records.filter(r => r.id !== id);
    renderAll();
    showToast('🗑️ 已撕掉记录', 'info');
    
    try {
        await fetch(`${API_BASE}/records/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${getToken()}` }
        });
    } catch {}
}

// ========== 心情选择 ==========
function selectMood(btn) {
    const parent = btn.closest('.mood-selector');
    parent.querySelectorAll('.mood-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
}

// ========== 成就检查 ==========
function checkStreakAchievement() {
    const streak = calculateStreak();
    if (streak === 7) showToast('🔥 连续记录7天！获得"坚持者"贴纸', 'success');
    else if (streak === 15) showToast('💪 连续记录15天！太厉害了', 'success');
    else if (streak === 30) showToast('👑 连续记录30天！你是传说', 'success');
}

// ========== 退出 ==========
function handleLogout() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    window.location.href = 'login.html';
}

// ========== Toast ==========
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    const icons = { success: '✅', error: '❌', info: '💡' };
    toast.innerHTML = `<span>${icons[type] || '💡'}</span><span>${message}</span>`;
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.classList.add('hiding');
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ========== 工具函数 ==========
function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
}

function escHtml(str) {
    if (!str) return '';
    return str.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function getMostFrequent(arr) {
    const counts = {};
    arr.forEach(item => { counts[item] = (counts[item] || 0) + 1; });
    return Object.entries(counts).sort((a,b) => b[1] - a[1])[0]?.[0] || '';
}
