import re
from typing import Dict, Any
from google.genai import types

def extract_code_block(text: str, default_fallback: str = "") -> str:
    """
    安全提取 TCAD (.in) 腳本。
    透過字串拼接避開程式碼中的連續三反引號，以防止渲染或解析衝突。
    """
    # 使用安全拼接方式建立 Regex Pattern，防止 markdown 渲染與程式碼解析衝突
    triple_backticks = "```"
    pattern = r" " + triple_backticks + r"(?:in|tcad|fortran|bash)?\n(.*?)\n" + triple_backticks
    pattern = pattern.strip() # 去除開頭空白
    
    blocks = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
    
    if blocks:
        # 優先找尋含有 TCAD 核心模擬引擎宣告的區塊
        for b in blocks:
            content = b.strip()
            if any(keyword in content.lower() for keyword in ["go victoryprocess", "go victorydevice", "go victoryvisual"]):
                return content
        # 若皆未符合，則預設回傳最後一個程式碼區塊
        return blocks[-1].strip()
    
    # 備用機制：若模型未使用標籤，則直接抓取 go 指令之後的所有行
    lines = text.strip().split('\n')
    for i, line in enumerate(lines):
        if line.strip().lower().startswith("go "):
            return "\n".join(lines[i:]).strip()
            
    return text.strip() if text.strip() else default_fallback

class DebugSpecialistAgent:
    """
    錯誤診斷與自動修復智能體 (Debug Specialist Agent)。
    當 DeckBuild 模擬失敗時，負責深入剖析編譯器日誌，並針對出錯的代碼進行手術刀式修正（自動自癒）。
    """
    def __init__(self, client):
        """
        初始化 Debug Specialist。
        
        Args:
            client: 已建立的 google-genai Client 實例。
        """
        self.client = client
        # 除錯與推理任務建議採用推理與程式碼能力最優的 pro 模型
        self.model_name = "gemini-3.5-flash"

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        print("🤖 [Debug Specialist]: 正在分析 Log 報錯並自動修復腳本...")
        
        feedback = state.get("feedback", "無可用錯誤日誌。")
        current_code = state.get("current_code", "")
        rag_context = state.get("rag_context", "無可用參考資料。")
        
        # 安全宣告系統提示詞，避免在內文中直接出現 markdown 程式碼塊標記
        backtick_tag = "```in"
        system_instruction = (
            "You are a senior Silvaco TCAD script debugging and physical parameter correction expert.\n"
            "Please carefully read the user-provided ERROR LOG to identify the specific causes and line numbers of syntax errors or convergence failures.\n"
            "Compare the CURRENT CODE with the RAG REFERENCE, and correct the erroneous or problematic commands.\n"
            f"Output ONLY the fully corrected pure code, which must be wrapped inside the {backtick_tag} ... block, without any extra text explanation or non-code descriptions."
        )
        
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.1  # 降低隨機度，確保語法修復具備高度確定性
        )
        
        prompt = f"""
# CURRENT CODE WITH ERRORS:
{current_code}

# DECKBUILD ERROR LOG (FEEDBACK):
{feedback}

# RAG REFERENCE (HELPFUL MANUAL SECTIONS):
{rag_context}

# TASK:
Analyze the log, identify the buggy line or non-converging parameters, fix them, and output the FULL corrected .in script.
"""
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )
            
            # 使用安全的高相容性提取器抓取修正後的代碼
            fixed_code = extract_code_block(response.text, default_fallback=current_code)
            
            # 寫入本地副本備份，方便即時檢視
            with open("task_current.in", "w", encoding="utf-8") as f:
                f.write(fixed_code)
                
            return {
                "current_code": fixed_code,
                "iteration": state.get("iteration", 0) + 1,
                "status": "code_written"
            }
            
        except Exception as e:
            print(f" [Debug Specialist] 腳本除錯與修復失敗: {e}")
            return {
                "current_code": current_code,
                "iteration": state.get("iteration", 0) + 1,
                "status": "error",
                "feedback": f"DebugSpecialistAgent 執行時發生異常: {str(e)}"
            }