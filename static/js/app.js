document.addEventListener('DOMContentLoaded', () => {
    console.log("アプリのロジックがスタートしました。");
    
    // 認証状態を管理するフラグ
    let isAuthenticated = false; 

    // ログイン画面のID
    const LOGIN_PAGE_ID = 'login-page';

    // -------------------------------------------------------------------------
    // ユーティリティ関数
    // -------------------------------------------------------------------------

    // 認証エラーをチェックし、ログインページへリダイレクトする fetch ラッパー
    const safeFetch = async (url, options = {}) => {
        const response = await fetch(url, options);
        if (response.status === 401) {
            console.warn("[AUTH] 401 Unauthenticated: ログインページへリダイレクトします。");
            isAuthenticated = false;
            // ログインページへの遷移を強制
            showPage(LOGIN_PAGE_ID);
            return null;
        }
        if (!response.ok) {
            throw new Error(`HTTP Error! Status: ${response.status}`);
        }
        return response;
    };

    // 認証状態をチェックし、適切なページを表示する関数
    const checkAuthAndShowPage = (pageId) => {
        if (!isAuthenticated && pageId !== LOGIN_PAGE_ID) {
            console.log("[AUTH] 認証が必要です。ログインページを表示します。");
            showPage(LOGIN_PAGE_ID);
        } else {
            showPage(pageId);
        }
    };

    // -------------------------------------------------------------------------
    // ページ遷移/レンダリングロジック
    // -------------------------------------------------------------------------

    // ページセクションの切り替え関数 (内部使用)
    const showPage = (pageId) => {
        console.log(`[NAV] ページを「${pageId}」に切り替えます。`); 
        document.querySelectorAll('.page-section').forEach(section => {
            section.classList.remove('active');
        });
        const targetElement = document.getElementById(pageId);
        if (targetElement) {
            targetElement.classList.add('active');
            console.log(`[NAV] #${pageId} に active クラスを適用しました。`); 
        } else {
            console.error(`[NAV ERROR] ID: ${pageId} の要素が見つかりません。`); 
        }
        
        // 各ページ固有の初期化ロジック
        if (pageId === 'order-page') {
            renderOrderPage();
        } else if (pageId === 'schedule-page') {
            renderSchedulePage(); 
        } else if (pageId === LOGIN_PAGE_ID) {
            renderLoginPage();
        }
    };

    // ログイン画面のレンダリングとイベント設定
    const renderLoginPage = () => {
        const loginMessage = document.getElementById('login-message');
        const loginForm = document.getElementById('login-form');
        
        // フォームがない場合は、HTMLが未定義
        if (!loginForm) return;

        loginMessage.textContent = 'ユーザー名とパスワードを入力してください (テストユーザー: testuser/password)';

        loginForm.onsubmit = async (event) => {
            event.preventDefault();
            const username = loginForm.username.value;
            const password = loginForm.password.value;
            loginMessage.textContent = 'ログイン中...';

            try {
                const response = await fetch('/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password })
                });

                const data = await response.json();

                if (response.ok) {
                    isAuthenticated = true;
                    loginMessage.textContent = `ログイン成功: User ID ${data.user_id}`;
                    console.log("[AUTH] ログイン成功。ホーム画面へ遷移します。");
                    // ログイン成功後、ホーム画面へ強制的に遷移
                    checkAuthAndShowPage('home-page'); 
                } else {
                    loginMessage.textContent = `ログイン失敗: ${data.message}`;
                    console.error("[AUTH] ログイン失敗:", data.message);
                }
            } catch (error) {
                loginMessage.textContent = 'サーバーとの通信エラーが発生しました。';
                console.error('[AUTH ERROR] ログイン通信エラー:', error);
            }
        };
    };

    // オーダー決定画面のレンダリング関数
    const renderOrderPage = async () => {
        const batterOrderContainer = document.getElementById('batter-order-container');
        const pitcherSelectionContainer = document.getElementById('pitcher-selection-container');
        
        console.log("[RENDER] オーダー決定画面のレンダリング開始。");
        
        try {
            // safeFetchを使用
            const playersResponse = await safeFetch('/api/players');
            if (!playersResponse) return; // 認証失敗時はここで処理終了
            
            const teamsData = await playersResponse.json();
            
            const userTeamName = "自チーム (ベイカーズ)";
            const userTeamPlayers = teamsData[userTeamName] || [];

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
                select.appendChild(option);
            });
            pitcherSelectionContainer.appendChild(group);

            console.log("[RENDER] オーダー決定画面のUI生成が完了しました。");
        } catch (error) {
            console.error("[RENDER ERROR] 選手データの取得または描画中にエラー:", error);
            batterOrderContainer.innerHTML = '選手データのロードに失敗しました。';
            pitcherSelectionContainer.innerHTML = '';
        }
    };

    // 日程進行画面のレンダリング関数
    const renderSchedulePage = async () => {
        console.log("[RENDER] 日程進行画面のレンダリング開始。");
        const scheduleDisplay = document.getElementById('game-schedule');
        const rankingDisplay = document.getElementById('league-ranking');
        
        // スケジュールとランキングの表示ロジック（未実装）
        scheduleDisplay.innerHTML = '<li>試合結果がここに表示されます。</li>';
        rankingDisplay.innerHTML = '<li>順位データは後で実装します。</li>';
    };

    // 試合をシミュレートする関数
    const advanceDay = async () => {
        console.log("[ACTION] 1日進めます。試合結果を生成中...");
        const scheduleDisplay = document.getElementById('game-schedule');
        
        try {
            // safeFetchを使用
            const response = await safeFetch('/api/simulate_game');
            if (!response) return; // 認証失敗時はここで処理終了

            const result = await response.json();

            // 試合結果を画面に追加
            const li = document.createElement('li');
            li.textContent = `${result.home_team} vs ${result.away_team} - スコア: ${result.home_score} - ${result.away_score} (${result.result})`;
            li.classList.add(result.result === '勝利' ? 'result-win' : result.result === '敗北' ? 'result-lose' : 'result-draw');
            scheduleDisplay.prepend(li); 

            console.log("[ACTION] 試合結果を画面に反映しました。");
        } catch (error) {
            console.error("[ACTION ERROR] 試合結果の取得中にエラーが発生しました:", error);
        }
    };

    // -------------------------------------------------------------------------
    // イベントリスナー
    // -------------------------------------------------------------------------

    // ナビゲーションボタンにイベントリスナーを設定
    document.querySelectorAll('.nav-btn').forEach(button => {
        button.addEventListener('click', (event) => {
            const targetPageId = event.target.dataset.target;
            console.log(`[EVENT] ナビボタンクリック: target=${targetPageId}`); 
            checkAuthAndShowPage(targetPageId); // 認証チェックを追加
        });
    });

    // オーダー決定ボタンのイベントリスナー 
    const submitOrderBtn = document.getElementById('submit-order-btn');
    submitOrderBtn.addEventListener('click', async () => {
        console.log("[EVENT] オーダー決定ボタンクリック。");
        if (!isAuthenticated) {
            alert('ログインが必要です。');
            return;
        }

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
        selectedPlayerIds.add(pitcherId);

        console.log("[API CALL] Flaskアプリに送信する選手IDリスト:", orderData);
        
        // Flask APIに選手IDリストを送信
        try {
            const response = await safeFetch('/api/order', { // safeFetchを使用
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(orderData)
            });

            if (!response) return; // 認証失敗時はここで処理終了
            
            const data = await response.json();
            messageArea.textContent = `オーダー送信成功！ Flask応答: ${data.message}`;
            console.log("[API SUCCESS] オーダー送信完了。");
        } catch (error) {
            messageArea.textContent = 'オーダー送信中にエラーが発生しました。';
            console.error('[API ERROR] Error sending order:', error);
        }
    });

    // 日程進行ボタンにイベントリスナーを設定
    const advanceDayBtn = document.getElementById('advance-day-btn');
    advanceDayBtn.addEventListener('click', advanceDay);

    // 初期表示: まず認証状態を確認し、ホームまたはログイン画面へ
    checkAuthAndShowPage('home-page'); 
});