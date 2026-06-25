import os
import sys
from langgraph.graph import StateGraph, END

# 1. import env setting classes & agents
from src.tcad_config import TCADEnvironment
from src.tcad_state import TCADState
from src.tcad_agents import (
    TaskAnalyzerAgent,
    RAGRetrieverAgent,
    TCADDeveloperAgent,
    ExecutorAgent,
    DebugSpecialistAgent,
    PlottingAgent,
    ReportGeneratorAgent
)

# 2. import rag query class
try:
    from src.tcad_rag import AdvancedHierarchicalRAG
except ImportError:
    print(" 錯誤：找不到 tcad_rag.py, 請確認檔案與 main.py 在同一個目錄下。")
    sys.exit(1)

# --- 1. init api env ---
env = TCADEnvironment()
client = env.get_client()

# --- 2. init rag dataset ---
DATASET_PATHS = [
    "./deckbuild_rag_dataset.json",
    "./victoryprocess_rag_dataset.json",
    "./victorydevice_rag_dataset.json",
    "./victoryvisual_rag_dataset.json"
]

selected_db = None
for db in DATASET_PATHS:
    if os.path.exists(db):
        selected_db = db
        break

if selected_db:
    print(f" initializing RAG dataset (selecting: {selected_db})...")
    rag_engine = AdvancedHierarchicalRAG(selected_db)
else:
    print(" warning: cannot find local RAG JSON dataset, operating without dataset.")
    rag_engine = None


# --- 3. init every Agents ---
analyzer_agent = TaskAnalyzerAgent(client)
retriever_agent = RAGRetrieverAgent(client, rag_engine)
developer_agent = TCADDeveloperAgent(client)
executor_agent = ExecutorAgent(target_host="ws43")
debugger_agent = DebugSpecialistAgent(client)
plotter_agent = PlottingAgent(client)
reporter_agent = ReportGeneratorAgent(client)


# --- 4. Graph Routing Logic ---

def post_executor_router(state: TCADState):
    """
    Executor 運作後的條件分支流程：
    1. 若模擬失敗且未達 5 次重試上限：到 debug_specialist 進行除錯。
    2. 若成功或達除錯上限，檢查 output_prefs:
       - 若需要繪圖且 plot_code 尚未生成：到 plotting_agent。
       - 若需要分析報告且 final_report 尚未生成：到 report_generator。
       - 否則直接結束。
    """
    # check if require debugging
    if state["status"] == "error" and state["iteration"] < 5:
        return "debug"
    # check if require plotting
    prefs = state.get("output_prefs", [])
    if "plot" in prefs and not state.get("plot_code"):
        return "plot"
    # check if require needed
    if "report" in prefs and not state.get("final_report"):
        return "report"
    return "end"


def post_plot_router(state: TCADState):
    """
    Plotting Agent 執行後的條件分支路由：
    - 檢查是否還需要生成分析報告，否則結束。
    """
    prefs = state.get("output_prefs", [])
    if "report" in prefs and not state.get("final_report"):
        return "report"
    return "end"

# --- 5. Build Graph ---
workflow = StateGraph(TCADState)

# 註冊所有 Agent 物件為工作節點 (由於實作了 __call__ 方法，可以直接作為 callable 傳入)
workflow.add_node("task_analyzer", analyzer_agent)
workflow.add_node("rag_retriever", retriever_agent)
workflow.add_node("script_writer", developer_agent)
workflow.add_node("executor", executor_agent)
workflow.add_node("debug_specialist", debugger_agent)
workflow.add_node("plotting_agent", plotter_agent)
workflow.add_node("report_generator", reporter_agent)

# 設定基礎線性工作邊 (Edges)
workflow.set_entry_point("task_analyzer")
workflow.add_edge("task_analyzer", "rag_retriever")
workflow.add_edge("rag_retriever", "script_writer")
workflow.add_edge("script_writer", "executor")

# 註冊執行器後的分支路由
workflow.add_conditional_edges(
    "executor",
    post_executor_router,
    {
        "debug": "debug_specialist",
        "plot": "plotting_agent",
        "report": "report_generator",
        "end": END
    }
)

# 除錯完成後，重新交給執行器驗證: Self-Healing Loop
workflow.add_edge("debug_specialist", "executor")

# 註冊繪圖專家後的分支
workflow.add_conditional_edges(
    "plotting_agent",
    post_plot_router,
    {
        "report": "report_generator",
        "end": END
    }
)

# 報告生成完畢，任務結束
workflow.add_edge("report_generator", END)

# 編譯 LangGraph 流程圖
app = workflow.compile()


# --- 6. system startup ---
if __name__ == "__main__":
    print("\n=======================================================")
    print("啟動 TCAD Multi-Agent 物件化協作系統")
    print("=======================================================\n")
    
    # 模擬使用者輸入的要求 (包含製程規格、量測、繪圖與報告偏好)
    user_request = """
    模擬一個 28nm Gate-last NMOS 的製程，並輸出其 Id-Vg 曲線。
    自動寫好提取特徵的圖表代碼，並在最後給我一份詳細的分析報告。
    """
    
    # 建立初始狀態
    initial_state = {
        "user_input": user_request.strip(),
        "parsed_task": "",
        "output_prefs": [],
        "rag_context": "",
        "current_code": "",
        "plot_code": "",
        "iteration": 0,
        "status": "init",
        "feedback": "",
        "final_report": ""
    }
    
    # 開始啟動協作網絡運算
    final_state = app.invoke(initial_state)
    
    print("\n=======================================================")
    print("任務全部完成！")
    print(f" 總除錯次數: {final_state['iteration']}")
    print(f" 最終狀態: {final_state['status']}")
    
    if final_state.get('current_code'):
        print(f" 最終 TCAD 腳本已匯出並存為 'task_current.in'")
    if final_state.get('plot_code'):
        print(f" 已生成 Victory Visual/Extract 數據腳本")
    if final_state.get('final_report'):
        print(f" 分析報告已產出並存為 'final_report.md'")
    print("=======================================================\n")