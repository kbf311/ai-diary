"""日記データのエクスポート処理を行うモジュール"""
import os
from datetime import date, timedelta
from typing import Dict, Any, Optional, Tuple

from models.daily_log import DailyLog
from models.weekly_log import WeeklyLog
from models.monthly_log import MonthlyLog
from models.yearly_log import YearlyLog
from utils.datetime_utils import (
    format_date_japanese,
    format_weekly_date_japanese,
    get_weekday_japanese,
)
from utils.log_utils import setup_logger

logger = setup_logger(logger_name="app", log_file_name="app.log")


def _format_content(content: Optional[str]) -> str:
    """テキストの改行統一およびHTMLエスケープを行う"""
    if not content:
        return '（内容なし）'
    
    # 改行コードを統一（\r\n → \n）
    formatted = content.replace('\r\n', '\n').replace('\r', '\n')
    # HTMLエスケープ
    formatted = (
        formatted.replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
        .replace('"', '&quot;')
        .replace("'", '&#39;')
    )
    return formatted


def generate_export_html() -> Tuple[str, int]:
    """
    日記データを元にエクスポート用静的HTMLコンテンツを生成する
    
    Returns:
        tuple[str, int]: (HTML文字列, エクスポート対象デイリーログ件数)
    """
    # is_completed=Trueのデイリーログをdate昇順で取得
    daily_logs = (
        DailyLog.query.filter(DailyLog.is_completed == True)
        .order_by(DailyLog.date.asc())
        .all()
    )

    # HTMLコンテンツを生成
    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AIダイアリー</title>
    <link rel="stylesheet" href="static/css/tailwind.css">
</head>
<body class="bg-white">
    <!-- ヘッダー -->
    <header class="bg-blue-600 border-b border-blue-700 sticky top-0 z-50">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between items-center h-16">
                <div class="flex items-center">
                    <h1 class="text-xl font-semibold text-white">AIダイアリー</h1>
                </div>
            </div>
        </div>
    </header>

    <!-- メインコンテンツ -->
    <main class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div class="space-y-4">
            <div class="space-y-4">
"""

    if daily_logs:
        # 日記開始前の年次ログを挿入
        first_diary_date = daily_logs[0].date
        first_diary_year = first_diary_date.year

        # 日記開始年より前の年次ログを取得（年が古い順）
        pre_diary_yearly_logs = (
            YearlyLog.query.filter(YearlyLog.year < first_diary_year)
            .order_by(YearlyLog.year.asc())
            .all()
        )

        # 日記開始前の年次ログを出力
        for yearly_log in pre_diary_yearly_logs:
            if yearly_log.content:
                yearly_content = _format_content(yearly_log.content)
                html_content += f"""                <div class="bg-white border border-gray-300 rounded-lg overflow-hidden">
                    <div class="bg-purple-300 px-4 py-2">
                        <div class="text-sm font-medium text-purple-900">【年次】{yearly_log.year}年</div>
                    </div>
                    <div class="p-6">
                        <div class="text-gray-900 whitespace-pre-wrap">{yearly_content}</div>
                    </div>
                </div>
"""

        # 各ログをカードとして追加
        for log in daily_logs:
            current_date = log.date

            # 年次ログの挿入（1月1日の場合）
            if current_date.month == 1 and current_date.day == 1:
                yearly_log = YearlyLog.query.filter_by(first_day=current_date).first()
                if yearly_log and yearly_log.content:
                    yearly_content = _format_content(yearly_log.content)
                    html_content += f"""                <div class="bg-white border border-gray-300 rounded-lg overflow-hidden">
                    <div class="bg-purple-300 px-4 py-2">
                        <div class="text-sm font-medium text-purple-900">【年次】{yearly_log.year}年</div>
                    </div>
                    <div class="p-6">
                        <div class="text-gray-900 whitespace-pre-wrap">{yearly_content}</div>
                    </div>
                </div>
"""

            # 週次ログの挿入（月曜日の場合）
            if current_date.weekday() == 0:  # 0 = 月曜日
                weekly_log = WeeklyLog.query.filter_by(
                    start_date=current_date - timedelta(days=7)
                ).first()
                if weekly_log and weekly_log.content:
                    weekly_content = _format_content(weekly_log.content)
                    week_title = format_weekly_date_japanese(
                        weekly_log.start_date, weekly_log.week_number
                    )
                    html_content += f"""                <div class="bg-white border border-gray-300 rounded-lg overflow-hidden">
                    <div class="bg-blue-300 px-4 py-2">
                        <div class="text-sm font-medium text-blue-900">【週次】{week_title}</div>
                    </div>
                    <div class="p-6">
                        <div class="text-gray-900 whitespace-pre-wrap">{weekly_content}</div>
                    </div>
                </div>
"""
                    # 月次ログの挿入（その月の最終週次ログの場合）
                    # 自分より後ろの週次ログが同じ月に存在しないかチェック
                    is_last_weekly_of_month = not WeeklyLog.query.filter(
                        WeeklyLog.year == weekly_log.year,
                        WeeklyLog.month == weekly_log.month,
                        WeeklyLog.start_date > weekly_log.start_date,
                    ).first()
                    if is_last_weekly_of_month:
                        month_first_day = date(weekly_log.year, weekly_log.month, 1)
                        monthly_log = MonthlyLog.query.filter_by(
                            first_day=month_first_day
                        ).first()
                        if monthly_log and monthly_log.content:
                            monthly_content = _format_content(monthly_log.content)
                            html_content += f"""                <div class="bg-white border border-gray-300 rounded-lg overflow-hidden">
                    <div class="bg-green-300 px-4 py-2">
                        <div class="text-sm font-medium text-green-900">【月次】{monthly_log.year}年{monthly_log.month}月</div>
                    </div>
                    <div class="p-6">
                        <div class="text-gray-900 whitespace-pre-wrap">{monthly_content}</div>
                    </div>
                </div>
"""

            # デイリーログの挿入
            date_jp = format_date_japanese(current_date)
            weekday = get_weekday_japanese(current_date)
            content = _format_content(log.content)

            html_content += f"""                <div class="bg-white border border-gray-300 rounded-lg overflow-hidden">
                    <div class="bg-gray-200 px-4 py-2">
                        <div class="text-sm font-medium text-gray-700">{date_jp}（{weekday}）</div>
                    </div>
                    <div class="p-6">
                        <div class="text-gray-900 whitespace-pre-wrap">{content}</div>
                    </div>
                </div>
"""
    else:
        html_content += """                <div class="text-center py-8 text-gray-500">
                    エクスポートするデータがありません
                </div>
"""

    html_content += """            </div>
        </div>
    </main>
</body>
</html>"""

    return html_content, len(daily_logs)


def export_diary_to_html(export_path: Optional[str] = None) -> Dict[str, Any]:
    """
    日記データをエクスポートして静的HTMLファイルを保存する

    Args:
        export_path: 保存先のファイルパス。Noneの場合はプロジェクトルートの export.html

    Returns:
        dict: {'count': エクスポート件数, 'path': 保存先絶対パス}
    """
    if export_path is None:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        export_path = os.path.join(project_root, 'export.html')

    html_content, count = generate_export_html()

    with open(export_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    logger.info(f"日記データをエクスポートしました: {export_path}")

    return {
        'count': count,
        'path': export_path
    }
