import json
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# ダミーの選手データ
# 選手IDをキーとし、名前とポジションを持つ
players_data = {
    1: {"name": "山田 太郎", "position": "P", "is_pitcher": True},
    2: {"name": "田中 健太", "position": "C", "is_pitcher": False},
    3: {"name": "鈴木 一朗", "position": "1B", "is_pitcher": False},
    4: {"name": "佐藤 大輔", "position": "2B", "is_pitcher": False},
    5: {"name": "高橋 誠", "position": "3B", "is_pitcher": False},
    6: {"name": "伊藤 雄一", "position": "SS", "is_pitcher": False},
    7: {"name": "渡辺 亮", "position": "LF", "is_pitcher": False},
    8: {"name": "山本 剛", "position": "CF", "is_pitcher": False},
    9: {"name": "中村 俊介", "position": "RF", "is_pitcher": False},
    10: {"name": "小林 賢治", "position": "P", "is_pitcher": True},
    11: {"name": "加藤 拓也", "position": "C", "is_pitcher": False},
    12: {"name": "吉田 啓介", "position": "OF", "is_pitcher": False},
}

# SPAのエントリーポイントを提供する
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def index(path):
    return render_template('index.html')

# 選手リストを取得するAPIエンドポイント
@app.route('/api/players', methods=['GET'])
def get_players():
    return jsonify(players_data)

# オーダー情報を受け取るAPIエンドポイント
@app.route('/api/order', methods=['POST'])
def receive_order():
    order_data = request.json
    print("Received order data:", json.dumps(order_data, indent=2))
    # ここでオーダーデータを処理し、試合結果を生成するロジックを実装
    return jsonify({"message": "Order received successfully!"}), 200

if __name__ == '__main__':
    app.run(debug=True)