import json
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import random

app = Flask(__name__, static_folder='static', template_folder='templates')
# 秘密鍵を設定 (セッション管理に必須)
app.config['SECRET_KEY'] = 'your_super_secret_key_that_should_be_long_and_random'
# SQLiteデータベースの設定
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app, supports_credentials=True) # 認証情報 (クッキー) の送受信を許可

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
# login_viewを設定することで、@login_requiredで保護された関数に未認証でアクセスした際のリダイレクト先を指定
login_manager.login_view = 'login' 

# ----------------- DBモデル -----------------

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# データベースと初期ユーザーの作成
with app.app_context():
    db.create_all()
    # テストユーザーがいない場合のみ作成
    if not db.session.execute(db.select(User).filter_by(username='testuser')).first():
        test_user = User(username='testuser')
        test_user.set_password('password')
        db.session.add(test_user)
        db.session.commit()
        print("Test user created: username='testuser', password='password'")

# ----------------- データ -----------------

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

# ----------------- ルーティング -----------------

# SPAのエントリーポイント
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def index(path):
    return render_template('index.html')

# ログイン処理API (重複なし)
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    user = db.session.execute(db.select(User).filter_by(username=username)).scalar_one_or_none()
    
    if user and user.check_password(password):
        login_user(user)
        # フロントエンドへの応答にはユーザーIDなどの機密情報を含めない
        return jsonify({"message": "Login successful"}), 200
    
    return jsonify({"error": "Invalid credentials"}), 401

# ログアウト処理API (重複なし)
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logout successful"}), 200

# ユーザー情報API (認証テスト用)
@app.route('/user_info', methods=['GET'])
@login_required
def user_info():
    return jsonify({"username": current_user.username, "id": current_user.id}), 200

# ----------------- ゲームAPI (認証必須) -----------------

# 選手リストを取得するAPIエンドポイント
@app.route('/api/players', methods=['GET'])
@login_required
def get_players():
    # 認証済みの場合のみデータを返す
    return jsonify(TEAMS_DATA)

# オーダー情報を受け取るAPIエンドポイント
@app.route('/api/order', methods=['POST'])
@login_required
def receive_order():
    order_data = request.json
    print(f"User {current_user.username} received order data (Player IDs):", json.dumps(order_data, indent=2))
    return jsonify({"message": "Order received successfully!", "received_ids": order_data}), 200

# ランダムな試合結果を生成するAPIエンドポイント
@app.route('/api/simulate_game', methods=['GET'])
@login_required
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
    app.run(debug=True, port=5000)