import re
from typing import Dict, Any
from google.genai import types

def extract_code_block(text: str, default_fallback: str = "") -> str:
    """
    安全提取 TCAD (.in) 腳本。
    透過字串拼接避開程式碼中的連續三反引號，以防止渲染或解析衝突。
    """
    # 使用安全拼接方式建立 Regex Pattern，防止 markdown 渲染衝突
    triple_backticks = "```"
    pattern = r" " + triple_backticks + r"(?:in|tcad|fortran|bash)?\n(.*?)\n" + triple_backticks
    pattern = pattern.strip() # 去除開頭空白
    
    blocks = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
    
    if blocks:
        # 優先找尋含有 TCAD 核心模擬引擎宣告的區塊
        for b in blocks:
            content = b.strip()
            if any(keyword in content.lower() for keyword in ["go victory", "go athena", "go atlas", "go spice"]):
                return content
        # 若皆未符合，則預設回傳最後一個程式碼區塊
        return blocks[-1].strip()
    
    # 備用機制：若模型未使用標籤，則直接抓取 go 指令之後的所有行
    lines = text.strip().split('\n')
    for i, line in enumerate(lines):
        if line.strip().lower().startswith("go "):
            return "\n".join(lines[i:]).strip()
            
    return text.strip() if text.strip() else default_fallback


class TCADDeveloperAgent:
    """
    TCAD 腳本編寫開發者智能體 (TCAD Developer Agent)。
    負責整合 RAG 檢索得到的手冊內容與物理規格要求，生成高精準度的模擬程式。
    """
    def __init__(self, client):
        """
        初始化 TCAD Developer。
        
        Args:
            client: 已建立的 google-genai Client 實例。
        """
        self.client = client
        self.model_name = "gemini-3.5-flash"

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        print(" [TCAD Developer]: 正在根據 RAG 參考資料編寫模擬腳本...")
        
        # 安全宣告系統提示詞，避免在內文中直接出現 markdown 程式碼塊標記
        backtick_tag = "```in"
        system_instruction = (
            "You are a senior Silvaco TCAD script development expert.\n"
            "Please write strictly based on the official manual syntax provided in the REFERENCE. Fabricating non-existent parameters and commands is strictly prohibited.\n"
            f"Output ONLY pure code, and you must wrap the code inside the {backtick_tag} ... block, with no additional explanations."
        )
        
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.1  # 降低隨機度，確保語法精準
        )
        
        prompt = f"""
# SIMULATION GOAL (USER SPECIFICATION):
{state['parsed_task']}

# MANUAL REFERENCE (RETRIEVED FROM RAG):
{state['rag_context']}

# TASK:
Please write the complete Silvaco TCAD .in script based on the goal and reference manuals.
Make sure your output follows the execution flow (e.g., 'go victoryprocess' first, then 'go victorydevice').
"""
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )
            
            # 使用高相容性提取器清洗與抓取代碼
            code = extract_code_block(response.text)
            
            # 寫入本地副本備份，方便即時檢視
            with open("task_current.in", "w", encoding="utf-8") as f:
                f.write(code)
                
            return {
                "current_code": code,
                "status": "code_written"
            }
            
        except Exception as e:
            print(f" [TCAD Developer] 腳本生成失敗: {e}")
            return {
                "current_code": state.get("current_code", ""),
                "status": "error",
                "feedback": f"TCADDeveloperAgent 執行時發生異常: {str(e)}"
            }