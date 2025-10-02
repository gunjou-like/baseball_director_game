let isAuthenticated = false;
let gameState = {
    teams: null, // 全チームの選手リスト
    schedule: [], // ユーザーの試合履歴
    current_order: { batters: [], pitcher: null } // ユーザーの保存済みオーダー
};

// --------------------------------------------------
// UI/ナビゲーション関連
// --------------------------------------------------

/**
 * すべてのゲーム画面要素とログイン画面要素の表示/非表示を制御
 * @param {boolean} showGame - ゲーム画面を表示するかどうか
 */
const updateUI = (showGame) => {
    const gamePages = document.querySelectorAll('.page-section:not(#login-page)');
    const loginPage = document.getElementById('login-page');
    const navBar = document.querySelector('.nav-bar');
    const logoutBtn = document.getElementById('logout-btn');

    if (showGame) {
        // ゲーム画面を表示
        gamePages.forEach(p => p.classList.remove('hidden'));
        loginPage.classList.add('hidden');
        navBar.classList.remove('hidden');
        
        // ★修正点: ログアウトボタンを再表示
        if (logoutBtn) logoutBtn.style.display = 'block'; 
        
        console.log("[UI] ゲーム画面を表示しました。");
    } else {
        // ログイン画面を表示
        gamePages.forEach(p => p.classList.add('hidden'));
        loginPage.classList.remove('hidden');
        navBar.classList.add('hidden');
        
        // ★修正点: ログアウトボタンを非表示
        if (logoutBtn) logoutBtn.style.display = 'none'; 
        
        console.log("[UI] ログイン画面を表示しました。");
    }
};

/**
 * ページセクションの表示を切り替える
 * @param {string} pageId - 表示したいセクションのID
 */
const showPage = (pageId) => {
    if (!pageId) {
        console.error("[NAV ERROR] 遷移先ページIDが未定義です。");
        return;
    }
    
    document.querySelectorAll('.page-section').forEach(section => {
        section.classList.remove('active');
    });
    const targetPage = document.getElementById(pageId);
    if (targetPage) {
        targetPage.classList.add('active');
        console.log(`[NAV] ページを「${pageId}」に切り替えます。`);

        // 各ページ固有のレンダリング
        if (pageId === 'order-page') {
            renderOrderPage();
        } else if (pageId === 'schedule-page') {
            renderSchedulePage();
        }
    } else {
        console.error(`[NAV ERROR] ID: ${pageId} の要素が見つかりません。`);
    }
};

/**
 * 認証状態をチェックし、適切な画面を表示する
 * @param {string} defaultPageId - 認証成功時に表示するデフォルトのページID
 */
const checkAuthAndShowPage = (defaultPageId) => {
    if (isAuthenticated) {
        updateUI(true);
        showPage(defaultPageId);
    } else {
        updateUI(false);
        showPage('login-page');
    }
};

// --------------------------------------------------
// 認証・セッション管理
// --------------------------------------------------

/**
 * 認証情報（セッションクッキー）を含む安全なfetch関数
 * 401エラーを検出した場合、自動的にログアウト処理を行う
 */
const safeFetch = async (url, options = {}) => {
    try {
        const response = await fetch(url, { 
            ...options,
            credentials: 'include' // クッキーを送信
        });

        if (response.status === 401) {
            console.log("[AUTH FAIL] 401 Unauthenticated. セッションをクリアしログインへ。");
            isAuthenticated = false;
            // ログインページへ強制リダイレクト (ただし、リロードはしない)
            checkAuthAndShowPage('login-page');
            return null;
        }

        return response;
    } catch (error) {
        console.error(`[FETCH ERROR] ${url}:`, error);
        return null; // ネットワークエラーの場合
    }
};

/**
 * ログイン処理
 */
const handleLogin = async (username, password) => {
    const messageArea = document.getElementById('login-message');
    messageArea.textContent = 'ログイン中...';

    const response = await safeFetch('/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
    });

    if (response && response.ok) {
        isAuthenticated = true;
        messageArea.textContent = 'ログイン成功！';
        console.log("[AUTH] ログイン成功。");
        
        // ログイン成功後、ゲーム状態をロードし、ホームへ遷移
        await loadGameState();
        checkAuthAndShowPage('home-page');
    } else if (response) {
        const errorData = await response.json();
        messageArea.textContent = `ログイン失敗: ${errorData.error}`;
        console.log(`[AUTH FAIL] ログイン失敗: ${errorData.error}`);
    } else {
        messageArea.textContent = 'ネットワーク接続エラー。サーバーを確認してください。';
    }
};

/**
 * ログアウト処理
 */
