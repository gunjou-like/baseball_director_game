import json
import random
from datetime import datetime
import math # 対数計算のためにmathをインポート

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

# --- ゲームロジックのためのクラス定義 ---

class Team:
    """試合進行で使用するチーム情報"""
    def __init__(self, team_name, players, order_ids):
        self.name = team_name
        self.players_map = {p['id']: p for p in players} # 選手IDで引ける辞書
        self.batting_order = [self.players_map[pid] for pid in order_ids['batters']]
        self.pitcher = self.players_map[order_ids['pitcher']]
        self.batter_index = 0 # 現在の打者インデックス
    
    def next_batter(self):
        """次の打者を返す"""
        batter = self.batting_order[self.batter_index]
        self.batter_index = (self.batter_index + 1) % len(self.batting_order)
        return batter
    
    def get_pitcher(self):
        """現在の投手を返す"""
        return self.pitcher

class GameState:
    """試合状況を管理するクラス"""
    def __init__(self, team_a, team_b):
        self.inning = 1
        self.half = "top" # "top" or "bottom"
        self.outs = 0
        self.bases = [None, None, None] # [1B, 2B, 3B] 走者がいればplayer_id, なければNone
        self.score = { team_a.name: 0, team_b.name: 0 }
        self.team_at_bat = team_a
        self.team_in_field = team_b
        self.result_log = [] # 試合進行ログ
        
        # 自チームの選手IDのみでstats_updateを初期化
        # 投手の被安打(h_allowed)も追加。
        self.stats_update = {p['id']: {'pa': 0, 'h': 0, 'bb': 0, 'so': 0, 'hr': 0, 'sb': 0, 'ip': 0.0, 'h_allowed': 0} 
                             for p in team_a.players_map.values()}
        
    def switch_half(self):
        """イニング表裏を交代し、攻守を入れ替える"""
        self.outs = 0
        self.bases = [None, None, None]
        self.team_at_bat, self.team_in_field = self.team_in_field, self.team_at_bat
        
        if self.half == "bottom":
            self.inning += 1
            self.half = "top"
        else:
            self.half = "bottom"
            
    def current_pitcher(self):
        return self.team_in_field.get_pitcher()
    
    def current_batter(self):
        return self.team_at_bat.batting_order[self.team_at_bat.batter_index]

