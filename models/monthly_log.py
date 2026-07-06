from datetime import date
from models import db


class MonthlyLog(db.Model):
    """マンスリー日記テーブル"""
    __tablename__ = 'monthly_logs'
    __table_args__ = (
        {'comment': 'マンスリー日記テーブル'},
    )

    id = db.Column(db.Integer, primary_key=True, comment='固有ID')
    first_day = db.Column(db.Date, unique=True, nullable=False, index=True, comment='その月の初日（例: 2026-01-01）')
    year = db.Column(db.Integer, nullable=False, index=True, comment='対象年') 
    month = db.Column(db.Integer, nullable=False, index=True, comment='対象月 (1-12)') 
    content = db.Column(db.Text, comment='要約文章')
    is_completed = db.Column(db.Boolean, default=False, index=True, comment='完了フラグ')
    created_at = db.Column(db.DateTime, server_default=db.func.now(), comment='作成日時')
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now(), comment='更新日時')

    def __repr__(self):
        return f'<MonthlyLog {self.year}-{self.month:02d}>'

