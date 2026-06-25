import os
import sys
import json
import numpy as np
from typing import List, Dict, Any, Tuple, Optional, Union

# --- 1. 嘗試載入本地 .env 設定 (防禦性載入) ---
try:
    from dotenv import load_dotenv
    load_dotenv()  # 自動讀取同目錄下的 .env 檔案
    if "GOOGLE_API_KEY" in os.environ:
        del os.environ["GOOGLE_API_KEY"]
except ImportError:
    # 若無安裝 python-dotenv 則忽略，直接讀取系統環境變數
    pass

# --- 2. 防禦性套件載入 ---
try:
    from google import genai
    from google.genai.errors import APIError
except ImportError:
    print("plz exec: pip install google-genai numpy")
    sys.exit(1)


# --- 3. 生產級進階 RAG 檢索引擎 ---
class AdvancedHierarchicalRAG:
    def __init__(self, db_paths: Union[str, List[str]]):
        """
        初始化 RAG 系統，載入多個本地 JSON 資料集並建立具有過濾功能的記憶體向量索引。
        """
        if isinstance(db_paths, str):
            self.db_paths = [db_paths]
        else:
            self.db_paths = db_paths

        self.parents: Dict[str, Any] = {}
        self.children: List[Dict[str, Any]] = []
        
        # 僅讀取 GEMINI_API_KEY 環境變數
        api_key = os.getenv("GEMINI_API_KEY")
        
        # 初始化全新 SDK Client
        try:
            if api_key:
                # 顯式傳入金鑰，防禦環境變數未成功載入至進程進程的問題
                self.client = genai.Client(api_key=api_key)
            else:
                self.client = genai.Client()
        except Exception as e:
            print(f"init Gemini user fail: {e}")
            self.client = None
            
        # 掃描可用模型候選清單
        self.available_embedding_models = self._scan_embedding_models()
        
        # 載入所有指定的資料庫並自動進行合併
        self._load_dataset()
        self._build_vector_index()

    def _scan_embedding_models(self) -> List[str]:
        """
        動態掃描 API 權限內可用的模型，不須嘗試添加 models/ 前綴。
        已針對用戶金鑰優化，優先且僅預設使用 gemini-embedding-001。
        """
        if not self.client:
            return ["gemini-embedding-001"]
            
        print("scanning API Key available models...")
        candidate_models = []
        try:
            # 取得官方回傳的可用清單
            for m in self.client.models.list():
                # 安全獲取屬性，防禦因 SDK 版本變動導致 AttributeError
                supported_methods = getattr(m, 'supported_generation_methods', []) or []
                if 'embedContent' in supported_methods:
                    candidate_models.append(m.name)
                    
        except Exception as e:
            print(f"cannot fetch online model list ({e})")

        # 針對您的帳號進行暴力補齊：不再使用 text-embedding-004，100% 綁定相容性最高的模型
        fallback_list = ["gemini-embedding-001"]
        
        # 合併並去重，保持原順序
        final_list = list(dict.fromkeys(candidate_models + fallback_list))
        print(f"scan finish!use backup model: {final_list}...")
        return final_list

    def _load_dataset(self):
        """讀取多個結構化 JSON 資料集並進行自動合併與去重"""
        loaded_count = 0
        for path in self.db_paths:
            if not os.path.exists(path):
                print(f"warn: cannot find json '{path}', skipping")
                continue
            
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                parents_data = data.get("parents", {})
                children_data = data.get("children", [])
                
                # 合併父節點 (Key 具備唯一性，會自動覆蓋與去重)
                self.parents.update(parents_data)
                # 合併子節點列表
                self.children.extend(children_data)
                
                print(f"find json: {path} (parent: {len(parents_data)}, child: {len(children_data)})")
                loaded_count += 1
            except Exception as e:
                print(f"loading '{path}' with error: {e}")

        if loaded_count == 0:
            print("error: 任何指定的資料集檔案皆無法成功載入！")
            sys.exit(1)
            
        print(f"所有資料集載入完成！合併後總父節點: {len(self.parents)} 個，總子節點: {len(self.children)} 個")

    def _build_vector_index(self):
        """將子節點轉換為 NumPy 矩陣，並進行 L2 正規化以利高速點積計算"""
        valid_children = []
        vectors_list = []

        for child in self.children:
            vec = child.get("vector", [])
            if vec and len(vec) > 0:
                vec_np = np.array(vec, dtype=np.float32)
                norm = np.linalg.norm(vec_np)
                if norm > 0:
                    normalized_vec = vec_np / norm
                    vectors_list.append(normalized_vec)
                    valid_children.append(child)

        self.children = valid_children
        self.vector_matrix = np.vstack(vectors_list) if vectors_list else None
        print(f"向量矩陣建立完成，有效子節點數量: {len(self.children)}")

    def _get_query_embedding(self, query: str) -> np.ndarray:
        """
        將查詢字句即時轉換為正規化向量。優先嘗試掃描到的模型，若均失效則強制直連 gemini-embedding-001。
        """
        if not self.client:
            raise RuntimeError("未設定 GEMINI_API_KEY，且無法初始化 Client，無法呼叫 Embedding 服務。")
            
        # 依序嘗試候選名單中的模型 (此時 gemini-embedding-001 已在最前面)
        for model_name in self.available_embedding_models:
            try:
                response = self.client.models.embed_content(
                    model=model_name,
                    contents=query[:8000]
                )
                
                # 解析結構
                if hasattr(response, 'embeddings') and response.embeddings:
                    query_vec = np.array(response.embeddings[0].values, dtype=np.float32)
                elif hasattr(response, 'embedding'):
                    query_vec = np.array(response.embedding.values, dtype=np.float32)
                else:
                    continue
                    
                norm = np.linalg.norm(query_vec)
                return (query_vec / norm) if norm > 0 else query_vec
                
            except Exception:
                # 靜默嘗試名單中下一個模型
                continue
                
        try:
            response = self.client.models.embed_content(
                model="gemini-embedding-001",
                contents=query[:8000]
            )
            if hasattr(response, 'embeddings') and response.embeddings:
                query_vec = np.array(response.embeddings[0].values, dtype=np.float32)
            elif hasattr(response, 'embedding'):
                query_vec = np.array(response.embedding.values, dtype=np.float32)
            else:
                raise ValueError("無法解析 gemini-embedding-001 結構。")
                
            norm = np.linalg.norm(query_vec)
            return (query_vec / norm) if norm > 0 else query_vec
        except Exception as e:
            raise RuntimeError(f"所有向量模型均遭拒絕，包括核心模型 gemini-embedding-001 也無法使用。錯誤訊息: {e}")

    def retrieve(self, query: str, top_k_parents: int = 2, doc_filter: Optional[str] = None) -> str:
        """進階檢索接口：支援根據 document 來源進行篩選"""
        if self.vector_matrix is None or len(self.children) == 0:
            return "warn: no data in database"

        try:
            query_vector = self._get_query_embedding(query)
            similarities = np.dot(self.vector_matrix, query_vector)
            
            # 套用 Metadata 篩選器
            if doc_filter:
                filter_mask = np.zeros(len(self.children), dtype=bool)
                for i, child in enumerate(self.children):
                    parent_id = child["parent_id"]
                    parent_info = self.parents.get(parent_id, {})
                    source_name = parent_info.get("source", "").lower()
                    if doc_filter.lower() in source_name:
                        filter_mask[i] = True
                similarities = np.where(filter_mask, similarities, -1.0)

            # 排序與去重
            sorted_indices = np.argsort(similarities)[::-1]
            retrieved_parents = []
            seen_parent_ids = set()
            
            print(f"\n (Query: '{query}'):")
            match_count = 0
            
            for idx in sorted_indices:
                score = similarities[idx]
                if score < 0:
                    break
                    
                child = self.children[idx]
                p_id = child["parent_id"]
                
                if match_count < 3:
                    print(f"    -> [相似度 {score:.4f}] 子節點 {child['id']} (類型: {child['type']})")
                    match_count += 1
                
                if p_id not in seen_parent_ids:
                    seen_parent_ids.add(p_id)
                    parent_data = self.parents.get(p_id)
                    if parent_data:
                        retrieved_parents.append(parent_data)
                        
                if len(retrieved_parents) >= top_k_parents:
                    break
            
            if not retrieved_parents:
                return "cannot find data"

            formatted_context = []
            for p in retrieved_parents:
                formatted_context.append(
                    f"=========================================\n"
                    f"REFERENCE CHAPTER: {p['title']}\n"
                    f"SOURCE: {p['source']}\n"
                    f"=========================================\n"
                    f"{p['content']}"
                )
            return "\n\n".join(formatted_context)

        except Exception as e:
            return f"query error: {e}"