class GameEngine:
    """打席結果を計算し、試合を進行するエンジン"""
    
    def __init__(self, game_state):
        self.state = game_state
        self.log = []

    def run_game(self):
        """9イニングまで試合を進行させる"""
        while self.state.inning <= 9:
            self.log.append(f"--- {self.state.inning}回 {self.state.half} ---")
            self.play_half_inning()
        
        # 試合結果の集計
        if self.state.half == 'bottom':
            home_team_name = self.state.team_in_field.name
            away_team_name = self.state.team_at_bat.name
        else:
            home_team_name = self.state.team_at_bat.name
            away_team_name = self.state.team_in_field.name
            
        home_score = self.state.score[home_team_name]
        away_score = self.state.score[away_team_name]
        
        result_text = "勝利" if home_score > away_score else "敗北" if home_score < away_score else "引き分け"

        return {
            "home_score": home_score,
            "away_score": away_score,
            "result": result_text,
            "home_team": home_team_name,
            "away_team": away_team_name,
            "stats_update": self.state.stats_update
        }

    def play_half_inning(self):
        """半イニング（アウト3つ）を消化する"""
        start_inning = self.state.inning
        while self.state.outs < 3 and self.state.inning == start_inning:
            # 盗塁判定を打席前に実行
            self.attempt_steals()
            
            batter = self.state.team_at_bat.next_batter()
            pitcher = self.state.team_in_field.get_pitcher()
            
            # 打席進行
            result_type, runs = self.play_at_bat(batter, pitcher)
            
            # 成績更新
            is_batter_user_team = batter['id'] in self.state.stats_update
            is_pitcher_user_team = pitcher['id'] in self.state.stats_update
            
            # 打者成績の更新
            if is_batter_user_team:
                self.state.stats_update[batter['id']]['pa'] += 1
                if result_type == 'SO':
                    self.state.stats_update[batter['id']]['so'] += 1
                elif result_type == 'BB':
                    self.state.stats_update[batter['id']]['bb'] += 1
                elif result_type in ['1B', '2B', '3B', 'HR']:
                    self.state.stats_update[batter['id']]['h'] += 1 # 安打をカウント
                
                if result_type == 'HR':
                    self.state.stats_update[batter['id']]['hr'] += 1
            
            # 投手成績の更新
            if is_pitcher_user_team:
                # 投手のIPは常に更新
                self.state.stats_update[pitcher['id']]['ip'] += 1/3
                
                if result_type == 'SO':
                    self.state.stats_update[pitcher['id']]['so'] += 1 # 奪三振
                elif result_type == 'BB':
                    self.state.stats_update[pitcher['id']]['bb'] += 1 # 与四球
                elif result_type in ['1B', '2B', '3B', 'HR']:
                    self.state.stats_update[pitcher['id']]['h_allowed'] += 1 # 被安打
            
            # スコア更新
            self.state.score[self.state.team_at_bat.name] += runs
        
        self.state.switch_half()

    def attempt_steals(self):
        """盗塁の試行と結果を判定する (簡易ロジック)"""
        # 盗塁は一塁走者のみ試行すると仮定 (bases[0]が1塁走者)
        runner_id = self.state.bases[0]
        
        if runner_id is None:
            return

        # 走者が自チームの場合のみ成績を反映
        is_runner_user_team = runner_id in self.state.stats_update

        # 相手チームの盗塁は成績に反映しないため、ここで早期リターンをかける
        if not is_runner_user_team:
            return 

        runner = self.state.team_at_bat.players_map.get(runner_id)
        if not runner:
            return # 選手が見つからなければスキップ

        # 盗塁の総合確率を簡易計算 (スピード能力に基づく)
        speed_ability = runner['abilities']['speed']
        steal_prob = max(0.4, min(0.85, 0.01 * speed_ability))
        
        # 盗塁を試行する確率 (ランナーがいれば常にするわけではない)
        if random.random() < 0.2: # 20%の確率で盗塁を試行
            if random.random() < steal_prob:
                # 成功: 走者を2塁へ進める
                self.state.bases[0] = None
                self.state.bases[1] = runner_id
                
                self.log.append(f"[HOMERUN/STEAL DEBUG] STOLEN BASE SUCCESS! Runner: {runner['name']}")

                # 盗塁(SB)の成績更新を確実に実行
                self.state.stats_update[runner_id]['sb'] += 1
            else:
                # 失敗: アウト追加
                self.state.outs += 1
                self.state.bases[0] = None # 走者をアウトにする
                self.log.append(f"CAUGHT STEALING: {runner['name']} caught stealing. ({self.state.outs}アウト)")

    def play_at_bat(self, batter, pitcher):
        """
        打席結果を能力に基づいてシミュレートする
        能力値 (60-90) を確率に変換して使用。
        """
        
        # 1. 基本確率の算出 (対数スケールで能力差を強調)
        
        # 三振確率: 投手の球威(Power) vs 野手のミート(Meet)
        pitcher_so_factor = math.log(pitcher['abilities']['power'] - 50) 
        batter_so_factor = math.log(batter['abilities']['meet'] - 50)
        so_prob = 0.25 + 0.05 * (pitcher_so_factor - batter_so_factor)
        so_prob = max(0.10, min(0.40, so_prob)) # 確率を0.10〜0.40に制限
        
        # 四球確率: 投手の制球(Control) 
        bb_prob = 0.10 - 0.001 * (pitcher['abilities']['control'] - 60)
        bb_prob = max(0.05, min(0.20, bb_prob)) # 確率を0.05〜0.20に制限
        
        # 本塁打確率: 野手のパワー(Power) vs 投手のパワー(Power)
        batter_hr_factor = batter['abilities']['power'] - 60
        pitcher_hr_factor = pitcher['abilities']['power'] - 60
        # パワー差で0.005から0.035程度の確率
        hr_prob = 0.15 + 0.0005 * (batter_hr_factor - pitcher_hr_factor)
        hr_prob = max(0.005, min(0.035, hr_prob)) # 確率を0.005〜0.035に制限
        
        # 2. 結果判定
        rand = random.random()
        
        # 本塁打判定
        if rand < hr_prob: 
            self.log.append(f"{batter['name']} HR!")
            return 'HR', self.move_runners(4, batter['id']) # HRは4塁打
        
        # 三振 (SO)
        if rand < so_prob:
            self.state.outs += 1
            self.log.append(f"{batter['name']} SO ({self.state.outs}アウト)")
            return 'SO', self.move_runners(0)

        # 四球 (BB)
        elif rand < so_prob + bb_prob:
            self.log.append(f"{batter['name']} BB")
            self.state.bases[0] = batter['id'] # 打者を出塁させる
            return 'BB', self.move_runners(1) # 1は移動する塁数ではなく、四球/単打の区別
        
        # 安打・凡退
        else:
            # 残り確率で安打 (H) か凡退 (OUT) かを決定
            # 投手の能力が高いほど、安打確率が下がる
            hit_prob = 0.30 - 0.002 * (pitcher['abilities']['control'] + pitcher['abilities']['power'] - 120)
            hit_prob = max(0.20, min(0.45, hit_prob))
            
            # ヒットかどうか
            if random.random() < hit_prob:
                # 安打の種類をランダムに決定 (単打, 二塁打, 三塁打)
                hit_type = random.choices(['1B', '2B', '3B'], weights=[0.75, 0.20, 0.05], k=1)[0]
                bases_moved = {'1B': 1, '2B': 2, '3B': 3}[hit_type]
                self.log.append(f"{batter['name']} {hit_type}")
                return hit_type, self.move_runners(bases_moved, batter['id'])
            
            # 凡退 (OUT)
            else:
                self.state.outs += 1
                self.log.append(f"{batter['name']} OUT ({self.state.outs}アウト)")
                return 'OUT', self.move_runners(0) # 走者移動なし

    def move_runners(self, bases_hit, batter_id=None):
        """
        走者を動かし、得点を計算する。
        """
        runs = 0
        new_bases = [None, None, None]
        
        # 1. 既存走者の移動
        for i in range(2, -1, -1): # 3B -> 2B -> 1B の順でチェック
            runner_id = self.state.bases[i]
            if runner_id is not None:
                new_base = i + 1 + bases_hit
                if new_base >= 4:
                    runs += 1
                else:
                    new_bases[new_base - 1] = runner_id
        
        # 2. 打者の移動
        if batter_id is not None:
            if bases_hit >= 4: # 本塁打（4塁打以上）
                runs += 1 # 打者自身も得点
            elif bases_hit > 0:
                new_bases[bases_hit - 1] = batter_id
        
        self.state.bases = new_bases
        return runs

