from datetime import date
from models import db


class YearlyLog(db.Model):
    """年日記テーブル"""
    __tablename__ = 'yearly_logs'
    __table_args__ = (
        {'comment': '年次ログテーブル'},
    )

    id = db.Column(db.Integer, primary_key=True, comment='固有ID')
    first_day = db.Column(db.Date, unique=True, nullable=False, index=True, comment='その年の元日（例: 2026-01-01）')
    year = db.Column(db.Integer, unique=True, nullable=False, index=True, comment='対象年')
    content = db.Column(db.Text, comment='要約文章')
    is_completed = db.Column(db.Boolean, default=False, index=True, comment='完了フラグ')
    created_at = db.Column(db.DateTime, server_default=db.func.now(), comment='作成日時')
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now(), comment='更新日時')

    def __repr__(self):
        return f'<YearlyLog {self.year}>'

