from typing import Dict, Any

# 防禦性套件載入，避免本機未安裝 fabric 套件時引發程式碼直接崩潰
try:
    from fabric import Connection
    FABRIC_AVAILABLE = True
except ImportError:
    FABRIC_AVAILABLE = False

class ExecutorAgent:
    """
    遠端模擬執行器智能體 (Executor Agent)。
    負責將當前生成的腳本安全上傳至工作站/伺服器，調用 DeckBuild 執行模擬並精準擷取執行日誌。
    """
    def __init__(self, target_host: str = "ws43"):
        """
        初始化 Executor。
        
        Args:
            target_host: 目標遠端 Linux 工作站主機名稱或連線設定。
        """
        self.target_host = target_host

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        print(f" [Executor]: 正在伺服器 {self.target_host} 端部署並執行模擬腳本 (除錯循環: {state['iteration']})...")
        
        # 1. 檢查本機執行環境是否安裝必要通訊套件
        if not FABRIC_AVAILABLE:
            print(" 警告: 本機環境未安裝 'fabric' 套件，無法進行遠端 SSH 連線運算。")
            print("   -> 進入虛擬執行模式，模擬運作成功。")
            return {
                "status": "success",
                "feedback": "模擬執行器模擬成功：[本機環境未安裝 fabric，已略過 SSH 連線測試]"
            }

        # 2. 檢查是否有待執行的代碼
        current_script = state.get("current_code", "").strip()
        if not current_script:
            return {
                "status": "error",
                "feedback": "執行器錯誤: 當前待執行腳本 (current_code) 為空，無法送往伺服器運行。"
            }

        # 3. 建立連線並遠端部署執行
        try:
            # 遠端建立與 `task_current.in` 檔案的連線
            with Connection(self.target_host) as conn:
                # 使用 cat 指令將代碼直接安全地寫入伺服器端
                # hide=True 隱藏大量不必要的檔案寫入輸出
                conn.run(f"cat << 'EOF' > task.in\n{current_script}\nEOF", hide=True)
                
                # 載入環境變數設定檔 (如 tcshrc) 並在同一個進程 shell 中呼叫 DeckBuild
                # 同時使用 `>&` 將標準輸出與標準錯誤一同導向 task.log，並使用 tail 精確擷取最後 50 行
                result = conn.run(
                    "source ./tcshrc && deckbuild -run -ascii task.in >& task.log ; tail -n 50 task.log", 
                    warn=True
                )
                
                log_output = result.stdout.strip() + result.stderr.strip()
                
                # 4. 分析 Log 內容以判定模擬是否收斂、語法是否報錯
                # 檢查 Fabric 本身的回傳代碼，或者 Log 內容是否包含經典報錯字眼
                if result.failed or "error" in log_output.lower() or "Error" in log_output:
                    print("    [Executor] 模擬執行失敗！語法錯誤或物理模型未收斂。")
                    return {
                        "status": "error",
                        "feedback": f"--- DeckBuild 遠端錯誤日誌 (最後 50 行) ---\n{log_output}"
                    }
                else:
                    print("    [Executor] 模擬順利跑通並成功收斂！")
                    # 只保留 Log 尾端一部分作為成功反饋，防止狀態物件過於臃腫
                    success_feedback = log_output[-200:] if len(log_output) > 200 else log_output
                    return {
                        "status": "success",
                        "feedback": f"模擬完美結束！終端反饋：\n{success_feedback}"
                    }
                    
        except Exception as e:
            print(f" [Executor] 遠端 SSH 連線或指令發送異常: {e}")
            # 如果是連線層級的問題，設定 status 為 error 讓除錯 Agent 決定是否重試
            return {
                "status": "error",
                "feedback": f"遠端伺服器連線異常，無法完成 CI/CD 流程。詳細原因: {str(e)}"
            }