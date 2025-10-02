import json
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
import random

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# チームごとの選手データ（一意の選手IDを付与）
TEAMS_DATA = {
    "自チーム (ベイカーズ)": [
        {"id": 1001, "name": "山田 太郎", "position": "P", "is_pitcher": True},
        {"id": 1002, "name": "田中 健太", "position": "C", "is_pitcher": False},
        {"id": 1003, "name": "鈴木 一朗", "position": "1B", "is_pitcher": False},
        {"id": 1004, "name": "佐藤 大輔", "position": "2B", "is_pitcher": False},
        {"id": 1005, "name": "高橋 誠", "position": "3B", "is_pitcher": False},
        {"id": 1006, "name": "伊藤 雄一", "position": "SS", "is_pitcher": False},
        {"id": 1007, "name": "渡辺 亮", "position": "LF", "is_pitcher": False},
        {"id": 1008, "name": "山本 剛", "position": "CF", "is_pitcher": False},
        {"id": 1009, "name": "中村 俊介", "position": "RF", "is_pitcher": False},
        {"id": 1010, "name": "小林 賢治", "position": "P", "is_pitcher": True},
        {"id": 1011, "name": "加藤 拓也", "position": "C", "is_pitcher": False},
        {"id": 1012, "name": "吉田 啓介", "position": "OF", "is_pitcher": False},
    ],
    "ライオンズ": [
        {"id": 2001, "name": "獅子丸", "position": "P", "is_pitcher": True},
        {"id": 2002, "name": "虎雄", "position": "C", "is_pitcher": False},
        {"id": 2003, "name": "猿吉", "position": "1B", "is_pitcher": False},
    ],
    "ホークス": [
        {"id": 3001, "name": "鷹山", "position": "P", "is_pitcher": True},
        {"id": 3002, "name": "隼人", "position": "C", "is_pitcher": False},
        {"id": 3003, "name": "鷲尾", "position": "1B", "is_pitcher": False},
    ],
    "イーグルス": [
        {"id": 4001, "name": "鷲巣", "position": "P", "is_pitcher": True},
        {"id": 4002, "name": "隼人", "position": "C", "is_pitcher": False},
        {"id": 4003, "name": "孔明", "position": "1B", "is_pitcher": False},
    ],
    "ファイターズ": [
        {"id": 5001, "name": "闘士", "position": "P", "is_pitcher": True},
        {"id": 5002, "name": "拓也", "position": "C", "is_pitcher": False},
        {"id": 5003, "name": "健太", "position": "1B", "is_pitcher": False},
    ],
    "バファローズ": [
        {"id": 6001, "name": "猛牛", "position": "P", "is_pitcher": True},
        {"id": 6002, "name": "角田", "position": "C", "is_pitcher": False},
        {"id": 6003, "name": "強太", "position": "1B", "is_pitcher": False},
    ],
}

# SPAのエントリーポイントを提供する
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def index(path):
    return render_template('index.html')

# 選手リストを取得するAPIエンドポイント
@app.route('/api/players', methods=['GET'])
def get_players():
    # 全チームの選手リストを返す
    return jsonify(TEAMS_DATA)

# オーダー情報を受け取るAPIエンドポイント
@app.route('/api/order', methods=['POST'])
def receive_order():
    order_data = request.json
    print("Received order data (Player IDs):", json.dumps(order_data, indent=2))
    return jsonify({"message": "Order received successfully!", "received_ids": order_data}), 200

# ランダムな試合結果を生成するAPIエンドポイント
@app.route('/api/simulate_game', methods=['GET'])
def simulate_game():
    home_score = random.randint(0, 10)
    away_score = random.randint(0, 10)
    
    user_team = "自チーム (ベイカーズ)"
    opponent_teams = [t for t in TEAMS_DATA.keys() if t != user_team]
    opponent_team = random.choice(opponent_teams)
    
    result = "勝利" if home_score > away_score else "敗北" if home_score < away_score else "引き分け"

    game_result = {
        "home_team": user_team,
        "away_team": opponent_team,
        "home_score": home_score,
        "away_score": away_score,
        "result": result
    }

    return jsonify(game_result)

if __name__ == '__main__':
    app.run(debug=True)