"""データベース初期化とログ生成関連のユーティリティ"""
from datetime import date, timedelta
from flask import Flask

from models import db, DailyLog, WeeklyLog, MonthlyLog, YearlyLog, Prompt, SystemConfig
from utils.datetime_utils import now_jst, get_monday_of_week, get_week_number_in_month
from utils.log_utils import setup_logger
from utils.constants import SEED_PROMPTS


# ロガーの設定
app_logger = setup_logger(logger_name="db_seeder", log_file_name="app.log")


def get_start_date():
    """システム開始日を取得（なければ今日を設定）"""
    start_date_config = SystemConfig.query.filter_by(key='start_date').first()
    if start_date_config:
        return date.fromisoformat(start_date_config.value)
    else:
        today = now_jst().date()
        start_date_config = SystemConfig(key='start_date', value=today.isoformat())
        db.session.add(start_date_config)
        db.session.commit()
        return today


def generate_daily_logs(start_date, end_date):
    """デイリーログの枠を生成"""
    # 既存の日付を取得
    existing_dates = {log.date for log in DailyLog.query.filter(
        DailyLog.date >= start_date,
        DailyLog.date <= end_date
    ).all()}
    
    # 不足している日付を生成
    current_date = start_date
    new_logs = []
    while current_date <= end_date:
        if current_date not in existing_dates:
            new_logs.append(DailyLog(date=current_date, is_completed=False))
        current_date += timedelta(days=1)
    
    if new_logs:
        db.session.bulk_save_objects(new_logs)
        db.session.commit()
        app_logger.info(f"デイリーログ: {len(new_logs)}件を生成しました。")


def generate_weekly_logs(start_date, end_date):
    """ウィークリーログの枠を生成"""
    # 開始日が含まれる週の月曜日を取得
    current_monday = get_monday_of_week(start_date)
    
    # 既存の週の開始日を取得
    existing_start_dates = {log.start_date for log in WeeklyLog.query.filter(
        WeeklyLog.start_date >= current_monday,
        WeeklyLog.start_date <= end_date
    ).all()}
    
    # 不足している週を生成
    new_logs = []
    while current_monday <= end_date:
        if current_monday not in existing_start_dates:
            year = current_monday.year
            month = current_monday.month
            week_number = get_week_number_in_month(current_monday)
            new_logs.append(WeeklyLog(
                start_date=current_monday,
                year=year,
                month=month,
                week_number=week_number,
                is_completed=False
            ))
        current_monday += timedelta(days=7)
    
    if new_logs:
        db.session.bulk_save_objects(new_logs)
        db.session.commit()
        app_logger.info(f"ウィークリーログ: {len(new_logs)}件を生成しました。")


def generate_monthly_logs(start_date, end_date):
    """マンスリーログの枠を生成"""
    # 開始日の月初日を取得
    current_first_day = date(start_date.year, start_date.month, 1)
    
    # 既存の月初日を取得
    existing_first_days = {log.first_day for log in MonthlyLog.query.filter(
        MonthlyLog.first_day >= current_first_day,
        MonthlyLog.first_day <= end_date
    ).all()}
    
    # 不足している月を生成
    new_logs = []
    while current_first_day <= end_date:
        if current_first_day not in existing_first_days:
            new_logs.append(MonthlyLog(
                first_day=current_first_day,
                year=current_first_day.year,
                month=current_first_day.month,
                is_completed=False
            ))
        
        # 翌月の月初日を計算
        if current_first_day.month == 12:
            current_first_day = date(current_first_day.year + 1, 1, 1)
        else:
            current_first_day = date(current_first_day.year, current_first_day.month + 1, 1)
    
    if new_logs:
        db.session.bulk_save_objects(new_logs)
        db.session.commit()
        app_logger.info(f"マンスリーログ: {len(new_logs)}件を生成しました。")


