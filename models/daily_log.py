from datetime import date
from models import db


class DailyLog(db.Model):
    """デイリー日記テーブル"""
    __tablename__ = 'daily_logs'
    __table_args__ = (
        {'comment': 'デイリー日記テーブル'},
    )

    id = db.Column(db.Integer, primary_key=True, comment='固有ID')
    date = db.Column(db.Date, unique=True, nullable=False, index=True, comment='日付（YYYY-MM-DD）')
    content = db.Column(db.Text, comment='日記の内容')
    is_completed = db.Column(db.Boolean, default=False, index=True, comment='入力完了フラグ（アラート消込用）')
    created_at = db.Column(db.DateTime, server_default=db.func.now(), comment='作成日時')
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now(), comment='更新日時')

    def __repr__(self):
        return f'<DailyLog {self.date}>'

