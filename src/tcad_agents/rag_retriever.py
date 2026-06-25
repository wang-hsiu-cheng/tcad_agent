from typing import Dict, Any

class RAGRetrieverAgent:
    """
    知識庫檢索智能體 (RAG Retriever Agent)。
    負責將具體的技術任務轉化為高相關性的英文關鍵字，並調用本地 RAG 引擎搜尋相關手冊語法。
    """
    def __init__(self, client, rag_engine):
        """
        初始化 RAG Retriever。
        
        Args:
            client: 已建立的 google-genai Client 實例
            rag_engine: 已初始化的 AdvancedHierarchicalRAG 實例
        """
        self.client = client
        self.rag_engine = rag_engine
        self.model_name = "gemini-2.5-flash"

    def __call__(self, state: Dict[str, Any]) -> Dict[str, Any]:
        print(" [RAG Retriever]: 正在向知識庫檢索相關語法與設定...")
        
        if not self.rag_engine:
            return {
                "rag_context": " 無法連線至本地 RAG 知識庫，將以無參考手冊模式運作。", 
                "status": "rag_done"
            }
            
        # 讓模型自動提煉最佳的檢索關鍵字句子
        keyword_prompt = (
            f"I want to implement the following TCAD objective: {state['parsed_task']}."
            "Please provide an English keyword phrase that is most suitable for searching in the Silvaco manuals "
            "(e.g., 'Id-Vg curve extraction models'). Output ONLY the phrase itself without any extra explanation."
        )
        
        try:
            keyword_resp = self.client.models.generate_content(
                model=self.model_name, 
                contents=keyword_prompt
            )
            search_query = keyword_resp.text.strip()
            print(f"    產生的搜尋關鍵字: {search_query}")
            
            # 呼叫傳入的 RAG 檢索引擎進行 Parent-Child 檢索
            rag_result = self.rag_engine.retrieve(search_query, top_k_parents=3)
            return {
                "rag_context": rag_result, 
                "status": "rag_done"
            }
            
        except Exception as e:
            print(f" 關鍵字生成或檢索失敗 ({e})")
            return {
                "rag_context": " 檢索過程發生異常，將以無參考手冊模式運作。", 
                "status": "rag_done"
            }