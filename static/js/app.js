document.addEventListener('DOMContentLoaded', () => {
    console.log("アプリのロジックがスタートしました。");
    
    // ページセクションの切り替え関数
    const showPage = (pageId) => {
        console.log(`[NAV] ページを「${pageId}」に切り替えます。`); // デバッグログ
        document.querySelectorAll('.page-section').forEach(section => {
            section.classList.remove('active');
        });
        const targetElement = document.getElementById(pageId);
        if (targetElement) {
            targetElement.classList.add('active');
            console.log(`[NAV] #${pageId} に active クラスを適用しました。`); // デバッグログ
        } else {
            console.error(`[NAV ERROR] ID: ${pageId} の要素が見つかりません。`); // デバッグログ
        }
        

        // 各ページ固有の初期化ロジック
        if (pageId === 'order-page') {
            renderOrderPage();
        } else if (pageId === 'schedule-page') {
            renderSchedulePage(); // スケジュールページにも初期化ロジックを追加
        }
    };

    // オーダー決定画面のレンダリング関数
    const renderOrderPage = async () => {
        const batterOrderContainer = document.getElementById('batter-order-container');
        const pitcherSelectionContainer = document.getElementById('pitcher-selection-container');
        
        console.log("[RENDER] オーダー決定画面のレンダリング開始。");
        
        // ** (変更点) Flask APIから直接データを取得します **
        try {
            const playersResponse = await fetch('/api/players');
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
                    // valueは選手ID
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
                // valueは選手ID
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
            // ** (変更点) Flask APIから直接データを取得します **
            const response = await fetch('/api/simulate_game');
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

    // ナビゲーションボタンにイベントリスナーを設定
    document.querySelectorAll('.nav-btn').forEach(button => {
        button.addEventListener('click', (event) => {
            const targetPageId = event.target.dataset.target;
            console.log(`[EVENT] ナビボタンクリック: target=${targetPageId}`); // デバッグログ
            showPage(targetPageId);
        });
    });

    // オーダー決定ボタンのイベントリスナー 
    const submitOrderBtn = document.getElementById('submit-order-btn');
    submitOrderBtn.addEventListener('click', async () => {
        console.log("[EVENT] オーダー決定ボタンクリック。");
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
            const response = await fetch('/api/order', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(orderData)
            });
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

    // 初期表示としてホーム画面を表示
    showPage('home-page');
});