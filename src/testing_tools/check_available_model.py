import os
import sys

# --- 1. 導入最新版 SDK ---
try:
    from google import genai
    from google.genai.errors import APIError
except ImportError:
    print(" 錯誤: 找不到 google-genai 套件。")
    print("請先在終端機執行: pip install google-genai")
    sys.exit(1)


def diagnostic_suite():
    print("==================================================")
    print(" Gemini 可用向量模型 (Embedding) 快速檢索工具 ")
    print("==================================================")

    # 1. 檢查系統環境變數
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print(" 偵測狀態: 未設定環境變數 GEMINI_API_KEY")
        print(" 請在終端機執行此指令設定（以 Linux/macOS 為例）：")
        print("   export GEMINI_API_KEY='您的金鑰'")
        print("   (Windows 則使用: set GEMINI_API_KEY=您的金鑰)")
        return
    else:
        # 遮蔽處理，保護隱私
        masked_key = f"{api_key[:6]}...{api_key[-6:]}"
        print(f" 偵測狀態: 已讀取 API 金鑰 ({masked_key})")

    # 2. 初始化客戶端
    try:
        client = genai.Client()
        print(" 連線狀態: SDK 客戶端初始化成功")
    except Exception as e:
        print(f" 連線狀態: 客戶端初始化失敗: {e}")
        return

    # 3. 僅進行模型清單檢索 (不消耗 Token 的 Metadata 查詢)
    print("\n---  正在檢索支援 Embedding 的可用模型清單 ---")
    try:
        found_embedding_models = []
        
        # 獲取官方模型清單並篩選
        for m in client.models.list():
            is_embedding = False
            
            # 判斷方式 1: 檢查 supported_methods
            if hasattr(m, 'supported_methods') and m.supported_methods:
                if any("embedContent" in method for method in m.supported_methods):
                    is_embedding = True
                    
            # 判斷方式 2: 比對名稱關鍵字 (雙重防禦屬性變更)
            if "embed" in m.name.lower():
                is_embedding = True
                
            if is_embedding:
                model_display_name = m.name.replace("models/", "")
                found_embedding_models.append(model_display_name)
                print(f"    支援向量模型: {model_display_name}")

        print("\n==================================================")
        print(" 檢索結論報告")
        print("==================================================")
        if found_embedding_models:
            print(f" 成功！您的 API 金鑰目前可以使用以下 {len(found_embedding_models)} 個向量模型：")
            for name in sorted(set(found_embedding_models)):
                print(f"    {name}")
            print("\n 提示: 建議優先使用 'text-embedding-004' 作為預設向量模型。")
        else:
            print(" 警告：您的 API 金鑰可用的模型清單中未偵測到任何向量模型。")
            print(" 請檢查您的帳號計費方案或 API Key 權限設定。")
        print("==================================================")

    except APIError as e:
        print(f" 呼叫 API 失敗！錯誤代碼: {e.code} | 訊息: {e.message}")
    except Exception as e:
        print(f" 執行發生未預期異常: {e}")


if __name__ == "__main__":
    diagnostic_suite()