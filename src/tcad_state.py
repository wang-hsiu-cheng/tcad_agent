from typing import TypedDict, List

class TCADState(TypedDict):
    """
    LangGraph 多智能體網路中流通的全域狀態定義。
    """
    user_input: str              # 使用者原始輸入 (需求或檔案路徑)
    parsed_task: str             # Agent 解析後的具體技術目標
    output_prefs: List[str]      # 輸出偏好 (例如: ["script", "plot", "report"])
    rag_context: str             # RAG 檢索回來的參考手冊
    current_code: str            # 當前編寫的 .in 腳本
    plot_code: str               # 繪圖/數據萃取腳本
    iteration: int               # 除錯迴圈計數
    status: str                  # 狀態追蹤
    feedback: str                # 執行器回傳的 Log 或報錯
    final_report: str            # 最終生成的分析報告