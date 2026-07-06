"""ログ関連のユーティリティ関数を管理するモジュール"""
import os
import logging
import logging.handlers
from pathlib import Path

def setup_logger(
    logger_name,
    log_file_name,
    log_dir=None,
    max_bytes=1 * 1024 * 1024,  # デフォルト1MB
    backup_count=5,
    formatter_pattern='%(asctime)s\t%(levelname)s\t%(message)s',
    log_level=logging.INFO
):
    """
    ローテーション機能付きのロガーをセットアップする
    
    Args:
        logger_name (str): ロガーの名前
        log_dir (str or Path, optional): ログディレクトリのパス。Noneの場合はデフォルトの場所を使用
        log_file_name (str): ログファイルの名前
        max_bytes (int): ログローテーションのサイズ上限（バイト）
        backup_count (int): 保持するバックアップファイルの数
        formatter_pattern (str): ログのフォーマットパターン
        log_level (int): ロギングレベル（logging.DEBUG, logging.INFO など）
        
    Returns:
        logging.Logger: 設定済みのロガーオブジェクト
    """
    # ログディレクトリの設定
    if log_dir is None:
        # デフォルトのログディレクトリ（logs）
        log_dir = Path(os.path.dirname(os.path.dirname(__file__))) / 'logs'
    elif isinstance(log_dir, str):
        log_dir = Path(log_dir)
    
    # ディレクトリが存在しない場合は作成
    log_dir.mkdir(exist_ok=True, parents=True)
    
    # ログファイルのパス
    log_file = log_dir / log_file_name
    
    # ロガーの設定
    logger = logging.getLogger(logger_name)
    logger.setLevel(log_level)
    
    # 親ロガーへの伝播を無効化（重複出力を防ぐ）
    logger.propagate = False
    
    # 既存のハンドラをクリア
    if logger.handlers:
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)
            handler.close()  # ファイルなどのリソースを確実に閉じる
    
    # ローテーティングファイルハンドラを追加
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    
    # フォーマッタの設定
    formatter = logging.Formatter(formatter_pattern)
    file_handler.setFormatter(formatter)
    
    # 標準出力ハンドラを追加
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # ハンドラをロガーに追加
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
