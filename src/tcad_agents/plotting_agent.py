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

class PlottingAgent:
    """
    數據繪圖與影像導出智能體 (Plotting Agent)。
    負責在模擬成功後，自動生成使用 Victory Visual (victoryvisual) 命令列，
    導出元件結構圖、電位分佈、能帶圖或電性特徵曲線 (Id-Vg, C-V) 影像檔。
    """
    def __init__(self, client):
        """
        初始化 PlottingAgent。
        
        Args:
            client: 已建立的 google-genai Client 實例。
        """
        self.client = client
        self.model_name = "gemini-2.5-flash"

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        print(" [Plotting Agent]: 正在生成 Victory Visual 數據繪圖與影像導出指令...")
        
        parsed_task = state.get("parsed_task", "")
        current_code = state.get("current_code", "")
        
        # 安全宣告系統提示詞，避免在內文中直接出現 markdown 程式碼塊標記
        backtick_tag = "```tcad"
        system_instruction = (
            "You are a senior Silvaco TCAD data visualization and plotting command expert.\n"
            "Based on the simulation output results, please write commands using the Victory Visual (victoryvisual) command-line tool to export images.\n"
            "For example, to export a process structure PNG image:\n"
            "victoryvisual -file task_process.str -png structure_output.png\n"
            "Or, in conjunction with the exported log file, plot a 1D characteristic curve image:\n"
            "victoryvisual -file task_device.log -png idvg_curve.png\n"
            f"Please output ONLY the code, and you must wrap the command code inside the {backtick_tag} ... block without any extra explanations or descriptions in English or Chinese."
        )
        
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=0.2
        )
        
        prompt = f"""
# SIMULATION OBJECTIVE (USER TASK):
{parsed_task}

# RECENT RUN TCAD SCRIPT CONTEXT:
{current_code[-600:]}

# TASK:
Develop the shell script or victoryvisual command strings to export the appropriate figures.
"""
        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )
            plot_code = extract_code_block(response.text)
            return {
                "plot_code": plot_code,
                "status": "plot_done"
            }
        except Exception as e:
            print(f" [Plotting Agent] 繪圖腳本生成失敗: {e}")
            return {
                "plot_code": "",
                "status": "error",
                "feedback": f"PlottingAgent 執行時發生異常: {str(e)}"
            }