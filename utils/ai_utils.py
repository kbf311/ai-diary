"""AI関連のユーティリティ関数を管理するモジュール"""
import os
import time

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

from config import GEMINI_API_KEY, LLM_MODEL_NAME
from constants import app, prompt
from utils.log_utils import setup_logger

# ロガーの設定
ai_logger = setup_logger(logger_name="ai", log_file_name="ai.log")

# 最後のリクエスト時刻を追跡
_last_request_time = None

def initialize_llm(model_name, temperature):
    os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY
    
    # モデルを初期化
    llm = ChatGoogleGenerativeAI(
        model=model_name,
        temperature=temperature,
    )
    
    return llm


def generate_text(prompt_text, model_name=None, temperature=0.7):
    """
    プロンプトを受け取り、AIの応答をテキストで返す
    
    Args:
        prompt_text: AIに送信するプロンプトテキスト
        model_name: 使用するモデル名（デフォルト: gemini-2.5-flash-lite）
        temperature: 温度パラメータ（デフォルト: 0.7）
    
    Returns:
        str: AIからの応答テキスト
    
    Raises:
        Exception: API呼び出しに失敗した場合
    """
    global _last_request_time
        
    # 前回のリクエストからの経過時間をチェック
    if _last_request_time is not None:
        elapsed_time = time.time() - _last_request_time
        if elapsed_time < app.REQUEST_INTERVAL_SECONDS:
            wait_time = app.REQUEST_INTERVAL_SECONDS - elapsed_time
            ai_logger.info(f"前回実行から{elapsed_time:.2f}秒しか経過していないため、{wait_time:.2f}秒待機します。")
            time.sleep(wait_time)
    
    # LLMを初期化
    if model_name is None: model_name = LLM_MODEL_NAME  # モデル名が指定されていない場合は、config.pyから取得
    llm = initialize_llm(model_name, temperature)
    
    # プロンプトをメッセージ形式に変換
    message = HumanMessage(content=prompt_text)
    
    # AIに送信して応答を取得
    response = llm.invoke([message])
    
    # リクエスト時刻を更新
    _last_request_time = time.time()
    
    # 応答テキストを返す
    return response.content