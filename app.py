import argparse
import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify

from models import db, Prompt
from models.daily_log import DailyLog
from models.weekly_log import WeeklyLog
from models.monthly_log import MonthlyLog
from models.yearly_log import YearlyLog
from models.system_config import SystemConfig
from datetime import date, datetime, timedelta
from utils.log_utils import setup_logger
from utils.db_seeder import init_database, seed_initial_data, truncate_all_tables, get_start_date
from utils.datetime_utils import now_jst, get_monday_of_week, get_week_number_in_month
from utils.constants import MAX_DAILY_ALERTS

# ロガーの設定
app_logger = setup_logger(logger_name="app", log_file_name="app.log")

# .envファイルから環境変数を読み込む
load_dotenv()

# Flaskアプリケーションの作成
app = Flask(__name__)

# データベース設定の読み込み
db_type = os.getenv('DATABASE_TYPE', 'sqlite').lower()

if db_type == 'sqlite':
    database_url = os.getenv('SQLITE_DATABASE_URL', 'sqlite:///ai-diary.db')
    
    # 接続文字列からファイルパスを抽出
    if database_url.startswith('sqlite:///'):
        db_path = database_url[10:]
    elif database_url.startswith('sqlite://'):
        db_path = database_url[9:]
    else:
        db_path = None
        
    if db_path and db_path != ':memory:':
        # 絶対パスに変換
        abs_path = os.path.abspath(db_path)
        dir_name = os.path.dirname(abs_path)
        
        # ディレクトリの作成
        if dir_name and not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)
            app_logger.info(f"SQLite用ディレクトリを作成しました: {dir_name}")
            
        # ファイルの作成
        if not os.path.exists(abs_path):
            with open(abs_path, 'w') as f:
                pass
            app_logger.info(f"SQLiteデータベースファイルを作成しました: {abs_path}")
            
        # SQLAlchemy用のURIを絶対パスで上書き（Windows対策・絶対パスの保証）
        abs_path_slashes = abs_path.replace('\\', '/')
        database_url = f"sqlite:///{abs_path_slashes}"
else:
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL環境変数が設定されていません。.envファイルを確認してください。")

# 先行生成年数を環境変数から取得（デフォルト2年）
pre_generate_years = int(os.getenv('PRE_GENERATE_YEARS', '2'))

# Flask-SQLAlchemyの設定
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# SQLAlchemyをアプリに初期化
db.init_app(app)


# ルート定義
@app.route('/')
@app.route('/dashboard')
def dashboard():
    """ダッシュボード"""
    return render_template('dashboard.html', 
                         daily_alerts=get_daily_alerts(),
                         weekly_alerts=get_weekly_alerts(),
                         monthly_alerts=get_monthly_alerts(),
                         yearly_alerts=get_yearly_alerts())


def get_daily_alerts():
    """未完了のデイリーログを取得してアラート用のデータを返す"""
    try:
        # システム開始日を取得
        start_date = get_start_date()
        
        # 今日の日付を取得
        today = now_jst().date()
        
        # 未完了のログを取得（開始日から今日まで、dateの昇順、最大MAX_DAILY_ALERTS件）
        incomplete_logs = DailyLog.query.filter(
            DailyLog.date >= start_date,
            DailyLog.date <= today,
            DailyLog.is_completed != True  # None と False の両方を含む
        ).order_by(DailyLog.date.asc()).limit(MAX_DAILY_ALERTS).all()
        
        # アラート用のデータを整形
        alerts = []
        for log in incomplete_logs:
            alerts.append({
                'date': log.date,
                'date_str': log.date.isoformat(),
                'date_jp': format_date_japanese(log.date)
            })
        
        return alerts
    except Exception as e:
        app_logger.error(f"デイリーアラートの取得中にエラーが発生しました: {e}")
        return []


def format_date_japanese(target_date):
    """日付を日本語形式でフォーマット（例: 2024年1月15日）"""
    return f"{target_date.year}年{target_date.month}月{target_date.day}日"


