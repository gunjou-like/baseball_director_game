import json
import random
from datetime import datetime

from flask import Flask, jsonify, request, render_template, redirect, url_for
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# --- Flask & SQLAlchemy 初期設定 ---
app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app, supports_credentials=True)

# セキュリティのためのシークレットキー設定（本番環境では安全なキーを使用）
app.config['SECRET_KEY'] = 'a_very_secret_key_for_session_management_baseball'

# SQLite データベース設定
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Flask-Login の設定
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ログインが必要なエンドポイントで認証されていない場合のリダイレクト処理
@login_manager.unauthorized_handler
def unauthorized():
    # 認証されていない場合は、JSONレスポンス（401 Unauthorized）を返します。
    # フロントエンドのJavaScriptがこの401を検出してログイン画面に遷移させます。
    return jsonify({"error": "Unauthorized Access"}), 401

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# --- DBモデル定義 ---

# 選手の初期成績と能力値をランダム生成するヘルパー関数
def create_random_player_data(is_pitcher):
    if is_pitcher:
        # 投手成績: 奪三振率、与四球率、被打率
        stats = {
            "strikeout_rate": 0.0, #random.uniform(7.0, 10.0),
            "walk_rate": 0.0, #random.uniform(2.0, 4.0),
            "batting_avg_allowed": 0.0  #random.uniform(0.220, 0.280),
        }
        # 投手能力: 球威、制球、変化球
        abilities = {
            "power": random.randint(60, 90),
            "control": random.randint(60, 90),
            "breaking_ball": random.randint(60, 90),
        }
    else:
        # 野手成績: 打率、本塁打、盗塁
        stats = {
            "batting_avg": 0.000, # random.uniform(0.250, 0.320),
            "homeruns": 0, #random.randint(0, 30),
            "steals": 0, #random.randint(0, 20),
        }
        # 野手能力: ミート、パワー、スピード
        abilities = {
            "meet": random.randint(60, 90),
            "power": random.randint(60, 90),
            "speed": random.randint(60, 90),
        }
    return stats, abilities