const handleLogout = async () => {
    const response = await safeFetch('/logout', { method: 'GET' });

    if (response && response.ok) {
        // サーバー側でセッションがクリアされた
        isAuthenticated = false;
        console.log("[AUTH] ログアウト成功。");
        // ログイン画面へ遷移
        checkAuthAndShowPage('login-page');
    } else {
        console.error("[AUTH ERROR] ログアウト通信エラー: サーバー応答が不正です。");
    }
};

// --------------------------------------------------
// ゲームデータ管理 (API連携)
// --------------------------------------------------

/**
 * 起動時の認証チェックとゲーム状態の初期ロード
 */
const loadGameState = async () => {
    // HEADリクエストで認証チェックとデータ取得を同時に行う
    console.log("[DATA] ゲーム状態をロード中...");
    
    // /api/game_stateは認証必須
    const response = await safeFetch('/api/game_state', { method: 'GET' });

    if (response && response.ok) {
        const data = await response.json();
        
        // グローバル状態を更新
        gameState.teams = data.teams;
        gameState.schedule = data.schedule;
        gameState.current_order = data.current_order;

        isAuthenticated = true;
        console.log("[DATA] ゲーム状態のロード完了。", gameState);
        return true;
    } else if (isAuthenticated) {
        // 認証フラグは立っているがデータ取得に失敗した場合
        console.error("[DATA ERROR] ゲームデータのロードに失敗しました。");
    }
    return false;
};

// --------------------------------------------------
// オーダー決定画面 (ID: order-page)
// --------------------------------------------------

const renderOrderPage = () => {
    const batterOrderContainer = document.getElementById('batter-order-container');
    const pitcherSelectionContainer = document.getElementById('pitcher-selection-container');
    const userTeamName = "自チーム (ベイカーズ)";
    
    if (!gameState.teams) {
        batterOrderContainer.innerHTML = '選手データをロード中...';
        pitcherSelectionContainer.innerHTML = '';
        return;
    }

    const userTeamPlayers = gameState.teams[userTeamName] || [];
    const batterPlayers = userTeamPlayers.filter(p => !p.is_pitcher);
    const pitcherPlayers = userTeamPlayers.filter(p => p.is_pitcher);

    // 打者スタメンのUIを動的に生成
    batterOrderContainer.innerHTML = '';
    for (let i = 1; i <= 9; i++) {
        const group = document.createElement('div');
        group.classList.add('player-select-group');
        group.innerHTML = `<label for="batter-${i}">${i}番</label><select id="batter-${i}"></select>`;
        
        const select = group.querySelector('select');
        select.innerHTML = '<option value="">選手を選択</option>';
        batterPlayers.forEach(player => {
            const option = document.createElement('option');
            option.value = player.id; 
            option.textContent = `${player.name} (${player.id})`;
            
            // 以前保存されたオーダーを初期値として設定
            if (gameState.current_order.batters[i - 1] === player.id) {
                option.selected = true;
            }
            select.appendChild(option);
        });
        batterOrderContainer.appendChild(group);
    }

    // 先発投手のUIを動的に生成
    pitcherSelectionContainer.innerHTML = '';
    const group = document.createElement('div');
    group.classList.add('player-select-group');
    group.innerHTML = `<label for="pitcher">先発</label><select id="pitcher"></select>`;
    
    const select = group.querySelector('select');
    select.innerHTML = '<option value="">選手を選択</option>';
    pitcherPlayers.forEach(player => {
        const option = document.createElement('option');
        option.value = player.id;
        option.textContent = `${player.name} (${player.id})`;
        
        // 以前保存されたオーダーを初期値として設定
        if (gameState.current_order.pitcher === player.id) {
            option.selected = true;
        }
        select.appendChild(option);
    });
    pitcherSelectionContainer.appendChild(group);
};

// --------------------------------------------------
// 日程進行画面 (ID: schedule-page)
// --------------------------------------------------

const renderSchedulePage = () => {
    const scheduleDisplay = document.getElementById('game-schedule');
    const rankingDisplay = document.getElementById('league-ranking');
    
    // 試合履歴の表示
    scheduleDisplay.innerHTML = '<h3>試合結果</h3>';
    
    if (gameState.schedule && gameState.schedule.length > 0) {
        // 最新の結果を上から表示
        gameState.schedule.slice().reverse().forEach(result => {
            const li = document.createElement('li');
            li.textContent = `${result.home_team} vs ${result.away_team} - スコア: ${result.home_score} - ${result.away_score} (${result.result})`;
            li.classList.add(result.result === '勝利' ? 'result-win' : result.result === '敗北' ? 'result-lose' : 'result-draw');
            scheduleDisplay.appendChild(li);
        });
    } else {
        scheduleDisplay.innerHTML += '<li>まだ試合がありません。</li>';
    }

    rankingDisplay.innerHTML = '<li>順位データは後で実装します。</li>';
};