# --- 3. 互動式測試環境 ---
if __name__ == "__main__":
    # 多個資料集路徑預設定義
    DATASET_PATHS = [
        "./victoryprocess_rag_dataset.json",
        "./victorydevice_rag_dataset.json",
        "./victoryvisual_rag_dataset.json",
        "./deckbuild_rag_dataset.json"
    ]
    
    # 自動偵測本地實際存在的資料集路徑
    existing_paths = [p for p in DATASET_PATHS if os.path.exists(p)]
    
    if not existing_paths:
        print(f"error: 在本地找不到任何預期的 TCAD RAG 資料集！")
        print(f"預計檢查路徑: {', '.join(DATASET_PATHS)}")
        sys.exit(1)
        
    # 初始化 RAG 引擎，直接傳入所有實際存在的檔案路徑
    rag = AdvancedHierarchicalRAG(existing_paths)
    
    print("\n ready!")
    print("=====================================================================")
    
    while True:
        try:
            user_query = input("\n enter query: ").strip()
            if not user_query:
                continue
            if user_query.lower() == 'exit':
                break
                
            # 執行檢索 (預設進行跨資料庫全域檢索)
            # 您也可以手動加上過濾功能，例如 rag.retrieve(user_query, doc_filter="victoryprocess")
            result = rag.retrieve(user_query, top_k_parents=2)
            
            print("\n------------------ [ RAG Output ] ------------------")
            print(result)
            print("---------------------------------------------------------------")
            
        except KeyboardInterrupt:
            print("\n break")
            break
        except Exception as e:
            print(f"\n error: {e}")