"""日時関連のユーティリティ関数"""
from datetime import datetime, timedelta, timezone, date


# 日本標準時（JST）のタイムゾーン
JST = timezone(timedelta(hours=9))


def now_jst() -> datetime:
    """
    現在の日本時間を取得する
    
    Returns:
        datetime: 日本時間の現在時刻
    """
    return datetime.now(JST)


def get_monday_of_week(target_date: date) -> date:
    """
    指定日付が含まれる週の月曜日を取得
    
    Args:
        target_date: 対象となる日付
        
    Returns:
        date: その週の月曜日の日付
    """
    # weekday(): 月曜日=0, 日曜日=6
    days_since_monday = target_date.weekday()
    return target_date - timedelta(days=days_since_monday)


def get_week_number_in_month(target_date: date) -> int:
    """
    指定日付がその月の第何週かを計算（月曜日始まり）
    その月に含まれる日付が含まれる週を第1週とする
    
    Args:
        target_date: 対象となる日付
        
    Returns:
        int: その月の第何週か（1から始まる）
    """
    # その月の1日を取得
    first_day_of_month = date(target_date.year, target_date.month, 1)
    
    # その月の1日が含まれる週の月曜日を取得
    first_monday = get_monday_of_week(first_day_of_month)
    
    # その月の1日が含まれる週の月曜日が前月の場合、次の週を第1週とする
    if first_monday.month != target_date.month:
        first_monday += timedelta(days=7)
    
    # 指定日付が含まれる週の月曜日を取得
    target_monday = get_monday_of_week(target_date)
    
    # 週の差を計算
    days_diff = (target_monday - first_monday).days
    week_number = (days_diff // 7) + 1
    
    return week_number