def get_weekly_alerts():
    """未完了のウィークリーログを取得してアラート用のデータを返す"""
    try:
        # 今日の日付を取得
        today = now_jst().date()
        
        # 今週の月曜日を取得
        current_week_monday = get_monday_of_week(today)
        
        # システム開始日を取得
        start_date = get_start_date()
        
        # 今週より前の週で、未完了のログを取得（start_date以降、dateの昇順、最大MAX_DAILY_ALERTS件）
        incomplete_logs = WeeklyLog.query.filter(
            WeeklyLog.start_date >= get_monday_of_week(start_date),
            WeeklyLog.start_date < current_week_monday,  # 今週は含まない
            WeeklyLog.is_completed != True  # None と False の両方を含む
        ).order_by(WeeklyLog.start_date.asc()).limit(MAX_DAILY_ALERTS).all()
        
        # アラート用のデータを整形
        alerts = []
        for log in incomplete_logs:
            alerts.append({
                'id': log.id,
                'date_jp': format_weekly_date_japanese(log.start_date, log.week_number)
            })
        
        return alerts
    except Exception as e:
        app_logger.error(f"ウィークリーアラートの取得中にエラーが発生しました: {e}")
        return []


def get_monthly_alerts():
    """未完了のマンスリーログを取得してアラート用のデータを返す"""
    try:
        # 今日の日付を取得
        today = now_jst().date()
        
        # 今月の1日を取得
        current_month_first = date(today.year, today.month, 1)
        
        # システム開始日を取得
        start_date = get_start_date()
        
        # 今月より前の月で、未完了のログを取得（start_date以降、dateの昇順、最大MAX_DAILY_ALERTS件）
        incomplete_logs = MonthlyLog.query.filter(
            MonthlyLog.first_day >= date(start_date.year, start_date.month, 1),
            MonthlyLog.first_day < current_month_first,  # 今月は含まない
            MonthlyLog.is_completed != True  # None と False の両方を含む
        ).order_by(MonthlyLog.first_day.asc()).limit(MAX_DAILY_ALERTS).all()
        
        # アラート用のデータを整形
        alerts = []
        for log in incomplete_logs:
            period = f"{log.year}-{log.month:02d}"
            alerts.append({
                'id': log.id,
                'date_jp': f"{log.year}年{log.month}月"
            })
        
        return alerts
    except Exception as e:
        app_logger.error(f"マンスリーアラートの取得中にエラーが発生しました: {e}")
        return []


def get_yearly_alerts():
    """未完了のイヤリーログを取得してアラート用のデータを返す"""
    try:
        # 今日の日付を取得
        today = now_jst().date()
        
        # 今年の1月1日を取得
        current_year_first = date(today.year, 1, 1)
        
        # システム開始日を取得
        start_date = get_start_date()
        
        # 今年より前の年で、未完了のログを取得（start_date以降、dateの昇順、最大MAX_DAILY_ALERTS件）
        incomplete_logs = YearlyLog.query.filter(
            YearlyLog.first_day >= date(start_date.year, 1, 1),
            YearlyLog.first_day < current_year_first,  # 今年は含まない
            YearlyLog.is_completed != True  # None と False の両方を含む
        ).order_by(YearlyLog.first_day.asc()).limit(MAX_DAILY_ALERTS).all()
        
        # アラート用のデータを整形
        alerts = []
        for log in incomplete_logs:
            period = str(log.year)
            alerts.append({
                'id': log.id,
                'date_jp': f"{log.year}年"
            })
        
        return alerts
    except Exception as e:
        app_logger.error(f"イヤリーアラートの取得中にエラーが発生しました: {e}")
        return []


def format_weekly_date_japanese(start_date, week_number):
    """週の日付を日本語形式でフォーマット（例: 2024年1月第1週）"""
    return f"{start_date.year}年{start_date.month}月第{week_number}週"


def get_weekday_japanese(target_date):
    """日付から日本語の曜日を取得"""
    weekdays = ['月', '火', '水', '木', '金', '土', '日']
    return weekdays[target_date.weekday()]


@app.route('/journal')
def journal():
    """デイリー日記"""
    return render_template('journal.html')


@app.route('/milestones')
def milestones():
    """日記検索"""
    return render_template('milestones.html')


