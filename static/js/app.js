document.addEventListener('DOMContentLoaded', () => {
    // ページセクションの切り替え関数
    const showPage = (pageId) => {
        document.querySelectorAll('.page-section').forEach(section => {
            section.classList.remove('active');
        });
        document.getElementById(pageId).classList.add('active');

        // 各ページ固有の初期化ロジック
        if (pageId === 'order-page') {
            renderOrderPage();
        }
    };

    // オーダー決定画面のレンダリング関数
    const renderOrderPage = async () => {
        const batterOrderContainer = document.getElementById('batter-order-container');
        const pitcherSelectionContainer = document.getElementById('pitcher-selection-container');
        
        // 選手データを取得
        const playersResponse = await fetch('/api/players');
        const players = await playersResponse.json();

        const batterPlayers = Object.values(players).filter(p => !p.is_pitcher);
        const pitcherPlayers = Object.values(players).filter(p => p.is_pitcher);

        // 打者スタメンのUIを動的に生成
        batterOrderContainer.innerHTML = ''; // コンテナをクリア
        for (let i = 1; i <= 9; i++) {
            const group = document.createElement('div');
            group.classList.add('player-select-group');
            group.innerHTML = `<label for="batter-${i}">${i}番</label><select id="batter-${i}"></select>`;
            
            const select = group.querySelector('select');
            select.innerHTML = '<option value="">選手を選択</option>';
            batterPlayers.forEach(player => {
                const option = document.createElement('option');
                option.value = player.name;
                option.textContent = player.name;
                select.appendChild(option);
            });
            batterOrderContainer.appendChild(group);
        }

        // 先発投手のUIを動的に生成
        pitcherSelectionContainer.innerHTML = ''; // コンテナをクリア
        const group = document.createElement('div');
        group.classList.add('player-select-group');
        group.innerHTML = `<label for="pitcher">先発</label><select id="pitcher"></select>`;
        
        const select = group.querySelector('select');
        select.innerHTML = '<option value="">選手を選択</option>';
        pitcherPlayers.forEach(player => {
            const option = document.createElement('option');
            option.value = player.name;
            option.textContent = player.name;
            select.appendChild(option);
        });
        pitcherSelectionContainer.appendChild(group);

        console.log("オーダー決定画面のUIを生成しました。");
    };

    // ナビゲーションボタンにイベントリスナーを設定
    document.querySelectorAll('.nav-btn').forEach(button => {
        button.addEventListener('click', (event) => {
            const targetPageId = event.target.dataset.target;
            showPage(targetPageId);
        });
    });

    // オーダー決定ボタンのイベントリスナー
    const submitOrderBtn = document.getElementById('submit-order-btn');
    submitOrderBtn.addEventListener('click', () => {
        const orderData = {
            batters: [],
            pitcher: ''
        };

        let hasError = false;
        const selectedPlayers = new Set();
        
        // 打者オーダーを取得
        for (let i = 1; i <= 9; i++) {
            const selectElement = document.getElementById(`batter-${i}`);
            const playerName = selectElement.value;

            if (!playerName) {
                alert(`${i}番の選手を選択してください。`);
                hasError = true;
                break;
            }
            if (selectedPlayers.has(playerName)) {
                alert(`打順に同じ選手が重複しています: ${playerName}`);
                hasError = true;
                break;
            }
            selectedPlayers.add(playerName);
            orderData.batters.push(playerName);
        }
        
        if (hasError) return;

        // 先発投手を設定
        const pitcherSelect = document.getElementById('pitcher');
        const pitcherName = pitcherSelect.value;
        if (!pitcherName) {
            alert('先発投手を指定してください。');
            return;
        }
        if (selectedPlayers.has(pitcherName)) {
            alert(`打順に選ばれた選手は先発投手になれません: ${pitcherName}`);
            return;
        }
        orderData.pitcher = pitcherName;

        console.log("オーダーが決定されました。Flaskアプリに送信します...", orderData);
        // TODO: FlaskへのAPIリクエストを実装
        // fetch('/api/order', {
        //     method: 'POST',
        //     headers: { 'Content-Type': 'application/json' },
        //     body: JSON.stringify(orderData)
        // })
        // .then(response => response.json())
        // .then(data => console.log(data));
    });

    // 日程進行画面
    const advanceDayBtn = document.getElementById('advance-day-btn');
    advanceDayBtn.addEventListener('click', () => {
        console.log("1日進めます。Flaskアプリに試合結果を生成させます...");
        // TODO: FlaskへのAPIリクエストを実装
    });

    // 初期表示としてホーム画面を表示
    showPage('home-page');
});
