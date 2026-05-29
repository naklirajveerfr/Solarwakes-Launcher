// ══════════════════════════════════════════════════════════════
//  PyCraft Launcher — Frontend Logic
//  Fix: loadSettings() is now in try-catch so a settings crash
//       can no longer prevent attemptAutoLogin() from running.
// ══════════════════════════════════════════════════════════════

// ── State ──────────────────────────────────────────────────────
let currentUser     = "";
let selectedVersion = "";
let isPlaying       = false;
let friendsData     = {};

// ── Init / Autologin ───────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {

    // Wrapped in try-catch: a settings crash will no longer kill autologin
    try { loadSettings(); } catch (e) { console.warn("Settings load failed, using defaults:", e); }

    await new Promise(r => setTimeout(r, 600));

    async function attemptAutoLogin(retries = 3) {
        try {
            const session = await eel.get_saved_session()();
            if (session?.username) {
                await login(session.username, session.password);
            } else if (retries > 0) {
                setTimeout(() => attemptAutoLogin(retries - 1), 600);
            }
        } catch (e) {
            if (retries > 0) setTimeout(() => attemptAutoLogin(retries - 1), 1000);
            else console.error("Backend connection failed:", e);
        }
    }

    attemptAutoLogin();
});

// ── Settings ───────────────────────────────────────────────────
function hexToRgb(hex) {
    hex = hex.replace(/^#?([a-f\d])([a-f\d])([a-f\d])$/i, (m, r, g, b) => r + r + g + g + b + b);
    const r = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
    return r ? { r: parseInt(r[1], 16), g: parseInt(r[2], 16), b: parseInt(r[3], 16) } : { r: 6, g: 14, b: 8 };
}

function updateUI() {
    const c1        = document.getElementById('set-c1').value;
    const c2        = document.getElementById('set-c2').value;
    const c3        = document.getElementById('set-c3').value;
    const c4        = document.getElementById('set-c4').value;
    const cardColor = document.getElementById('set-card-color').value;
    const playColor = document.getElementById('set-play-color').value;
    const speed     = document.getElementById('set-speed').value;
    const opac      = document.getElementById('set-opac').value;      // ← was missing from HTML before
    const blur      = document.getElementById('set-blur').value;
    const gradOn    = document.getElementById('set-gradient-toggle').checked;

    document.getElementById('speed-val').innerText = speed;
    document.getElementById('opac-val').innerText  = opac;
    document.getElementById('blur-val').innerText  = blur;

    const root = document.documentElement;
    root.style.setProperty('--grad-1',     c1);
    root.style.setProperty('--grad-2',     c2);
    root.style.setProperty('--grad-3',     c3);
    root.style.setProperty('--grad-4',     c4);
    root.style.setProperty('--grad-speed', speed + 's');
    root.style.setProperty('--card-blur',  blur  + 'px');

    const cr = hexToRgb(cardColor);
    root.style.setProperty('--card-bg', `rgba(${cr.r},${cr.g},${cr.b},${opac / 100})`);

    root.style.setProperty('--play-btn-bg', playColor);
    const pr = hexToRgb(playColor);
    root.style.setProperty('--play-btn-glow', `rgba(${pr.r},${pr.g},${pr.b},0.38)`);

    document.querySelectorAll('.extra-picker').forEach(el => el.classList.toggle('hidden', !gradOn));
    document.getElementById('color-pickers-label').innerText = gradOn ? 'Gradient Colors' : 'Background Color';
    document.body.classList.toggle('gradient-bg', gradOn);

    localStorage.setItem('pycraft_settings',
        JSON.stringify({ c1, c2, c3, c4, cardColor, playColor, speed, opac, blur, gradOn }));
}

function loadSettings() {
    const s = JSON.parse(localStorage.getItem('pycraft_settings') || 'null');
    if (s) {
        document.getElementById('set-c1').value         = s.c1        || '#030706';
        document.getElementById('set-c2').value         = s.c2        || '#060e08';
        document.getElementById('set-c3').value         = s.c3        || '#071510';
        document.getElementById('set-c4').value         = s.c4        || '#030706';
        document.getElementById('set-card-color').value = s.cardColor || '#060e08';
        document.getElementById('set-play-color').value = s.playColor || '#22c55e';
        document.getElementById('set-speed').value      = s.speed     || '15';
        document.getElementById('set-opac').value       = s.opac      || '30';
        document.getElementById('set-blur').value       = s.blur      || '16';
        document.getElementById('set-gradient-toggle').checked = s.gradOn !== false;
    }
    updateUI();
}

function resetSettings() {
    document.getElementById('set-c1').value         = '#030706';
    document.getElementById('set-c2').value         = '#060e08';
    document.getElementById('set-c3').value         = '#071510';
    document.getElementById('set-c4').value         = '#030706';
    document.getElementById('set-card-color').value = '#060e08';
    document.getElementById('set-play-color').value = '#22c55e';
    document.getElementById('set-speed').value      = '15';
    document.getElementById('set-opac').value       = '30';
    document.getElementById('set-blur').value       = '16';
    document.getElementById('set-gradient-toggle').checked = true;
    updateUI();
}

function openSettings()  { document.getElementById('settings-modal').classList.remove('hidden'); }
function closeSettings() { document.getElementById('settings-modal').classList.add('hidden');    }


// ── Auth Helpers ────────────────────────────────────────────────
function showAuthMessage(msg, type = 'error') {
    const el  = document.getElementById('auth-error');
    const err = (type === 'error');
    el.style.color       = err ? '#f87171'                  : '#4ade80';
    el.style.background  = err ? 'rgba(239,68,68,0.10)'    : 'rgba(74,222,128,0.07)';
    el.style.borderColor = err ? 'rgba(239,68,68,0.22)'    : 'rgba(74,222,128,0.22)';
    el.innerText = msg;
    el.classList.remove('hidden');
}

function clearAuthUI() {
    document.getElementById('auth-error').classList.add('hidden');
    document.getElementById('username')?.classList.remove('error');
    document.getElementById('password')?.classList.remove('error');
}

function handleLoginSuccess(user, avatar) {
    currentUser = user;
    document.getElementById('player-name').innerText = user;
    document.getElementById('prof-name').innerText   = user;
    document.getElementById('player-avatar').src     = avatar;

    const auth = document.getElementById('auth-screen');
    const app  = document.getElementById('app-screen');
    auth.style.opacity = '0';
    setTimeout(() => {
        auth.classList.add('hidden');
        app.classList.remove('hidden');
        setTimeout(() => { app.style.opacity = '1'; }, 40);
        loadVersions();
    }, 440);
}

function showRegister() {
    document.getElementById('login-form').classList.add('hidden');
    document.getElementById('register-form').classList.remove('hidden');
    clearAuthUI();
}

function showLogin() {
    document.getElementById('register-form').classList.add('hidden');
    document.getElementById('login-form').classList.remove('hidden');
    clearAuthUI();
}


// ── Authentication ──────────────────────────────────────────────
async function login(autoUser = null, autoPass = null) {
    const user = autoUser || document.getElementById('username').value.trim();
    const pass = autoPass || document.getElementById('password').value;

    if (!user || !pass) { showAuthMessage('Username and password required.'); return; }
    if (autoUser) showAuthMessage('Authenticating saved session…', 'info');

    const res = await eel.auth_login(user, pass)();
    if (res.error) {
        showAuthMessage(res.error);
        const isPwErr = res.error.toLowerCase().includes('password');
        document.getElementById('password')?.classList.toggle('error',  isPwErr);
        document.getElementById('username')?.classList.toggle('error', !isPwErr);
    } else {
        handleLoginSuccess(user, res.avatar);
    }
}

async function register() {
    const user  = document.getElementById('reg-username').value.trim();
    const email = document.getElementById('reg-email').value.trim();
    const pass  = document.getElementById('reg-password').value;

    if (!user || !email || !pass) { showAuthMessage('All fields are required.'); return; }
    showAuthMessage('Creating account…', 'info');

    const res = await eel.auth_register(user, pass, email)();
    if (res.error) showAuthMessage(res.error);
    else handleLoginSuccess(user, res.avatar);
}


// ── Profile & Account Switcher ──────────────────────────────────
async function openProfile() {
    document.getElementById('profile-modal').classList.remove('hidden');
    const data = await eel.get_user_profile(currentUser)();
    if (data) {
        document.getElementById('prof-joined').innerText  = data.joined;
        document.getElementById('prof-friends').innerText = data.friends;
    }
    loadSavedAccounts();
}
function closeProfile() { document.getElementById('profile-modal').classList.add('hidden'); }

async function loadSavedAccounts() {
    const data = await eel.get_all_accounts()();
    const list = document.getElementById('saved-accounts-list');
    list.innerHTML = '';
    if (!data?.accounts?.length) {
        list.innerHTML = `<p class="section-label" style="letter-spacing:2px;color:var(--text-ghost);text-align:center;padding:12px 0;">No saved accounts</p>`;
        return;
    }
    const makeBtn = (label, onclick, extraStyle) =>
        `<button onclick="${onclick}" style="font-family:Rajdhani,sans-serif;font-size:11px;font-weight:700;letter-spacing:1px;padding:3px 10px;border-radius:7px;cursor:pointer;transition:all 0.2s;${extraStyle}">${label}</button>`;

    data.accounts.forEach(acc => {
        const isActive = acc.username === currentUser;
        list.innerHTML += `
        <div class="account-card ${isActive ? 'active-account' : ''}">
            <div class="flex items-center gap-2 min-w-0">
                <img src="${acc.avatar}" style="width:30px;height:30px;border-radius:7px;background:var(--bg-surface);flex-shrink:0;">
                <span style="font-family:Rajdhani,sans-serif;font-weight:600;font-size:14px;color:var(--text-bright);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
                    ${acc.username}${isActive ? ' <span style="color:#4ade80;font-size:12px;">✓</span>' : ''}
                </span>
            </div>
            <div class="flex gap-1 shrink-0">
                ${!isActive ? makeBtn('SWITCH', `switchAccount('${acc.username}')`, 'color:white;background:rgba(74,222,128,0.10);border:1px solid rgba(74,222,128,0.22);') : ''}
                ${makeBtn('✕', `removeAccount('${acc.username}')`, 'color:#f87171;background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.18);')}
            </div>
        </div>`;
    });
}

async function initializeAppState() {
    const session = await eel.get_saved_session()();
    if (session) {
        currentUser = session.username;
        document.getElementById('player-name').innerText = currentUser;
        document.getElementById('prof-name').innerText   = currentUser;
        document.getElementById('auth-screen').classList.add('hidden');
        const app = document.getElementById('app-screen');
        app.classList.remove('hidden');
        app.style.opacity = '1';
        loadVersions();
    }
}

async function switchAccount(username) {
    if (await eel.switch_to_account(username)()) {
        document.getElementById('profile-modal').classList.add('hidden');
        const app = document.getElementById('app-screen');
        app.style.opacity = '0';
        setTimeout(() => {
            app.classList.add('hidden');
            const auth = document.getElementById('auth-screen');
            auth.classList.remove('hidden');
            auth.style.opacity = '1';
            initializeAppState();
        }, 300);
    }
}

async function removeAccount(username) {
    await eel.remove_saved_account(username)();
    if (username === currentUser) window.location.reload();
    else loadSavedAccounts();
}

async function addNewAccount() {
    await eel.set_active_account_null()();
    window.location.reload();
}

async function uploadSkin() {
    const avatar = await eel.upload_skin(currentUser)();
    if (avatar) document.getElementById('player-avatar').src = avatar;
}


// ── Version Helpers ─────────────────────────────────────────────
function getVersionIcon(ver) {
    const v = ver.toLowerCase();
    if (v.includes('forge') || v.includes('fabric') || v.includes('quilt') || v.includes('neoforge')) return '⚙️';
    if (v.includes('snapshot') || v.includes('pre') || v.includes('rc'))   return '🧪';
    if (v.includes('1.21') || v.includes('1.20') || v.includes('1.19'))    return '🌿';
    return '📦';
}

function getTypeBadgeClass(type) {
    const t = (type || '').toLowerCase();
    if (t === 'release')  return 'badge-release';
    if (t === 'snapshot') return 'badge-snapshot';
    if (t.includes('mod') || t.includes('forge') || t.includes('fabric')) return 'badge-modded';
    return 'badge-unknown';
}


// ── Dashboard ────────────────────────────────────────────────────
async function loadVersions() {
    const versions = await eel.get_versions()();
    const list     = document.getElementById('version-list');
    document.getElementById('version-count').innerText = versions.length;
    list.innerHTML = '';

    if (!versions.length) {
        list.innerHTML = `<div class="text-center py-6 section-label" style="letter-spacing:1px;color:var(--text-ghost);">No versions found</div>`;
        return;
    }

    versions.forEach(ver => {
        const div = document.createElement('div');
        div.className = 'version-slot';
        div.innerHTML = `
            <div class="version-slot-icon">${getVersionIcon(ver)}</div>
            <div class="min-w-0 flex-1">
                <p style="font-family:Rajdhani,sans-serif;font-size:13px;font-weight:600;color:var(--text-primary);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${ver}</p>
            </div>`;
        div.onclick = () => selectVersion(ver, div);
        list.appendChild(div);
    });
}

async function selectVersion(ver, element) {
    selectedVersion = ver;
    document.querySelectorAll('.version-slot').forEach(el => el.classList.remove('active'));
    element.classList.add('active');
    document.getElementById('play-btn').classList.add('has-version');

    const d = await eel.get_version_details(ver)();

    document.getElementById('details-empty').classList.add('hidden');
    document.getElementById('details-content').classList.remove('hidden');

    document.getElementById('det-name').innerText = d.id;
    document.getElementById('det-icon').innerText = getVersionIcon(ver);

    const badge     = document.getElementById('det-type');
    badge.innerText = (d.type || 'unknown').toUpperCase();
    badge.className = 'version-type-badge ' + getTypeBadgeClass(d.type);

    document.getElementById('det-date').innerText = d.date || '—';
    document.getElementById('det-base').innerText = d.base || '—';
}

function toggleConsole() {
    // flex-col class on #console-area means removing 'hidden' makes it display:flex
    document.getElementById('console-area').classList.toggle('hidden');
}


// ── Game Launch ──────────────────────────────────────────────────
async function playGame() {
    if (!selectedVersion || isPlaying) return;
    isPlaying = true;

    const btn       = document.getElementById('play-btn');
    btn.disabled    = true;
    btn.innerText   = 'LAUNCHING…';
    btn.classList.remove('has-version');

    document.getElementById('status-text').innerText = 'IN GAME';
    document.getElementById('status-dot').className  = 'status-ingame';
    document.getElementById('console-logs').innerHTML = '';

    if (document.getElementById('console-area').classList.contains('hidden')) toggleConsole();

    await eel.launch_game(currentUser, selectedVersion)();
}

eel.expose(ui_log);
function ui_log(msg, type) {
    const logBox  = document.getElementById('console-logs');
    const div     = document.createElement('div');
    div.className = 'console-log' +
        (type === 'error' ? ' error' : type === 'success' ? ' success' : '');
    div.innerText = msg;
    logBox.appendChild(div);
    logBox.scrollTop = logBox.scrollHeight;
}

eel.expose(ui_game_exit);
function ui_game_exit() {
    isPlaying = false;
    const btn   = document.getElementById('play-btn');
    btn.disabled  = false;
    btn.innerText = 'PLAY';
    if (selectedVersion) btn.classList.add('has-version');
    document.getElementById('status-text').innerText = 'ONLINE';
    document.getElementById('status-dot').className  = 'status-online';
}


// ── Friends System ────────────────────────────────────────────────
function openFriends()  { document.getElementById('friends-modal').classList.remove('hidden'); reloadFriends(); }
function closeFriends() { document.getElementById('friends-modal').classList.add('hidden');    }

function switchFriendTab(tab) {
    ['list', 'reqs', 'add'].forEach(t => {
        document.getElementById('tab-' + t).classList.toggle('active', t === tab);
    });
    const listView = document.getElementById('f-list-view');
    const addView  = document.getElementById('f-add-view');
    listView.classList.toggle('hidden',  tab === 'add');
    addView.classList.toggle('hidden',   tab !== 'add');
    if (tab === 'add') {
        document.getElementById('f-search-res').innerHTML = '';
    } else {
        renderFriendsList(tab);
    }
}

async function reloadFriends() {
    friendsData = await eel.fetch_friends(currentUser)();
    const activeTab = document.getElementById('tab-reqs').classList.contains('active') ? 'reqs' : 'list';
    switchFriendTab(activeTab);
}

function renderFriendsList(mode) {
    const box = document.getElementById('f-list-view');
    box.innerHTML = '';
    let count = 0;

    const btnStyle = 'font-family:Rajdhani,sans-serif;font-size:12px;font-weight:700;letter-spacing:1px;padding:4px 12px;border-radius:8px;cursor:pointer;transition:all 0.2s;';
    const makeBtn  = (label, onclick, extra) =>
        `<button onclick="${onclick}" style="${btnStyle}${extra}">${label}</button>`;

    for (const [key, data] of Object.entries(friendsData)) {
        const ok  = data.status === 'accepted';
        const inc = data.status === 'pending_incoming';
        const out = data.status === 'pending_outgoing';

        if (mode === 'list' && !ok)  continue;
        if (mode === 'reqs' && ok)   continue;
        count++;

        const dotCls = { online: 'status-online', 'in-game': 'status-ingame' }[data.status_now] || 'status-offline';

        let actions = '';
        if (ok) {
            actions = makeBtn('REMOVE', `doFriendAct('${key}','remove')`,
                'color:#f87171;background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.20);');
        } else if (inc) {
            actions =
                makeBtn('ACCEPT',  `doFriendAct('${key}','accept','${data.username}')`,
                    'color:#4ade80;background:rgba(74,222,128,0.10);border:1px solid rgba(74,222,128,0.25);') +
                makeBtn('DECLINE', `doFriendAct('${key}','decline')`,
                    'color:#f87171;background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.20);');
        } else if (out) {
            actions =
                `<span style="${btnStyle}color:#fbbf24;background:transparent;border:1px solid rgba(251,191,36,0.20);cursor:default;">PENDING</span>` +
                makeBtn('CANCEL', `doFriendAct('${key}','cancel')`,
                    'color:#94a3b8;background:rgba(100,116,139,0.10);border:1px solid rgba(100,116,139,0.20);');
        }

        box.innerHTML += `
        <div class="friend-card">
            <div class="flex items-center gap-3">
                <img src="${data.avatar}" style="width:40px;height:40px;border-radius:10px;background:var(--bg-surface);flex-shrink:0;">
                <div>
                    <p style="font-family:Rajdhani,sans-serif;font-weight:700;font-size:15px;color:var(--text-bright);">${data.username}</p>
                    ${ok ? `<p style="font-family:Rajdhani,sans-serif;font-size:12px;font-weight:600;display:flex;align-items:center;gap:4px;">
                        <span class="${dotCls}" style="font-size:7px;">●</span>${data.status_now}
                    </p>` : ''}
                </div>
            </div>
            <div class="flex gap-2 items-center">${actions}</div>
        </div>`;
    }

    if (!count) {
        box.innerHTML = `<p class="section-label text-center" style="letter-spacing:2px;color:var(--text-ghost);padding:32px 0;">NOTHING TO SEE HERE</p>`;
    }
}

async function searchFriend() {
    const q   = document.getElementById('f-search-input').value.trim();
    const box = document.getElementById('f-search-res');
    if (!q) return;

    box.innerHTML = `<p class="section-label" style="color:var(--text-dim);letter-spacing:2px;margin-top:8px;">SEARCHING...</p>`;
    const res = await eel.search_user(q)();

    if (!res) {
        box.innerHTML = `<p class="section-label" style="color:#f87171;letter-spacing:1px;margin-top:8px;">USER NOT FOUND</p>`;
        return;
    }

    const existing = friendsData[res.key];
    const btnStyle = 'font-family:Rajdhani,sans-serif;font-size:12px;font-weight:700;letter-spacing:1px;padding:4px 14px;border-radius:8px;cursor:pointer;';
    let act = `<button onclick="doFriendAct('${res.key}','add','${res.username}')" style="${btnStyle}color:#4ade80;background:rgba(74,222,128,0.10);border:1px solid rgba(74,222,128,0.25);">ADD FRIEND</button>`;

    if (res.username === currentUser)       act = `<span class="section-label" style="color:var(--text-dim);letter-spacing:1px;">YOU</span>`;
    else if (existing?.status === 'accepted') act = `<span class="section-label" style="color:#4ade80;letter-spacing:1px;">FRIENDS ✓</span>`;
    else if (existing)                        act = `<span class="section-label" style="color:#fbbf24;letter-spacing:1px;">PENDING</span>`;

    box.innerHTML = `
    <div class="friend-card mt-2">
        <div class="flex items-center gap-3">
            <img src="${res.avatar}" style="width:40px;height:40px;border-radius:10px;background:var(--bg-surface);flex-shrink:0;">
            <p style="font-family:Rajdhani,sans-serif;font-weight:700;font-size:15px;color:var(--text-bright);">${res.username}</p>
        </div>
        ${act}
    </div>`;
}

async function doFriendAct(targetKey, action, targetName = "") {
    await eel.friend_action(currentUser, targetKey, action, targetName)();
    reloadFriends();
}