@app.route('/config', methods=['GET', 'POST'])
def config():
    """設定"""
    if request.method == 'POST':
        # POSTリクエストの場合、プロンプトを更新
        daily_template = request.form.get('daily_prompt', '')
        weekly_template = request.form.get('weekly_prompt', '')
        monthly_template = request.form.get('monthly_prompt', '')
        yearly_template = request.form.get('yearly_prompt', '')
        
        # 各プロンプトを更新または作成
        prompts = [
            ('daily', daily_template),
            ('weekly', weekly_template),
            ('monthly', monthly_template),
            ('yearly', yearly_template)
        ]
        
        for log_type, template in prompts:
            prompt = Prompt.query.filter_by(log_type=log_type).first()
            if prompt:
                prompt.template = template
            else:
                prompt = Prompt(log_type=log_type, template=template)
                db.session.add(prompt)
        
        db.session.commit()
        app_logger.info("プロンプト設定を更新しました")
        
        return jsonify({'status': 'success', 'message': 'プロンプト設定を保存しました'}), 200
    
    # GETリクエストの場合、プロンプトを取得して表示
    daily_prompt = Prompt.query.filter_by(log_type='daily').first()
    weekly_prompt = Prompt.query.filter_by(log_type='weekly').first()
    monthly_prompt = Prompt.query.filter_by(log_type='monthly').first()
    yearly_prompt = Prompt.query.filter_by(log_type='yearly').first()
    
    return render_template('config.html',
                         daily_prompt=daily_prompt.template if daily_prompt else '',
                         weekly_prompt=weekly_prompt.template if weekly_prompt else '',
                         monthly_prompt=monthly_prompt.template if monthly_prompt else '',
                         yearly_prompt=yearly_prompt.template if yearly_prompt else '')


@app.route('/summary')
def summary():
    """要約作成"""
    type_param = request.args.get('type')
    id_param = request.args.get('id')
    
    # weekly の場合の処理
    if type_param == 'weekly' and id_param:
        try:
            weekly_id = int(id_param)
            weekly_log = WeeklyLog.query.get(weekly_id)
            
            if not weekly_log:
                return render_template('summary.html', error='週次ログが見つかりませんでした')
            
            # 週の開始日（月曜日）を取得
            start_date = weekly_log.start_date
            
            # 週の終了日（日曜日）を計算
            end_date = start_date + timedelta(days=6)
            
            # 1週間分のデイリーログを取得（月曜日から日曜日まで）
            daily_logs = DailyLog.query.filter(
                DailyLog.date >= start_date,
                DailyLog.date <= end_date
            ).order_by(DailyLog.date.asc()).all()
            
            # 7日分のデータを配列に格納（存在しない日はNone）
            week_data = []
            for i in range(7):
                current_date = start_date + timedelta(days=i)
                daily_log = next((log for log in daily_logs if log.date == current_date), None)
                week_data.append({
                    'date': current_date,
                    'content': daily_log.content if daily_log else None
                })
            # JavaScript用：dateをISO文字列に変換（tojsonで確実にシリアライズできるようにする）
            week_data_for_js = [
                {'date': d['date'].isoformat(), 'content': d['content']}
                for d in week_data
            ]
            
            # 週のタイトルを生成
            week_title = format_weekly_date_japanese(start_date, weekly_log.week_number)
            
            return render_template('summary.html',
                                 type='weekly',
                                 weekly_log=weekly_log,
                                 week_data=week_data,
                                 week_data_for_js=week_data_for_js,
                                 week_title=week_title,
                                 get_weekday_japanese=get_weekday_japanese,
                                 format_date_japanese=format_date_japanese)
        except ValueError:
            return render_template('summary.html', error='無効なIDです')
        except Exception as e:
            app_logger.error(f"要約作成画面の表示中にエラーが発生しました: {e}")
            return render_template('summary.html', error='データの取得中にエラーが発生しました')
    
    # monthly の場合の処理
    elif type_param == 'monthly' and id_param:
        try:
            monthly_id = int(id_param)
            monthly_log = MonthlyLog.query.get(monthly_id)
            
            if not monthly_log:
                return render_template('summary.html', error='月次ログが見つかりませんでした')
            
            # yearとmonthを取得
            year = monthly_log.year
            month = monthly_log.month
            
            # 同一のyearとmonthのWeeklyLogを取得（week_numberの昇順でソート）
            weekly_logs = WeeklyLog.query.filter(
                WeeklyLog.year == year,
                WeeklyLog.month == month
            ).order_by(WeeklyLog.week_number.asc()).all()
            
            # 月のタイトルを生成
            month_title = f"{year}年{month}月"
            
            # プロンプトコピー用の月データ（週次ログをstart_date, week_number, content形式で）
            month_data = [
                {
                    'start_date': wl.start_date.isoformat(),
                    'week_number': wl.week_number,
                    'content': wl.content
                }
                for wl in weekly_logs
            ]
            
            return render_template('summary.html', 
                                 type='monthly',
                                 monthly_log=monthly_log,
                                 weekly_logs=weekly_logs,
                                 month_data=month_data,
                                 month_title=month_title,
                                 get_weekday_japanese=get_weekday_japanese,
                                 format_date_japanese=format_date_japanese,
                                 format_weekly_date_japanese=format_weekly_date_japanese)
        except ValueError:
            return render_template('summary.html', error='無効なIDです')
        except Exception as e:
            app_logger.error(f"要約作成画面の表示中にエラーが発生しました: {e}")
            return render_template('summary.html', error='データの取得中にエラーが発生しました')
    
    # yearly の場合の処理
    elif type_param == 'yearly' and id_param:
        try:
            yearly_id = int(id_param)
            yearly_log = YearlyLog.query.get(yearly_id)
            
            if not yearly_log:
                return render_template('summary.html', error='年次ログが見つかりませんでした')
            
            # yearを取得
            year = yearly_log.year
            
            # 同一のyearのMonthlyLogを取得（monthの昇順でソート）
            monthly_logs = MonthlyLog.query.filter(
                MonthlyLog.year == year
            ).order_by(MonthlyLog.month.asc()).all()
            
            # 年のタイトルを生成
            year_title = f"{year}年"
            
            return render_template('summary.html', 
                                 type='yearly',
                                 yearly_log=yearly_log,
                                 monthly_logs=monthly_logs,
                                 year_title=year_title)
        except ValueError:
            return render_template('summary.html', error='無効なIDです')
        except Exception as e:
            app_logger.error(f"要約作成画面の表示中にエラーが発生しました: {e}")
            return render_template('summary.html', error='データの取得中にエラーが発生しました')
    
    # その他のtypeやパラメータがない場合はエラー
    return render_template('summary.html', error='パラメータが不正です')