/**
 * 試合をシミュレートし、DBに結果を保存する
 */
const advanceDay = async () => {
    if (!isAuthenticated) return;
    console.log("[GAME] 1日進めます。試合結果を生成中...");

    const response = await safeFetch('/api/simulate_game', { method: 'GET' });

    if (response && response.ok) {
        // 試合結果生成とDB保存がサーバー側で完了
        console.log("[GAME] 試合結果をDBに記録しました。");
        
        // 最新のゲーム状態を再ロードしてUIを更新
        await loadGameState();
        renderSchedulePage(); // スケジュール画面を再描画
    } else {
        console.error("[GAME ERROR] 試合の進行中にエラーが発生しました。");
    }
};

// --------------------------------------------------
// イベントリスナーと初期化
// --------------------------------------------------

const setupEventListeners = () => {
    // ナビゲーションボタンにイベントリスナーを設定
    document.querySelectorAll('.nav-btn').forEach(button => {
        button.addEventListener('click', (event) => {
            if (isAuthenticated) {
                const targetPageId = event.target.dataset.target;
                showPage(targetPageId);
            }
        });
    });

    // ログアウトボタン
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) logoutBtn.addEventListener('click', handleLogout);

    // ログインフォームの処理
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.onsubmit = (e) => {
            e.preventDefault();
            const username = document.getElementById('username').value;
            const password = document.getElementById('password').value;
            handleLogin(username, password);
        };
    }

    // オーダー決定ボタンのイベントリスナー
    const submitOrderBtn = document.getElementById('submit-order-btn');
    if (submitOrderBtn) {
        submitOrderBtn.addEventListener('click', async () => {
            if (!isAuthenticated) return;
            const messageArea = document.getElementById('order-message');
            const orderData = {
                batters: [],
                pitcher: null
            };

            let hasError = false;
            const selectedPlayerIds = new Set();
            
            // 打者オーダー（1-9番）の選手IDを取得
            for (let i = 1; i <= 9; i++) {
                const selectElement = document.getElementById(`batter-${i}`);
                const playerId = selectElement.value;

                if (!playerId) {
                    messageArea.textContent = `${i}番の選手を選択してください。`;
                    hasError = true;
                    break;
                }
                if (selectedPlayerIds.has(playerId)) {
                    messageArea.textContent = `打順に選手ID: ${playerId}が重複しています。`;
                    hasError = true;
                    break;
                }
                selectedPlayerIds.add(playerId);
                orderData.batters.push(parseInt(playerId)); 
            }
            
            if (hasError) return;

            // 先発投手の選手IDを取得
            const pitcherSelect = document.getElementById('pitcher');
            const pitcherId = pitcherSelect.value;
            if (!pitcherId) {
                messageArea.textContent = '先発投手を指定してください。';
                return;
            }
            if (selectedPlayerIds.has(pitcherId)) {
                messageArea.textContent = `先発投手が打順に重複しています。`;
                return;
            }
            orderData.pitcher = parseInt(pitcherId); 

            console.log("[ORDER] オーダーを保存します:", orderData);
            
            // Flask APIに選手IDリストを送信し、DBに保存
            const response = await safeFetch('/api/order', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(orderData)
            });

            if (response && response.ok) {
                const data = await response.json();
                messageArea.textContent = `オーダー保存成功！`;
                // グローバル状態の current_order を更新 (DB書き込み後)
                gameState.current_order = orderData;
            } else {
                messageArea.textContent = 'オーダー保存中にエラーが発生しました。';
            }
        });
    }


    // 日程進行ボタンにイベントリスナーを設定
    const advanceDayBtn = document.getElementById('advance-day-btn');
    if (advanceDayBtn) advanceDayBtn.addEventListener('click', advanceDay);
};

// アプリケーション初期化
document.addEventListener('DOMContentLoaded', async () => {
    console.log("アプリのロジックがスタートしました。");
    setupEventListeners();

    // 起動時の認証チェックとデータロード
    console.log("[INIT] 起動時の認証状態を確認中...");
    const isAuthenticatedOnLoad = await loadGameState();

    if (isAuthenticatedOnLoad) {
        console.log("[INIT] 既存セッションを検出しました。");
        checkAuthAndShowPage('home-page');
    } else {
        console.log("[INIT] セッションが見つかりませんでした。");
        checkAuthAndShowPage('login-page');
    }
});