def generate_yearly_logs(start_date, end_date):
    """イヤリーログの枠を生成"""
    # 開始日の年初日を取得
    current_first_day = date(start_date.year, 1, 1)
    
    # 既存の年初日を取得
    existing_first_days = {log.first_day for log in YearlyLog.query.filter(
        YearlyLog.first_day >= current_first_day,
        YearlyLog.first_day <= end_date
    ).all()}
    
    # 不足している年を生成
    new_logs = []
    while current_first_day.year <= end_date.year:
        if current_first_day not in existing_first_days:
            new_logs.append(YearlyLog(
                first_day=current_first_day,
                year=current_first_day.year,
                is_completed=False
            ))
        current_first_day = date(current_first_day.year + 1, 1, 1)
    
    if new_logs:
        db.session.bulk_save_objects(new_logs)
        db.session.commit()
        app_logger.info(f"イヤリーログ: {len(new_logs)}件を生成しました。")


def seed_system_config(today: date):
    """システム設定テーブルに初期データを投入"""
    # システム稼働日を設定（既に存在する場合はスキップ）
    start_date_config = SystemConfig.query.filter_by(key='start_date').first()
    if not start_date_config:
        start_date_config = SystemConfig(key='start_date', value=today.isoformat())
        db.session.add(start_date_config)
        db.session.commit()
        app_logger.info(f"システム稼働日を設定しました: {today.isoformat()}")
    else:
        app_logger.info(f"システム稼働日は既に設定されています: {start_date_config.value}")


def seed_prompts():
    """プロンプトテーブルにサンプルプロンプトを投入"""
    # 既存のプロンプトを取得
    existing_log_types = {prompt.log_type for prompt in Prompt.query.all()}
    
    # 不足しているプロンプトを追加
    new_prompts = []
    for log_type, template in SEED_PROMPTS.items():
        if log_type not in existing_log_types:
            new_prompts.append(Prompt(log_type=log_type, template=template))
    
    if new_prompts:
        db.session.bulk_save_objects(new_prompts)
        db.session.commit()
        app_logger.info(f"プロンプト: {len(new_prompts)}件を生成しました。")
    else:
        app_logger.info("プロンプトは既に全て設定されています。")


def truncate_all_tables(app: Flask):
    """全てのテーブルのデータを削除（truncate）"""
    with app.app_context():
        try:
            # 外部キー制約を考慮して、依存関係の順序で削除
            # ログテーブルを先に削除
            DailyLog.query.delete()
            WeeklyLog.query.delete()
            MonthlyLog.query.delete()
            YearlyLog.query.delete()
            
            # その他のテーブル
            Prompt.query.delete()
            SystemConfig.query.delete()
            
            db.session.commit()
            app_logger.info("全てのテーブルのデータを削除しました。")
        except Exception as e:
            db.session.rollback()
            app_logger.error(f"テーブルのデータ削除中にエラーが発生しました: {e}")
            raise


def init_database(app: Flask):
    """データベースに接続し、テーブルが存在しない場合は作成する"""
    with app.app_context():
        # すべてのテーブルを作成（存在しない場合のみ）
        db.create_all()
        app_logger.info("データベースの初期化が完了しました。")


def seed_initial_data(app: Flask, pre_generate_years: int):
    """初期データ（日・週・月・年の枠）を投入"""
    with app.app_context():
        
        # システム開始日を取得
        start_date = get_start_date()
        
        # 現在日時を取得
        today = now_jst().date()
        
        # 終了日を計算（現在日 + 先行生成年数）
        end_date = date(today.year + pre_generate_years, 12, 31)
        
        app_logger.info(f"初期データ投入を開始します...")
        app_logger.info(f"開始日: {start_date}, 終了日: {end_date}")
        
        # 各ログの枠を生成
        generate_daily_logs(start_date, end_date)
        generate_weekly_logs(start_date, end_date)
        generate_monthly_logs(start_date, end_date)
        generate_yearly_logs(start_date, end_date)
        
        # システム設定を投入
        seed_system_config(today)
        
        # プロンプトを投入
        seed_prompts()
        
        app_logger.info("初期データ投入が完了しました。")