@app.route('/api/prompt/daily', methods=['GET'])
def get_daily_prompt():
    """デイリープロンプトを取得するAPI"""
    prompt = Prompt.query.filter_by(log_type='daily').first()
    if prompt:
        return jsonify({'status': 'success', 'template': prompt.template}), 200
    else:
        return jsonify({'status': 'error', 'message': 'プロンプトが見つかりませんでした'}), 404


@app.route('/api/prompt/weekly', methods=['GET'])
def get_weekly_prompt():
    """ウィークリープロンプトを取得するAPI"""
    prompt = Prompt.query.filter_by(log_type='weekly').first()
    if prompt:
        return jsonify({'status': 'success', 'template': prompt.template}), 200
    else:
        return jsonify({'status': 'error', 'message': 'プロンプトが見つかりませんでした'}), 404


@app.route('/api/prompt/monthly', methods=['GET'])
def get_monthly_prompt():
    """マンスリープロンプトを取得するAPI"""
    prompt = Prompt.query.filter_by(log_type='monthly').first()
    if prompt:
        return jsonify({'status': 'success', 'template': prompt.template}), 200
    else:
        return jsonify({'status': 'error', 'message': 'プロンプトが見つかりませんでした'}), 404


@app.route('/api/prompt/yearly', methods=['GET'])
def get_yearly_prompt():
    """イヤリープロンプトを取得するAPI"""
    prompt = Prompt.query.filter_by(log_type='yearly').first()
    if prompt:
        return jsonify({'status': 'success', 'template': prompt.template}), 200
    else:
        return jsonify({'status': 'error', 'message': 'プロンプトが見つかりませんでした'}), 404


