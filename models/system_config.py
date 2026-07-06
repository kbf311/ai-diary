from models import db


class SystemConfig(db.Model):
    """システム設定テーブル"""
    __tablename__ = 'system_config'
    __table_args__ = (
        {'comment': 'システム設定テーブル'},
    )

    key = db.Column(db.String(50), primary_key=True, index=True, comment="設定キー (例: 'start_date')")
    value = db.Column(db.String(255), comment='設定値')

    def __repr__(self):
        return f'<SystemConfig {self.key}={self.value}>'

