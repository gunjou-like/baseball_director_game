import json
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship # relationshipをインポート
from werkzeug.security import generate_password_hash, check_password_hash
import random

app = Flask(__name__, static_folder='static', template_folder='templates')
# 秘密鍵を設定 (セッション管理に必須)
app.config['SECRET_KEY'] = 'your_super_secret_key_that_should_be_long_and_random'
# SQLiteデータベースの設定
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# CORS設定を強化し、すべてのリソースで認証情報と全メソッドを許可する
CORS(app, supports_credentials=True, resources={r"/*": {"origins": "*"}}) 

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login' 

# ----------------- DBモデル -----------------

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    
    # UserStateとの一対一のリレーションシップ
    state = relationship("UserState", back_populates="user", uselist=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# ★新規追加: ユーザーごとのゲームデータを保存するモデル
class UserState(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=False)
    
    # 試合履歴 (JSON文字列として保存)
    schedule_json = db.Column(db.Text, default=json.dumps([]))
    
    # 現在のオーダー情報 (JSON文字列として保存)
    current_order_json = db.Column(db.Text, default=json.dumps({"batters": [], "pitcher": None}))

    # Userモデルへの逆参照
    user = relationship("User", back_populates="state")

    # JSONデータをPythonオブジェクトとして扱うためのプロパティ
    @property
    def schedule(self):
        return json.loads(self.schedule_json)
    
    @schedule.setter
    def schedule(self, value):
        self.schedule_json = json.dumps(value)

    @property
    def current_order(self):
        return json.loads(self.current_order_json)
    
    @current_order.setter
    def current_order(self, value):
        self.current_order_json = json.dumps(value)

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

# ----------------- データ (グローバルな選手リスト) -----------------

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

# ログイン処理API
@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    user = db.session.execute(db.select(User).filter_by(username=username)).scalar_one_or_none()
    
    if user and user.check_password(password):
        login_user(user)
        return jsonify({"message": "Login successful"}), 200
    
    return jsonify({"error": "Invalid credentials"}), 401

# ログアウト処理API
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

# ----------------- ゲームAPI (認証必須 & データ永続化) -----------------

# 選手リストを取得し、ゲーム状態を初期化/取得するエンドポイント
@app.route('/api/game_state', methods=['GET', 'HEAD']) 
@login_required
def get_game_state():
    # ユーザーのゲーム状態を取得
    user_state = db.session.execute(db.select(UserState).filter_by(user_id=current_user.id)).scalar_one_or_none()
    
    if user_state is None:
        # データがない場合、初期データを作成
        user_state = UserState(user_id=current_user.id)
        db.session.add(user_state)
        db.session.commit()
        print(f"UserState created for user: {current_user.username}")
    
    # HEADリクエストの場合は認証ステータスのみ応答
    if request.method == 'HEAD':
        return '', 200 
    
    # GETリクエストの場合はグローバルデータとユーザーデータを結合して返す
    game_state = {
        "teams": TEAMS_DATA, # グローバルな選手データ
        "schedule": user_state.schedule, # ユーザーの試合履歴
        "current_order": user_state.current_order, # ユーザーの現在のオーダー
    }
    
    return jsonify(game_state)

# オーダー情報を受け取り、DBに保存するAPIエンドポイント
@app.route('/api/order', methods=['POST'])
@login_required
def update_order():
    order_data = request.json
    
    user_state = db.session.execute(db.select(UserState).filter_by(user_id=current_user.id)).scalar_one_or_none()
    if not user_state:
        return jsonify({"error": "UserState not found. Please reload."}), 500

    # UserStateのcurrent_orderフィールドを更新
    user_state.current_order = order_data
    db.session.commit()

    print(f"User {current_user.username}: Order saved successfully.")
    return jsonify({"message": "Order saved successfully."}), 200

# ランダムな試合結果を生成し、DBに保存するAPIエンドポイント
@app.route('/api/simulate_game', methods=['GET'])
@login_required
def simulate_game():
    user_state = db.session.execute(db.select(UserState).filter_by(user_id=current_user.id)).scalar_one_or_none()
    if not user_state:
        return jsonify({"error": "UserState not found. Please reload."}), 500
        
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
    
    # 試合結果をUserStateのscheduleに追加して保存
    current_schedule = user_state.schedule
    current_schedule.append(game_result)
    user_state.schedule = current_schedule # Setterプロパティを通じてJSONに変換し保存
    db.session.commit()

    return jsonify(game_result)

if __name__ == '__main__':
    # 開発環境特有の問題に対処するため、debug=Falseを推奨
    # ただし、開発中は利便性のためdebug=Trueのままにしておきます
    app.run(debug=True, port=5000)