@app.route('/api/journal/<date_str>', methods=['GET', 'POST'])
def journal_api(date_str):
    """日記データの取得・更新API"""
    try:
        # 日付文字列をdateオブジェクトに変換
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'status': 'error', 'message': '無効な日付形式です'}), 400
    
    if request.method == 'GET':
        # GET: 日記データを取得
        daily_log = DailyLog.query.filter_by(date=target_date).first()
        
        if not daily_log:
            # データが存在しない場合
            today = date.today()
            if target_date > today:
                # 未来の日付の場合
                return jsonify({
                    'status': 'error',
                    'message': '未来の日付は登録できません',
                    'is_future': True
                }), 404
            else:
                # 過去の日付でデータが存在しない場合（通常は発生しないはず）
                return jsonify({
                    'status': 'error',
                    'message': 'データが見つかりませんでした',
                    'is_future': False
                }), 404
        
        return jsonify({
            'status': 'success',
            'content': daily_log.content if daily_log.content else ''
        }), 200
    
    elif request.method == 'POST':
        # POST: 日記データを更新
        content = request.form.get('content', '')
        
        daily_log = DailyLog.query.filter_by(date=target_date).first()
        
        if not daily_log:
            return jsonify({
                'status': 'error',
                'message': 'データが見つかりませんでした'
            }), 404
        
        # データを更新（下書きは破棄、清書のみ保存）
        daily_log.content = content

        # 入力完了フラグを更新
        if daily_log.content == '':
            daily_log.is_completed = False
        else:
            daily_log.is_completed = True
        
        db.session.commit()
        
        app_logger.info(f"日記データを更新しました: {target_date}")
        
        return jsonify({
            'status': 'success',
            'message': '日記を保存しました'
        }), 200


@app.route('/api/weekly/<int:weekly_id>', methods=['POST'])
def weekly_api(weekly_id):
    """週次ログデータの更新API"""
    try:
        weekly_log = WeeklyLog.query.get(weekly_id)
        
        if not weekly_log:
            return jsonify({
                'status': 'error',
                'message': '週次ログが見つかりませんでした'
            }), 404
        
        # POST: 週次ログデータを更新
        content = request.form.get('content', '')
        
        # データを更新
        weekly_log.content = content
        
        # 入力完了フラグを更新
        if weekly_log.content == '':
            weekly_log.is_completed = False
        else:
            weekly_log.is_completed = True
        
        db.session.commit()
        
        app_logger.info(f"週次ログデータを更新しました: {weekly_id}")
        
        return jsonify({
            'status': 'success',
            'message': '要約を保存しました'
        }), 200
    except Exception as e:
        app_logger.error(f"週次ログデータの更新中にエラーが発生しました: {e}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'データの保存中にエラーが発生しました'
        }), 500


@app.route('/api/monthly/<int:monthly_id>', methods=['POST'])
def monthly_api(monthly_id):
    """月次ログデータの更新API"""
    try:
        monthly_log = MonthlyLog.query.get(monthly_id)
        
        if not monthly_log:
            return jsonify({
                'status': 'error',
                'message': '月次ログが見つかりませんでした'
            }), 404
        
        # POST: 月次ログデータを更新
        content = request.form.get('content', '')
        
        # データを更新
        monthly_log.content = content
        
        # 入力完了フラグを更新
        if monthly_log.content == '':
            monthly_log.is_completed = False
        else:
            monthly_log.is_completed = True
        
        db.session.commit()
        
        app_logger.info(f"月次ログデータを更新しました: {monthly_id}")
        
        return jsonify({
            'status': 'success',
            'message': '要約を保存しました'
        }), 200
    except Exception as e:
        app_logger.error(f"月次ログデータの更新中にエラーが発生しました: {e}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'データの保存中にエラーが発生しました'
        }), 500