def update_stats_after_game(teams_data, user_team_name, game_result):
    """
    試合結果に基づいて、ユーザーチームの成績を更新する
    """
    teams_data = json.loads(json.dumps(teams_data)) # 変更可能なコピーを作成
    user_team_players = teams_data[user_team_name]
    
    # 統計集計マップを生成
    # 試合結果から得られた成績の増分
    update_data = game_result.get('stats_update', {})

    for player in user_team_players:
        p_id = player['id']
        update = update_data.get(p_id, None)
        
        if update:
            # 野手成績の更新
            if not player['is_pitcher']:
                
                # 集計値の更新
                player['stats']['pa'] += update.get('pa', 0)
                player['stats']['h'] += update.get('h', 0)
                player['stats']['bb'] += update.get('bb', 0)
                player['stats']['so'] += update.get('so', 0)
                player['stats']['hr'] += update.get('hr', 0) # 本塁打
                player['stats']['sb'] += update.get('sb', 0) # 盗塁
                
                # 計算: 打数 (AB) = 打席 (PA) - 四球 (BB)
                ab = player['stats']['pa'] - player['stats']['bb']
                hits = player['stats']['h']
                
                # 打率の計算 (打数 > 0 の場合のみ)
                if ab > 0:
                    # 少数第3位までの文字列として保持
                    player['stats']['batting_avg'] = round(hits / ab, 3) 
                else:
                    player['stats']['batting_avg'] = 0.000

            # 投手成績の更新
            else:
                # 集計値の更新
                player['stats']['ip'] += update.get('ip', 0.0)
                player['stats']['so'] += update.get('so', 0)
                player['stats']['bb'] += update.get('bb', 0)
                player['stats']['h_allowed'] += update.get('h_allowed', 0)
                
                # IPの計算を整数と端数に分解して正確に計算
                total_outs = round(player['stats']['ip'] * 3)
                innings_pitched_for_calc = total_outs / 3
                
                if innings_pitched_for_calc > 0:
                    # 奪三振率: (SO * 9) / IP
                    player['stats']['strikeout_rate'] = round((player['stats']['so'] * 9) / innings_pitched_for_calc, 2)
                    # 与四球率: (BB * 9) / IP
                    player['stats']['walk_rate'] = round((player['stats']['bb'] * 9) / innings_pitched_for_calc, 2)
                    
                    # 被打率: H_allowed / (H_allowed + Outs_by_opponents)
                    outs_by_opponents = total_outs - player['stats']['so']
                    
                    if player['stats']['h_allowed'] + outs_by_opponents > 0:
                         player['stats']['batting_avg_allowed'] = round(player['stats']['h_allowed'] / (player['stats']['h_allowed'] + outs_by_opponents), 3)
                    else:
                        player['stats']['batting_avg_allowed'] = 0.000
                else:
                    player['stats']['strikeout_rate'] = 0.0
                    player['stats']['walk_rate'] = 0.0
                    player['stats']['batting_avg_allowed'] = 0.000
    
    return teams_data


