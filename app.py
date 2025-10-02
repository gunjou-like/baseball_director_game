import json
from flask import Flask, jsonify, request, render_template, redirect, url_for, flash
from flask_cors import CORS
import random
import os
from secrets import token_hex

# 認証とDB関連のインポート
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash

# --- Flask アプリのセットアップ ---
app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# SQLite データベース設定
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'users.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# セッションとセキュリティのための秘密鍵
app.config['SECRET_KEY'] = token_hex(16) 

db = SQLAlchemy(app)

# --- Flask-Login のセットアップ ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'  # 未認証ユーザーをリダイレクトするビュー
login_manager.login_message = 'ログインが必要です。'

# --- ユーザーモデル ---
class User(UserMixin, db.Model):
    # RDBのカラムに相当
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    """セッションからユーザーIDをロードする"""
    return db.session.get(User, int(user_id))

# --- データベースの初期化 ---
with app.app_context():
    db.create_all()
    # テストユーザーがいない場合、デフォルトユーザーを作成
    if not db.session.execute(db.select(User)).scalars().first():
        test_user = User(username='testuser')
        test_user.set_password('password')
        db.session.add(test_user)
        db.session.commit()
        print("Default user 'testuser' created with password 'password'")


# --- 選手データ（認証後も利用） ---
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
    # ... 他チームのデータは省略 ...
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


# --- 認証エンドポイント ---

@app.route('/register', methods=['POST'])
def register():
    """新規ユーザー登録エンドポイント"""
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"message": "ユーザー名とパスワードが必要です"}), 400
    
    if db.session.execute(db.select(User).filter_by(username=username)).scalars().first():
        return jsonify({"message": "このユーザー名は既に使用されています"}), 409

    user = User(username=username)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    
    return jsonify({"message": f"ユーザー {username} が正常に登録されました"}), 201


@app.route('/login', methods=['POST'])
def login():
    """ログイン処理エンドポイント"""
    data = request.json
    username = data.get('username')
    password = data.get('password')

    user = db.session.execute(db.select(User).filter_by(username=username)).scalars().first()

    if user and user.check_password(password):
        login_user(user)
        # ログイン成功時は、成功メッセージとユーザーIDを返す
        return jsonify({"message": "ログイン成功", "user_id": user.id}), 200
    
    # ログイン失敗時は、エラーメッセージを返す
    return jsonify({"message": "無効なユーザー名またはパスワードです"}), 401


@app.route('/logout')
@login_required
def logout():
    """ログアウト処理エンドポイント"""
    logout_user()
    return jsonify({"message": "ログアウトしました"}), 200


# --- メインアプリケーションルート ---

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def index(path):
    """SPAのエントリーポイントを提供"""
    # フロントエンドが認証状態を認識できるように、ログイン情報を返す
    is_authenticated = current_user.is_authenticated
    user_info = {'id': current_user.id, 'username': current_user.username} if is_authenticated else {}
    
    # render_templateを呼び出し、ユーザー情報をJavaScriptで利用できるようにする
    # 実際には、このHTMLファイル内でJSをロードし、認証状態に応じてUIを切り替える
    return render_template('index.html', user_info=json.dumps(user_info))


# --- 保護されたゲームAPIエンドポイント ---

@app.route('/api/players', methods=['GET'])
@login_required  # ログイン必須
def get_players():
    """選手リストを取得するAPIエンドポイント"""
    return jsonify(TEAMS_DATA)

@app.route('/api/order', methods=['POST'])
@login_required  # ログイン必須
def receive_order():
    """オーダー情報を受け取るAPIエンドポイント"""
    order_data = request.json
    print(f"User {current_user.username} (ID: {current_user.id}) received order data (Player IDs):", json.dumps(order_data, indent=2))
    # 認証されたユーザーのIDを元にゲームデータを保存する処理を、今後追加できます
    return jsonify({"message": "Order received successfully!", "user_id": current_user.id}), 200

@app.route('/api/simulate_game', methods=['GET'])
@login_required  # ログイン必須
def simulate_game():
    """ランダムな試合結果を生成するAPIエンドポイント"""
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
        "result": result,
        "user_id": current_user.id # 誰がシミュレーションを実行したか
    }

    return jsonify(game_result)

if __name__ == '__main__':
    app.run(debug=True)