@app.route('/api/yearly/<int:yearly_id>', methods=['POST'])
def yearly_api(yearly_id):
    """年次ログデータの更新API"""
    try:
        yearly_log = YearlyLog.query.get(yearly_id)
        
        if not yearly_log:
            return jsonify({
                'status': 'error',
                'message': '年次ログが見つかりませんでした'
            }), 404
        
        # POST: 年次ログデータを更新
        content = request.form.get('content', '')
        
        # データを更新
        yearly_log.content = content
        
        # 入力完了フラグを更新
        if yearly_log.content == '':
            yearly_log.is_completed = False
        else:
            yearly_log.is_completed = True
        
        db.session.commit()
        
        app_logger.info(f"年次ログデータを更新しました: {yearly_id}")
        
        return jsonify({
            'status': 'success',
            'message': '要約を保存しました'
        }), 200
    except Exception as e:
        app_logger.error(f"年次ログデータの更新中にエラーが発生しました: {e}")
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'データの保存中にエラーが発生しました'
        }), 500


@app.route('/export')
def export():
    """エクスポートページを表示"""
    return render_template('export.html')


@app.route('/api/export')
def api_export():
    """日記データをエクスポートして静的HTMLファイルを生成"""
    try:
        # is_completed=Trueのデイリーログをdate昇順で取得
        daily_logs = DailyLog.query.filter(
            DailyLog.is_completed == True
        ).order_by(DailyLog.date.asc()).all()
        
        # HTMLコンテンツを生成
        html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AIダイアリー</title>
    <link rel="stylesheet" href="static/css/tailwind.css">
</head>
<body class="bg-white">
    <!-- ヘッダー -->
    <header class="bg-blue-600 border-b border-blue-700 sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between items-center h-16">
                <div class="flex items-center">
                    <h1 class="text-xl font-semibold text-white">AIダイアリー</h1>
                </div>
            </div>
        </div>
    </header>

    <!-- メインコンテンツ -->
    <main class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div class="space-y-4">
            <div class="space-y-4">
"""
        
        # 日記開始前の年次ログを挿入
        if daily_logs:
            first_diary_date = daily_logs[0].date
            first_diary_year = first_diary_date.year
            
            # 日記開始年より前の年次ログを取得（年が古い順）
            pre_diary_yearly_logs = YearlyLog.query.filter(
                YearlyLog.year < first_diary_year
            ).order_by(YearlyLog.year.asc()).all()
            
            # 日記開始前の年次ログを出力
            for yearly_log in pre_diary_yearly_logs:
                if yearly_log.content:
                    yearly_content = yearly_log.content
                    # 改行コードを統一（\r\n → \n）
                    yearly_content = yearly_content.replace('\r\n', '\n').replace('\r', '\n')
                    # HTMLエスケープ
                    yearly_content = yearly_content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#39;')
                    html_content += f"""                <div class="bg-white border border-gray-300 rounded-lg overflow-hidden">
                    <div class="bg-purple-300 px-4 py-2">
                        <div class="text-sm font-medium text-purple-900">【年次】{yearly_log.year}年</div>
                    </div>
                    <div class="p-6">
                        <div class="text-gray-900 whitespace-pre-wrap">{yearly_content}</div>
                    </div>
                </div>
"""
        
        # 各ログをカードとして追加
        if daily_logs:
            for log in daily_logs:
                current_date = log.date
                
                # 年次ログの挿入（1月1日の場合）
                if current_date.month == 1 and current_date.day == 1:
                    yearly_log = YearlyLog.query.filter_by(first_day=current_date).first()
                    if yearly_log and yearly_log.content:
                        yearly_content = yearly_log.content
                        # 改行コードを統一（\r\n → \n）
                        yearly_content = yearly_content.replace('\r\n', '\n').replace('\r', '\n')
                        # HTMLエスケープ
                        yearly_content = yearly_content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#39;')
                        html_content += f"""                <div class="bg-white border border-gray-300 rounded-lg overflow-hidden">
                    <div class="bg-purple-300 px-4 py-2">
                        <div class="text-sm font-medium text-purple-900">【年次】{yearly_log.year}年</div>
                    </div>
                    <div class="p-6">
                        <div class="text-gray-900 whitespace-pre-wrap">{yearly_content}</div>
                    </div>
                </div>