# 初期データテンプレート
def generate_initial_teams_data():
    base_data = {
    "自チーム (blue)": [
        {"id": 1001, "name": "山田 太郎", "position": "P", "is_pitcher": True},
        {"id": 1010, "name": "小林 賢治", "position": "P", "is_pitcher": True},
        {"id": 1013, "name": "石井 直人", "position": "P", "is_pitcher": True},
        {"id": 1014, "name": "村上 翔", "position": "P", "is_pitcher": True},
        {"id": 1015, "name": "大野 智", "position": "P", "is_pitcher": True},
        {"id": 1002, "name": "田中 健太", "position": "C", "is_pitcher": False},
        {"id": 1003, "name": "鈴木 一朗", "position": "1B", "is_pitcher": False},
        {"id": 1004, "name": "佐藤 大輔", "position": "2B", "is_pitcher": False},
        {"id": 1005, "name": "高橋 誠", "position": "3B", "is_pitcher": False},
        {"id": 1006, "name": "伊藤 雄一", "position": "SS", "is_pitcher": False},
        {"id": 1007, "name": "渡辺 亮", "position": "LF", "is_pitcher": False},
        {"id": 1008, "name": "山本 剛", "position": "CF", "is_pitcher": False},
        {"id": 1009, "name": "中村 俊介", "position": "RF", "is_pitcher": False},
        {"id": 1011, "name": "加藤 拓也", "position": "C", "is_pitcher": False},
        {"id": 1012, "name": "吉田 啓介", "position": "OF", "is_pitcher": False},
        {"id": 1016, "name": "藤井 陽介", "position": "OF", "is_pitcher": False},
        {"id": 1017, "name": "三浦 健", "position": "IF", "is_pitcher": False},
    ],
    "red": [
        {"id": 2001, "name": "獅子丸", "position": "P", "is_pitcher": True},
        {"id": 2010, "name": "金田 豪", "position": "P", "is_pitcher": True},
        {"id": 2011, "name": "白井 翔太", "position": "P", "is_pitcher": True},
        {"id": 2012, "name": "黒川 直樹", "position": "P", "is_pitcher": True},
        {"id": 2013, "name": "青木 亮太", "position": "P", "is_pitcher": True},
        {"id": 2002, "name": "虎雄", "position": "C", "is_pitcher": False},
        {"id": 2003, "name": "猿吉", "position": "1B", "is_pitcher": False},
        {"id": 2014, "name": "鹿島 勇", "position": "2B", "is_pitcher": False},
        {"id": 2015, "name": "熊谷 翔", "position": "3B", "is_pitcher": False},
        {"id": 2016, "name": "猿渡 剛", "position": "SS", "is_pitcher": False},
        {"id": 2017, "name": "犬飼 健", "position": "LF", "is_pitcher": False},
        {"id": 2018, "name": "猫田 俊", "position": "CF", "is_pitcher": False},
        {"id": 2019, "name": "鳥居 光", "position": "RF", "is_pitcher": False},
        {"id": 2020, "name": "馬場 直人", "position": "OF", "is_pitcher": False},
        {"id": 2021, "name": "鯉沼 大地", "position": "IF", "is_pitcher": False},
        {"id": 2022, "name": "亀山 亮", "position": "C", "is_pitcher": False},
    ],
        "yellow": [
        {"id": 3001, "name": "鷹山", "position": "P", "is_pitcher": True},
        {"id": 3010, "name": "隼田 剛", "position": "P", "is_pitcher": True},
        {"id": 3011, "name": "鷲野 翔", "position": "P", "is_pitcher": True},
        {"id": 3012, "name": "鷹田 健", "position": "P", "is_pitcher": True},
        {"id": 3013, "name": "鷲崎 大地", "position": "P", "is_pitcher": True},
        {"id": 3002, "name": "隼人", "position": "C", "is_pitcher": False},
        {"id": 3003, "name": "鷲尾", "position": "1B", "is_pitcher": False},
        {"id": 3014, "name": "鷹川 翔太", "position": "2B", "is_pitcher": False},
        {"id": 3015, "name": "隼谷 亮", "position": "3B", "is_pitcher": False},
        {"id": 3016, "name": "鷲村 健太", "position": "SS", "is_pitcher": False},
        {"id": 3017, "name": "鷹井 剛", "position": "LF", "is_pitcher": False},
        {"id": 3018, "name": "隼島 大輔", "position": "CF", "is_pitcher": False},
        {"id": 3019, "name": "鷲田 陽介", "position": "RF", "is_pitcher": False},
        {"id": 3020, "name": "鷹本 拓也", "position": "OF", "is_pitcher": False},
        {"id": 3021, "name": "隼川 啓介", "position": "IF", "is_pitcher": False},
        {"id": 3022, "name": "鷲山 賢治", "position": "C", "is_pitcher": False},
    ],
    "brown": [
        {"id": 4001, "name": "虎谷 剛", "position": "P", "is_pitcher": True},
        {"id": 4010, "name": "虎島 健", "position": "P", "is_pitcher": True},
        {"id": 4011, "name": "虎野 翔太", "position": "P", "is_pitcher": True},
        {"id": 4012, "name": "虎田 陽介", "position": "P", "is_pitcher": True},
        {"id": 4013, "name": "虎井 大地", "position": "P", "is_pitcher": True},
        {"id": 4002, "name": "虎丸", "position": "C", "is_pitcher": False},
        {"id": 4003, "name": "虎吉", "position": "1B", "is_pitcher": False},
        {"id": 4014, "name": "虎川 健太", "position": "2B", "is_pitcher": False},
        {"id": 4015, "name": "虎村 拓也", "position": "3B", "is_pitcher": False},
        {"id": 4016, "name": "虎山 賢治", "position": "SS", "is_pitcher": False},
        {"id": 4017, "name": "虎本 大輔", "position": "LF", "is_pitcher": False},
        {"id": 4018, "name": "虎島 陽介", "position": "CF", "is_pitcher": False},
        {"id": 4019, "name": "虎田 剛", "position": "RF", "is_pitcher": False},
        {"id": 4020, "name": "虎井 健", "position": "OF", "is_pitcher": False},
        {"id": 4021, "name": "虎川 翔", "position": "IF", "is_pitcher": False},
        {"id": 4022, "name": "虎山 啓介", "position": "C", "is_pitcher": False},
    ],
    "black": [
        {"id": 5001, "name": "竜崎 剛", "position": "P", "is_pitcher": True},
        {"id": 5010, "name": "竜田 健", "position": "P", "is_pitcher": True},
        {"id": 5011, "name": "竜野 翔太", "position": "P", "is_pitcher": True},
        {"id": 5012, "name": "竜井 陽介", "position": "P", "is_pitcher": True},
        {"id": 5013, "name": "竜川 大地", "position": "P", "is_pitcher": True},
        {"id": 5002, "name": "竜丸", "position": "C", "is_pitcher": False},
        {"id": 5003, "name": "竜吉", "position": "1B", "is_pitcher": False},
        {"id": 5014, "name": "竜村 健太", "position": "2B", "is_pitcher": False},
        {"id": 5015, "name": "竜山 拓也", "position": "3B", "is_pitcher": False},
        {"id": 5016, "name": "竜本 賢治", "position": "SS", "is_pitcher": False},
        {"id": 5017, "name": "竜島 大輔", "position": "LF", "is_pitcher": False},
        {"id": 5018, "name": "竜田 陽介", "position": "CF", "is_pitcher": False},
        {"id": 5019, "name": "竜井 剛", "position": "RF", "is_pitcher": False},
        {"id": 5020, "name": "竜川 健", "position": "OF", "is_pitcher": False},
        {"id": 5021, "name": "竜山 翔", "position": "IF", "is_pitcher": False},
        {"id": 5022, "name": "竜本 啓介", "position": "C", "is_pitcher": False},
    ],
    "green": [
        {"id": 6001, "name": "燕谷 剛", "position": "P", "is_pitcher": True},
        {"id": 6010, "name": "燕田 健", "position": "P", "is_pitcher": True},
        {"id": 6011, "name": "燕野 翔太", "position": "P", "is_pitcher": True},
        {"id": 6012, "name": "燕井 陽介", "position": "P", "is_pitcher": True},
        {"id": 6013, "name": "燕川 大地", "position": "P", "is_pitcher": True},
        {"id": 6002, "name": "燕丸", "position": "C", "is_pitcher": False},
        {"id": 6003, "name": "燕吉", "position": "1B", "is_pitcher": False},
        {"id": 6014, "name": "燕村 健太", "position": "2B", "is_pitcher": False},
        {"id": 6015, "name": "燕山 拓也", "position": "3B", "is_pitcher": False},
        {"id": 6016, "name": "燕本 賢治", "position": "SS", "is_pitcher": False},
        {"id": 6017, "name": "燕島 大輔", "position": "LF", "is_pitcher": False},
        {"id": 6018, "name": "燕田 陽介", "position": "CF", "is_pitcher": False},
        {"id": 6019, "name": "燕井 剛", "position": "RF", "is_pitcher": False},
        {"id": 6020, "name": "燕川 健", "position": "OF", "is_pitcher": False}
    ]
    }

    # 各チームの各選手に成績と能力を付与
    teams_data_with_stats = {}
    for team_name, players in base_data.items():
        teams_data_with_stats[team_name] = []
        for player in players:
            stats, abilities = create_random_player_data(player['is_pitcher'])
            player['stats'] = stats
            player['abilities'] = abilities
            teams_data_with_stats[team_name].append(player)
            
    return teams_data_with_stats


