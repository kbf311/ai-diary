from models import db


class Prompt(db.Model):
    """プロンプトテンプレートテーブル"""
    __tablename__ = 'prompts'
    __table_args__ = (
        {'comment': 'プロンプトテンプレートテーブル'},
    )

    id = db.Column(db.Integer, primary_key=True, comment='固有ID')
    log_type = db.Column(db.String(20), unique=True, nullable=False, comment='ログタイプ（daily, weekly, monthly, yearly）')
    template = db.Column(db.Text, comment='プロンプトの本文')
    created_at = db.Column(db.DateTime, server_default=db.func.now(), comment='作成日時')
    updated_at = db.Column(db.DateTime, server_default=db.func.now(), onupdate=db.func.now(), comment='更新日時')

    def __repr__(self):
        return f'<Prompt {self.log_type}>'

