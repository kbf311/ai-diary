from datetime import date
from models import db


class WeeklyLog(db.Model):
    """ウィークリー日記テーブル"""
    __tablename__ = 'weekly_logs'
    __table_args__ = (
        {'comment': 'ウィークリー日記テーブル'},
    )

    id = db.Column(db.Integer, primary_key=True, comment='固有ID')
    start_date = db.Column(db.Date, unique=True, nullable=False, index=True, comment='週の開始日（月曜日）')
    content = db.Column(db.Text, comment='要約文章')
    is_completed = db.Column(db.Boolean, default=False, index=True, comment='完了フラグ')
    year = db.Column(db.Integer, index=True, comment='統計用の年')
    month = db.Column(db.Integer, index=True, comment='統計用の月')
    week_number = db.Column(db.Integer, index=True, comment='統計用の第何週か（1～5）')
    created_at = db.Column(db.DateTime, server_default=db.func.now(), comment='作成日時')
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now(), comment='更新日時')

    def __repr__(self):
        return f'<WeeklyLog {self.start_date}>'