# ユーザー認証情報テーブル
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    
    # ユーザーの状態（ゲームデータ）と1対1で関連付け
    user_state = db.relationship('UserState', backref='manager', uselist=False, lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# ユーザーごとのゲーム状態（セーブデータ）テーブル
class UserState(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    
    # JSON文字列として保存するフィールド
    teams_json = db.Column(db.Text, nullable=False) # 全チームの選手データ（成績と能力を含む）
    schedule_json = db.Column(db.Text, nullable=False) # 試合履歴のリスト
    current_order_json = db.Column(db.Text, nullable=False) # 現在のオーダー（選手IDリスト）
    
    # 初期データを生成するクラスメソッド
    @classmethod
    def create_initial_state(cls, user_id):
        initial_teams_data = generate_initial_teams_data()
        initial_order = {"batters": [], "pitcher": None}

        return cls(
            user_id=user_id,
            teams_json=json.dumps(initial_teams_data),
            schedule_json=json.dumps([]),
            current_order_json=json.dumps(initial_order)
        )

# --- データベースの初期化 ---
with app.app_context():
    db.create_all()

    # デバッグ用の初期ユーザーを作成
    if not User.query.filter_by(username='testuser').first():
        test_user = User(username='testuser')
        test_user.set_password('password')
        db.session.add(test_user)
        db.session.commit()
        # ユーザー状態も初期化
        initial_state = UserState.create_initial_state(test_user.id)
        db.session.add(initial_state)
        db.session.commit()
        print("Initial user 'testuser' created.")

# --- ルーティング ---

# SPAのエントリーポイント
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def index(path):
    return render_template('index.html')

# ログインエンドポイント
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        login_user(user)
        print(f"User {username} logged in successfully.")
        return jsonify({"message": "Login successful"}), 200
    
    return jsonify({"error": "Invalid username or password"}), 401

# ログアウトエンドポイント
@app.route('/logout', methods=['GET'])
@login_required
def logout():
    logout_user()
    return jsonify({"success": True, "message": "Logout successful"}), 200

# ユーザーごとのゲーム状態を取得するエンドポイント（認証必須）
@app.route('/api/game_state', methods=['GET'])
@login_required
def get_game_state():
    # ユーザーのゲーム状態を取得。存在しない場合は自動的に初期化される
    user_state = current_user.user_state
    if user_state is None:
        user_state = UserState.create_initial_state(current_user.id)
        db.session.add(user_state)
        db.session.commit()

    # DBからJSONデータをロードして結合し、フロントエンドに返す
    return jsonify({
        "teams": json.loads(user_state.teams_json),
        "schedule": json.loads(user_state.schedule_json),
        "current_order": json.loads(user_state.current_order_json),
    }), 200


# オーダー情報を受け取り、DBに保存するエンドポイント（認証必須）
@app.route('/api/order', methods=['POST'])
@login_required
def receive_order():
    order_data = request.json
    
    user_state = current_user.user_state
    if user_state is None:
        return jsonify({"error": "User state not initialized"}), 500

    # current_order_jsonを更新
    user_state.current_order_json = json.dumps(order_data)
    db.session.commit()

    return jsonify({"message": "Order saved successfully!"}), 200


# ランダムな試合結果を生成し、DBに保存するエンドポイント（認証必須）
@app.route('/api/simulate_game', methods=['GET'])
@login_required
def simulate_game():
    user_state = current_user.user_state
    if user_state is None:
        return jsonify({"error": "User state not initialized"}), 500

    # 1. 試合結果をランダム生成
    home_score = random.randint(0, 10)
    away_score = random.randint(0, 10)
    
    user_team = "自チーム (blue)"
    # チームデータをロードし、対戦相手をランダム選択
    teams_data = json.loads(user_state.teams_json)
    opponent_teams = [t for t in teams_data.keys() if t != user_team]
    opponent_team = random.choice(opponent_teams)
    
    result_text = "勝利" if home_score > away_score else "敗北" if home_score < away_score else "引き分け"

    game_result = {
        "home_team": user_team,
        "away_team": opponent_team,
        "home_score": home_score,
        "away_score": away_score,
        "result": result_text,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # 2. 試合結果をスケジュールに追加
    schedule = json.loads(user_state.schedule_json)
    schedule.append(game_result)
    user_state.schedule_json = json.dumps(schedule)
    
    # TODO: 3. 成績データを更新するロジックをここに追加
    # teams_dataを更新し、user_state.teams_jsonを上書きする
    # 例: 山田太郎の打率を少し変動させるなど

    # 4. DBコミット
    db.session.commit()

    return jsonify({"message": "Game simulated and state saved."}), 200

if __name__ == '__main__':
    # 開発環境でのみポート5000を使用
    app.run(debug=True, port=5000)