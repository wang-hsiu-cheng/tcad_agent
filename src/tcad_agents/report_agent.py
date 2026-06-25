import re
from typing import Dict, Any
from google.genai import types

class ReportGeneratorAgent:
    """
    最終分析報告生成智能體 (Report Generator Agent)。
    負責彙整協作網絡中的所有核心資訊（目標、代碼、Log 反饋、繪圖命令），
    撰寫一份具備極高學術與工程價值的繁體中文 Markdown TCAD 模擬分析報告。
    """
    def __init__(self, client):
        """
        初始化 ReportGeneratorAgent。
        
        Args:
            client: 已建立的 google-genai Client 實例。
        """
        self.client = client
        # 生成深度分析報告建議使用推理能力最強的 pro 模型
        self.model_name = "gemini-2.5-flash"

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        print(" [Report Generator]: 正在彙整所有資訊，製作最終分析報告...")
        
        parsed_task = state.get("parsed_task", "")
        feedback = state.get("feedback", "無可用終端日誌。")
        current_code = state.get("current_code", "無可用模擬程式。")
        rag_context = state.get("rag_context", "無檢索手冊資料。")
        plot_code = state.get("plot_code", "無可用繪圖指令。")
        
        prompt = f"""
Please write a professional, rigorous, and well-structured Markdown TCAD analysis report in Traditional Chinese based on the following complete simulation process and information.

# 1. TASK OBJECTIVE:
{parsed_task}

# 2. DECKBUILD LOG (Terminal Execution & Convergence Feedback):
{feedback[:1000]}

# 3. TCAD CODE (The final fully-executed simulation script):
{current_code}

# 4. RAG REFERENCE (Official manual knowledge base retrieved via RAG):
{rag_context[:800]}

# 5. VISUALIZATION PLAN (Victory Visual data and curve export plan):
{plot_code}

# REPORT WRITING GUIDELINES (Strictly use professional Markdown format and Traditional Chinese):
Please include the following high-level engineering sections:
- **Section 1: Task and Specification Summary**: Analyze the simulation goals, key technology nodes (e.g., 28nm), or electrical device specification requirements.
- **Section 2: Mesh Generation and Process/Device Structure Design**: Analyze the mesh settings and the process step flow (including etching, deposition, and doping diffusion logic in VictoryProcess).
- **Section 3: Physical Modeling and Numerical Method Analysis**: Explain the mobility, recombination, and other physical models configured in VictoryDevice, as well as their numerical convergence methods.
- **Section 4: Simulation Execution and Convergence Assessment**: Interpret the final execution log, analyze whether it converged perfectly, and describe the electrical characteristics.
- **Section 5: Data and Visualization Export Guide**: Explain in detail how to use the Victory Visual `{plot_code}` commands to inspect and export 2D structures and characteristic curves.

Please construct the discussion from the perspective of a senior semiconductor device physicist and process engineer, providing in-depth, meticulous, and academically valuable analysis.
"""
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            report_text = response.text.strip()
            
            # 儲存到本地 Markdown 檔案
            with open("final_report.md", "w", encoding="utf-8") as f:
                f.write(report_text)
                
            return {
                "final_report": report_text,
                "status": "report_done"
            }
        except Exception as e:
            print(f" [Report Generator] 報告生成失敗: {e}")
            return {
                "final_report": "",
                "status": "error",
                "feedback": f"ReportGeneratorAgent 執行時發生異常: {str(e)}"
            }