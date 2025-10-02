// -------------------------------------------------------------------------
// グローバル定数と状態管理
// -------------------------------------------------------------------------

const HOME_PAGE_ID = 'home-page';
const ORDER_PAGE_ID = 'order-page';
const SCHEDULE_PAGE_ID = 'schedule-page';
const LOGIN_PAGE_ID = 'login-page';

let isAuthenticated = false; // 認証状態フラグ

// -------------------------------------------------------------------------
// ユーティリティ関数
// -------------------------------------------------------------------------

/**
 * 保護されたエンドポイントへのリクエストを安全に実行し、401エラーを処理します。
 * @param {string} url - リクエストURL
 * @param {object} options - fetchオプション
 * @returns {Promise<Response>} fetchのレスポンスオブジェクト
 */
const safeFetch = async (url, options = {}) => {
    try {
        const response = await fetch(url, {
            ...options,
            // 認証情報（クッキー）を確実に送信
            credentials: 'include'
        });

        if (response.status === 401) {
            console.warn(`[AUTH] 保護されたエンドポイント (${url}) へのアクセスが拒否されました (401)。`);
            // 強制的に未認証状態に設定し、ログイン画面へ遷移
            isAuthenticated = false;
            updateAuthUI();
            showPage(LOGIN_PAGE_ID); 
            
            // 呼び出し元が further processing を停止できるようにカスタムエラーをスロー
            throw new Error("Unauthenticated access detected.");
        }

        return response;
    } catch (error) {
        // ネットワークエラーなどを捕捉
        console.error(`[FETCH ERROR] ${url} の通信中にエラーが発生:`, error);
        throw error;
    }
};

/**
 * 指定されたページIDに基づいて画面を切り替えます。
 * @param {string} pageId - 表示するページセクションのID
 */
const showPage = (pageId) => {
    if (!document.getElementById(pageId)) {
        console.error(`[NAV ERROR] ID: ${pageId} の要素が見つかりません。`);
        return;
    }

    console.log(`[NAV] ページを「${pageId}」に切り替えます。`);
    document.querySelectorAll('.page-section').forEach(section => {
        section.classList.remove('active');
    });
    document.getElementById(pageId).classList.add('active');
    console.log(`[NAV] #${pageId} に active クラスを適用しました。`);
};

/**
 * 認証状態に基づいて、ナビゲーションUIの表示/非表示を更新します。
 */
const updateAuthUI = () => {
    const logoutBtn = document.getElementById('logout-btn');
    const navBar = document.querySelector('.nav-bar');
    
    // ナビゲーションボタン（ゲーム画面へのリンク）
    document.querySelectorAll('.nav-btn').forEach(btn => {
        if (btn.dataset.target !== LOGIN_PAGE_ID) {
            btn.disabled = !isAuthenticated;
        }
    });

    if (isAuthenticated) {
        console.log("[UI] ログアウトボタンを表示しました。");
        if (logoutBtn) logoutBtn.style.display = 'block';
        if (navBar) navBar.style.visibility = 'visible';
    } else {
        console.log("[UI] ログイン/ゲーム要素を非表示にしました。");
        if (logoutBtn) logoutBtn.style.display = 'none';
        // 未認証時はナビゲーション全体も非表示にする (CSSでinitial-visibilityをhiddenに設定)
        if (navBar) navBar.style.visibility = 'hidden'; 
    }
};

/**
 * 認証状態をチェックし、アプリケーションの初期画面を表示します。
 * @param {string} [initialPageId=HOME_PAGE_ID] - 認証成功時の遷移先
 */
const checkAuthAndShowPage = async (initialPageId = HOME_PAGE_ID) => {
    console.log("[INIT] 起動時の認証状態を確認中...");

    // 認証チェックのため、保護された最小限のAPIにアクセス
    try {
        const response = await safeFetch('/api/players', { method: 'HEAD' });
        
        // HEADリクエストが成功し、401エラーをスローしなかった場合
        if (response.ok) {
            isAuthenticated = true;
            console.log("[INIT] 既存セッションを検出しました。");
        }
    } catch (error) {
        // safeFetchが401エラーをスローした場合は、catchで捕捉される
        isAuthenticated = false;
        console.log("[INIT] セッションが見つかりませんでした。");
    }
    
    updateAuthUI();

    if (isAuthenticated) {
        // 認証済みの場合、指定された初期画面またはホームに遷移
        showPage(initialPageId);
        // オーダーページが初期画面の場合、レンダリングを呼び出す
        if (initialPageId === ORDER_PAGE_ID) renderOrderPage();
    } else {
        // 未認証の場合、ログイン画面へ遷移
        showPage(LOGIN_PAGE_ID);
        renderLoginPage(); // ログインフォームをレンダリング
    }
};