"""
                
                # 週次ログの挿入（月曜日の場合）
                if current_date.weekday() == 0:  # 0 = 月曜日
                    weekly_log = WeeklyLog.query.filter_by(start_date=current_date - timedelta(days=7)).first()
                    if weekly_log and weekly_log.content:
                        weekly_content = weekly_log.content
                        # 改行コードを統一（\r\n → \n）
                        weekly_content = weekly_content.replace('\r\n', '\n').replace('\r', '\n')
                        # HTMLエスケープ
                        weekly_content = weekly_content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#39;')
                        week_title = format_weekly_date_japanese(weekly_log.start_date, weekly_log.week_number)
                        html_content += f"""                <div class="bg-white border border-gray-300 rounded-lg overflow-hidden">
                    <div class="bg-blue-300 px-4 py-2">
                        <div class="text-sm font-medium text-blue-900">【週次】{week_title}</div>
                    </div>
                    <div class="p-6">
                        <div class="text-gray-900 whitespace-pre-wrap">{weekly_content}</div>
                    </div>
                </div>
"""
                        # 月次ログの挿入（その月の最終週次ログの場合）
                        # 自分より後ろの週次ログが同じ月に存在しないかチェック
                        is_last_weekly_of_month = not WeeklyLog.query.filter(
                            WeeklyLog.year == weekly_log.year,
                            WeeklyLog.month == weekly_log.month,
                            WeeklyLog.start_date > weekly_log.start_date
                        ).first()
                        if is_last_weekly_of_month:
                            month_first_day = date(weekly_log.year, weekly_log.month, 1)
                            monthly_log = MonthlyLog.query.filter_by(first_day=month_first_day).first()
                            if monthly_log and monthly_log.content:
                                monthly_content = monthly_log.content
                                # 改行コードを統一（\r\n → \n）
                                monthly_content = monthly_content.replace('\r\n', '\n').replace('\r', '\n')
                                # HTMLエスケープ
                                monthly_content = monthly_content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#39;')
                                html_content += f"""                <div class="bg-white border border-gray-300 rounded-lg overflow-hidden">
                    <div class="bg-green-300 px-4 py-2">
                        <div class="text-sm font-medium text-green-900">【月次】{monthly_log.year}年{monthly_log.month}月</div>
                    </div>
                    <div class="p-6">
                        <div class="text-gray-900 whitespace-pre-wrap">{monthly_content}</div>
                    </div>
                </div>
"""
                
                # デイリーログの挿入
                date_jp = format_date_japanese(current_date)
                weekday = get_weekday_japanese(current_date)
                content = log.content if log.content else '（内容なし）'
                # 改行コードを統一（\r\n → \n）
                content = content.replace('\r\n', '\n').replace('\r', '\n')
                # HTMLエスケープ
                content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&#39;')
                
                html_content += f"""                <div class="bg-white border border-gray-300 rounded-lg overflow-hidden">
                    <div class="bg-gray-200 px-4 py-2">
                        <div class="text-sm font-medium text-gray-700">{date_jp}（{weekday}）</div>
                    </div>
                    <div class="p-6">
                        <div class="text-gray-900 whitespace-pre-wrap">{content}</div>
                    </div>
                </div>
"""
        else:
            html_content += """                <div class="text-center py-8 text-gray-500">
                    エクスポートするデータがありません
                </div>
"""
        
        html_content += """            </div>
        </div>
    </main>
