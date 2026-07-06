from flask_sqlalchemy import SQLAlchemy

# 共有のSQLAlchemyインスタンス
db = SQLAlchemy()

# 各モデルをインポート（循環インポートを避けるため、最後にインポート）
from models.daily_log import DailyLog
from models.weekly_log import WeeklyLog
from models.monthly_log import MonthlyLog
from models.yearly_log import YearlyLog
from models.prompt import Prompt
from models.system_config import SystemConfig

__all__ = [
    'db',
    'DailyLog',
    'WeeklyLog',
    'MonthlyLog',
    'YearlyLog',
    'Prompt',
    'SystemConfig',
]