// -------------------------------------------------------------------------
// 認証ロジック
// -------------------------------------------------------------------------

/**
 * ログイン画面をレンダリングし、イベントリスナーを設定します。
 */
const renderLoginPage = () => {
    const loginForm = document.getElementById('login-form');
    const loginMessage = document.getElementById('login-message');
    
    if (!loginForm) return;

    loginForm.onsubmit = async (event) => {
        event.preventDefault();
        loginMessage.textContent = 'ログイン中...';
        
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;

        try {
            const response = await fetch('/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password }),
                credentials: 'include'
            });

            const data = await response.json();

            if (response.ok) {
                console.log("[AUTH] ログイン成功:", data.message);
                loginMessage.textContent = 'ログイン成功！';
                isAuthenticated = true;
                updateAuthUI();
                // 認証成功後、ホーム画面へ遷移
                showPage(HOME_PAGE_ID);
            } else {
                // 401 Unauthorized またはその他のエラー
                console.warn("[AUTH] ログイン失敗:", data.error);
                loginMessage.textContent = `ログイン失敗: ${data.error || '認証情報が不正です'}`;
                isAuthenticated = false;
                updateAuthUI();
            }
        } catch (error) {
            console.error("[AUTH ERROR] ログイン通信エラー:", error);
            loginMessage.textContent = '通信エラーが発生しました。';
            isAuthenticated = false;
            updateAuthUI();
        }
    };
};

/**
 * ログアウト処理を実行します。
 */
const handleLogout = async () => {
    console.log("[AUTH] ログアウト処理を開始します。");
    try {
        // 修正: ログアウトエンドポイントはJSONを返すようにFlask側を修正済み
        const response = await safeFetch('/logout'); 
        
        if (response.ok) {
            const data = await response.json();
            console.log("[AUTH] ログアウト成功:", data.message);
            
            // 状態をリセットし、UIを更新
            isAuthenticated = false;
            updateAuthUI();
            
            // ログアウト後、ログイン画面に遷移
            showPage(LOGIN_PAGE_ID); 
            renderLoginPage();
        } else {
            console.error("[AUTH ERROR] ログアウト処理でサーバーエラー:", response.status);
            alert("ログアウトに失敗しました。サーバーエラーです。");
        }
    } catch (error) {
        // safeFetch内の401ハンドリングで既にログインページにリダイレクトされるため、ここでは主にネットワークエラーを捕捉
        if (error.message !== "Unauthenticated access detected.") {
            console.error("[AUTH ERROR] ログアウト通信エラー:", error);
        }
    }
};


// -------------------------------------------------------------------------
// ゲームロジック (UI/API連携)
// -------------------------------------------------------------------------

/**
 * オーダー決定画面のレンダリング関数
 */
const renderOrderPage = async () => {
    const batterOrderContainer = document.getElementById('batter-order-container');
    const pitcherSelectionContainer = document.getElementById('pitcher-selection-container');
    
    try {
        // 認証済みのセッションで選手データを取得
        const playersResponse = await safeFetch('/api/players');
        const teamsData = await playersResponse.json();
        
        const userTeamName = "自チーム (ベイカーズ)";
        const userTeamPlayers = teamsData[userTeamName] || [];

        const batterPlayers = userTeamPlayers.filter(p => !p.is_pitcher);
        const pitcherPlayers = userTeamPlayers.filter(p => p.is_pitcher);

        // ... 打者スタメンと投手のUI生成ロジック（選手IDを使用） ...
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
                select.appendChild(option);
            });
            batterOrderContainer.appendChild(group);
        }

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
            select.appendChild(option);
        });
        pitcherSelectionContainer.appendChild(group);

        console.log("オーダー決定画面のUIを生成しました。");

    } catch (error) {
        // 401エラーはsafeFetchが処理するため、ここでは無視
        if (error.message !== "Unauthenticated access detected.") {
            console.error("オーダーページレンダリング中にエラー:", error);
        }
    }
};

