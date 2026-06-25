import os
import sys
try:
    from dotenv import load_dotenv
    from google import genai
except ImportError:
    print("plz install new SDK: pip install google-genai python-dotenv")
    sys.exit(1)


class TCADEnvironment:
    """
    API 呼叫與環境初始化封裝物件。
    負責清理環境變數衝突，並提供安全、純淨的 Gemini Client。
    """
    def __init__(self):
        self._clean_environment()
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.client = self._initialize_client()

    def _clean_environment(self):
        """強效清洗雙金鑰衝突"""
        if 'dotenv' in sys.modules:
            load_dotenv()
            
        if "GOOGLE_API_KEY" in os.environ:
            del os.environ["GOOGLE_API_KEY"]

    def _initialize_client(self):
        """初始化新版 SDK 用戶端"""
        try:
            if self.api_key:
                return genai.Client(api_key=self.api_key)
            else:
                return genai.Client()
        except Exception as e:
            print(f"⚠️ 初始化 Gemini 用戶端失敗: {e}")
            return None

    def get_client(self):
        """取得初始化完成的 Client 實例"""
        if not self.client:
            raise RuntimeError("Gemini Client 未成功初始化，請檢查 API 金鑰。")
        return self.client