# --- DBモデル定義（変更なし） ---

# 選手の初期成績と能力値をランダム生成するヘルパー関数
def create_random_player_data(is_pitcher):
    if is_pitcher:
        # 投手成績: 奪三振率、与四球率、被打率
        stats = {
            "strikeout_rate": 0.0, 
            "walk_rate": 0.0,
            "batting_avg_allowed": 0.0,
            # 成績計算のための内部集計値
            "so": 0, "bb": 0, "h_allowed": 0, "ip": 0.0
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
            "batting_avg": 0.000, 
            "homeruns": 0,
            "steals": 0,
            # 成績計算のための内部集計値
            "pa": 0, "ab": 0, "h": 0, "bb": 0, "so": 0, "hr": 0, "sb": 0
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
        "自チーム (blue)": [ # フロントエンドの修正に合わせて、ここを "自チーム (blue)" に合わせる
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

    # 1. 試合の準備
    teams_data = json.loads(user_state.teams_json)
    user_order = json.loads(user_state.current_order_json)
    user_team_name = "自チーム (blue)"
    
    # オーダーが空の場合はシミュレーションを中止
    if not user_order['batters'] or user_order['pitcher'] is None:
        # ランダムな試合結果を返さず、警告を返す
        return jsonify({"message": "オーダーが設定されていません。先にオーダーを決定してください。", "warning": True}), 200

    # 対戦相手のランダム選択
    opponent_teams_names = [t for t in teams_data.keys() if t != user_team_name]
    opponent_team_name = random.choice(opponent_teams_names)
    
    # 相手チームのオーダーを自動生成 (ランダムな打順と先発投手)
    opponent_players = teams_data[opponent_team_name]
    opponent_batters = [p for p in opponent_players if not p['is_pitcher']]
    opponent_pitchers = [p for p in opponent_players if p['is_pitcher']]
    
    random.shuffle(opponent_batters)
    opponent_pitcher = random.choice(opponent_pitchers) if opponent_pitchers else None

    opponent_order = {
        "batters": [p['id'] for p in opponent_batters[:9]],
        "pitcher": opponent_pitcher['id'] if opponent_pitcher else None
    }
    
    # 2. Teamオブジェクトの作成
    user_team = Team(user_team_name, teams_data[user_team_name], user_order)
    opponent_team = Team(opponent_team_name, teams_data[opponent_team_name], opponent_order)
    
    # 3. 試合の実行
    engine = GameEngine(GameState(user_team, opponent_team))
    game_result_data = engine.run_game()
    
    # 4. 成績データの更新 (簡易的な更新ロジックを呼び出し)
    updated_teams_data = update_stats_after_game(teams_data, user_team_name, game_result_data)
    
    # 5. DBに保存
    schedule = json.loads(user_state.schedule_json)
    schedule.append({
        "home_team": game_result_data['home_team'],
        "away_team": game_result_data['away_team'],
        "home_score": game_result_data['home_score'],
        "away_score": game_result_data['away_score'],
        "result": game_result_data['result'],
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "log": engine.log # 試合ログを保存（デバッグ用）
    })
    
    user_state.schedule_json = json.dumps(schedule)
    user_state.teams_json = json.dumps(updated_teams_data) # 更新された選手データを保存
    db.session.commit()

    return jsonify({"message": "Game simulated and state saved.", "log": engine.log}), 200

if __name__ == '__main__':
    # 開発環境でのみポート5000を使用
    app.run(debug=True, port=5000)