/**
 * 日程進行画面のレンダリング関数
 */
const renderSchedulePage = async () => {
    // スケジュールとランキングの表示ロジック（未実装）
    const scheduleDisplay = document.getElementById('game-schedule');
    const rankingDisplay = document.getElementById('league-ranking');
    
    scheduleDisplay.innerHTML = '<li>試合結果がここに表示されます。</li>';
    rankingDisplay.innerHTML = '<li>順位データは後で実装します。</li>';
};

/**
 * 試合をシミュレートする関数
 */
const advanceDay = async () => {
    console.log("1日進めます。試合結果を生成中...");
    const scheduleDisplay = document.getElementById('game-schedule');
    
    try {
        const response = await safeFetch('/api/simulate_game');
        const result = await response.json();

        // 試合結果を画面に追加
        const li = document.createElement('li');
        li.textContent = `${result.home_team} vs ${result.away_team} - スコア: ${result.home_score} - ${result.away_score} (${result.result})`;
        li.classList.add(result.result === '勝利' ? 'result-win' : result.result === '敗北' ? 'result-lose' : 'result-draw');
        scheduleDisplay.prepend(li); 

        console.log("試合結果を画面に反映しました。");
    } catch (error) {
        if (error.message !== "Unauthenticated access detected.") {
            console.error("試合シミュレーション中にエラーが発生しました:", error);
        }
    }
};


// -------------------------------------------------------------------------
// イベントリスナーと初期化
// -------------------------------------------------------------------------

document.addEventListener('DOMContentLoaded', () => {
    console.log("アプリのロジックがスタートしました。");
    
    // ナビゲーションボタンにイベントリスナーを設定
    document.querySelectorAll('.nav-btn').forEach(button => {
        button.addEventListener('click', (event) => {
            const targetPageId = event.target.dataset.target;
            // ログイン済みかチェックし、適切な画面へ遷移
            if (targetPageId !== LOGIN_PAGE_ID) {
                checkAuthAndShowPage(targetPageId);
            } else {
                showPage(targetPageId);
                renderLoginPage();
            }
        });
    });

    // ログアウトボタンのイベントリスナー
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', handleLogout);
    }
    
    // オーダー決定ボタンのイベントリスナー 
    const submitOrderBtn = document.getElementById('submit-order-btn');
    if (submitOrderBtn) {
        submitOrderBtn.addEventListener('click', async () => {
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
                if (!selectElement) continue;

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
            const pitcherId = pitcherSelect ? pitcherSelect.value : null;

            if (!pitcherId) {
                messageArea.textContent = '先発投手を指定してください。';
                return;
            }
            if (selectedPlayerIds.has(pitcherId)) {
                messageArea.textContent = `先発投手が打順に重複しています。`;
                return;
            }
            orderData.pitcher = parseInt(pitcherId); 
            selectedPlayerIds.add(pitcherId);

            console.log("オーダーが決定されました。Flaskアプリに送信する選手IDリスト:", orderData);
            
            // Flask APIに選手IDリストを送信
            try {
                const response = await safeFetch('/api/order', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(orderData),
                    credentials: 'include'
                });

                if (response.ok) {
                    const data = await response.json();
                    messageArea.textContent = `オーダー送信成功！ Flask応答: ${data.message}`;
                } else if (response.status !== 401) {
                    // 401以外のエラー
                    messageArea.textContent = 'オーダー送信中にサーバーエラーが発生しました。';
                }
            } catch (error) {
                 // safeFetchで401は処理済み
                if (error.message !== "Unauthenticated access detected.") {
                    messageArea.textContent = '通信エラーが発生しました。';
                    console.error('Error sending order:', error);
                }
            }
        });
    }

    // 日程進行ボタンにイベントリスナーを設定
    const advanceDayBtn = document.getElementById('advance-day-btn');
    if (advanceDayBtn) {
        advanceDayBtn.addEventListener('click', advanceDay);
    }

    // アプリケーション起動時の認証チェックと画面表示
    checkAuthAndShowPage();
});