</body>
</html>"""
        
        # app.pyと同じディレクトリにexport.htmlを保存
        export_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'export.html')
        with open(export_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        app_logger.info(f"日記データをエクスポートしました: {export_path}")
        
        return jsonify({
            'status': 'success',
            'message': f'日記データをexport.htmlにエクスポートしました（{len(daily_logs)}件）',
            'count': len(daily_logs),
            'path': export_path
        }), 200
        
    except Exception as e:
        app_logger.error(f"エクスポート処理中にエラーが発生しました: {e}")
        return jsonify({
            'status': 'error',
            'message': 'エクスポート処理中にエラーが発生しました'
        }), 500


@app.route('/api/search', methods=['GET'])
def search_logs():
    """日記検索API"""
    try:
        # パラメータを取得
        log_type = request.args.get('type', 'daily')
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        
        # 日付のバリデーション
        if not start_date_str or not end_date_str:
            return jsonify({
                'status': 'error',
                'message': '開始日と終了日を指定してください'
            }), 400
        
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': '無効な日付形式です'
            }), 400
        
        results = []
        total_count = 0
        is_truncated = False
        
        if log_type == 'daily':
            # デイリー: dateが開始日以上、終了日以下のものを日付の昇順で取得、最大10件
            # 総数をカウント
            total_count = DailyLog.query.filter(
                DailyLog.date >= start_date,
                DailyLog.date <= end_date
            ).count()
            
            logs = DailyLog.query.filter(
                DailyLog.date >= start_date,
                DailyLog.date <= end_date
            ).order_by(DailyLog.date.asc()).limit(10).all()
            
            for log in logs:
                results.append({
                    'id': log.id,
                    'date': log.date.isoformat(),
                    'date_jp': format_date_japanese(log.date) + f'（{get_weekday_japanese(log.date)}）',
                    'content': log.content if log.content else ''
                })
        
        elif log_type == 'weekly':
            # ウィークリー: start_dateが開始日以上、終了日以下のものを日付の昇順で取得、最大10件
            # 総数をカウント
            total_count = WeeklyLog.query.filter(
                WeeklyLog.start_date >= start_date,
                WeeklyLog.start_date <= end_date
            ).count()
            
            logs = WeeklyLog.query.filter(
                WeeklyLog.start_date >= start_date,
                WeeklyLog.start_date <= end_date
            ).order_by(WeeklyLog.start_date.asc()).limit(10).all()
            
            for log in logs:
                results.append({
                    'id': log.id,
                    'date': log.start_date.isoformat(),
                    'date_jp': format_weekly_date_japanese(log.start_date, log.week_number),
                    'content': log.content if log.content else ''
                })
        
        elif log_type == 'monthly':
            # マンスリー: first_dayが開始日以上、終了日以下のものを日付の昇順で取得、最大10件
            # 総数をカウント
            total_count = MonthlyLog.query.filter(
                MonthlyLog.first_day >= start_date,
                MonthlyLog.first_day <= end_date
            ).count()
            
            logs = MonthlyLog.query.filter(
                MonthlyLog.first_day >= start_date,
                MonthlyLog.first_day <= end_date
            ).order_by(MonthlyLog.first_day.asc()).limit(10).all()
            
            for log in logs:
                results.append({
                    'id': log.id,
                    'date': log.first_day.isoformat(),
                    'date_jp': f"{log.year}年{log.month}月",
                    'content': log.content if log.content else ''
                })
        
        elif log_type == 'yearly':
            # イヤリー: first_dayが開始日以上、終了日以下のものを日付の昇順で取得、最大10件
            # 総数をカウント
            total_count = YearlyLog.query.filter(
                YearlyLog.first_day >= start_date,
                YearlyLog.first_day <= end_date
            ).count()
            
            logs = YearlyLog.query.filter(
                YearlyLog.first_day >= start_date,
                YearlyLog.first_day <= end_date
            ).order_by(YearlyLog.first_day.asc()).limit(10).all()
            
            for log in logs:
                results.append({
                    'id': log.id,
                    'date': log.first_day.isoformat(),
                    'date_jp': f"{log.year}年",
                    'content': log.content if log.content else ''
                })
        
        else:
            return jsonify({
                'status': 'error',
                'message': '無効な種別です'
            }), 400
        
        # 10件を超える場合は切り捨てられたと判定
        is_truncated = total_count > 10
        
        return jsonify({
            'status': 'success',
            'results': results,
            'total_count': total_count,
            'is_truncated': is_truncated
        }), 200
        
    except Exception as e:
        app_logger.error(f"検索処理中にエラーが発生しました: {e}")
        return jsonify({
            'status': 'error',
            'message': '検索処理中にエラーが発生しました'
        }), 500


if __name__ == '__main__':
    # コマンドライン引数のパース
    parser = argparse.ArgumentParser(description='AI Board Batch Processor')
    parser.add_argument('--init', action='store_true', help='DBの初期化を行う')
    args = parser.parse_args()  

    # データベースの初期化
    init_database(app)
    
    # init引数が指定されている場合は全てのテーブルを削除
    if args.init:
        truncate_all_tables(app)
    
    # 初期データ投入
    seed_initial_data(app, pre_generate_years)
    
    # Flaskアプリケーションを起動
    app_logger.info("Flaskアプリケーションを起動しています...")
    app.run(debug=True, host='0.0.0.0', port=5000)

