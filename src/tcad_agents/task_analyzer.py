import re
import json
from typing import Dict, Any, List

class TaskAnalyzerAgent:
    """
    任務解析與意圖識別智能體 (Task Analyzer Agent)。
    負責分析使用者輸入的原始需求，並釐清技術模擬目標與輸出偏好。
    """
    def __init__(self, client):
        """
        初始化 Task Analyzer。
        
        Args:
            client: 已建立的 google-genai Client 實例
        """
        self.client = client
        self.model_name = "gemini-2.5-flash"

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        print("🤖 [Task Analyzer]: 正在解析使用者需求與輸出偏好...")
        
        prompt = f"""
Please analyze the following user's TCAD simulation requirements:
"{state['user_input']}"

Please return the response in JSON format (strictly prohibited to include any markdown blocks like ```json or ```, directly output the raw JSON string):
{{
    "technical_goal": "Convert the user's requirements into a specific TCAD simulation objective description",
    "requires_plot": true/false (whether plotting, curves, or data outputs are required),
    "requires_report": true/false (whether a final textual analysis report is required)
}}
        """
        
        try:
            response = self.client.models.generate_content(
                model=self.model_name, 
                contents=prompt
            )
            
            # 清理 JSON 字串中可能被模型夾帶的 Markdown 標籤
            clean_json = re.sub(r'```json|```', '', response.text).strip()
            parsed = json.loads(clean_json)
            
            # 建立輸出偏好清單 (預設必定包含 script 腳本撰寫)
            prefs = ["script"]
            if parsed.get("requires_plot"):
                prefs.append("plot")
            if parsed.get("requires_report"):
                prefs.append("report")
                
            return {
                "parsed_task": parsed.get("technical_goal", state['user_input']),
                "output_prefs": prefs,
                "status": "task_analyzed"
            }
            
        except Exception as e:
            print(f"⚠️ 解析意圖失敗，將使用預設設定模式運作 ({e})")
            # 發生異常時的安全降級機制
            return {
                "parsed_task": state['user_input'], 
                "output_prefs": ["script", "report"], 
                "status": "task_analyzed"
            }