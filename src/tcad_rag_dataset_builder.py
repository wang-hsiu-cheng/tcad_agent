import os
import re
import sys
import json
import time
import hashlib
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Tuple
import numpy as np

from dotenv import load_dotenv
load_dotenv()

if "GOOGLE_API_KEY" in os.environ:
    del os.environ["GOOGLE_API_KEY"]

import fitz  # PyMuPDF
from google import genai
from google.genai import types
from google.genai.errors import APIError

from unstructured.partition.pdf import partition_pdf
from unstructured.documents.elements import Title, NarrativeText, Text, Table, Image, ListItem


# --- 3. 全域配置與初始化 ---
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

# 模型與快取配置
VISION_MODEL_NAME = "gemini-2.5-flash"
EMBEDDING_MODEL_NAME = "gemini-embedding-001"
CACHE_FILE = "./tcad_api_cache.json"

# --- 4. 輔助函數：快取、重試機制與文字清洗 ---
def load_cache() -> dict:
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_cache(cache_data: dict):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=4)

GLOBAL_CACHE = load_cache()
cache_lock = threading.Lock()

def call_gemini_with_retry(api_func, *args, **kwargs) -> Any:
    delays = [2, 4, 8]
    for i, delay in enumerate(delays):
        try:
            return api_func(*args, **kwargs)
        except APIError as e:
            if i == len(delays) - 1:
                raise RuntimeError(f"呼召 Gemini API 失敗，已達最大重試次數: {e}")
            print(f"   [API 頻率限制] 遇到錯誤 ({e})，等待 {delay} 秒後重試...")
            time.sleep(delay)

def clean_noise_text(text: str) -> str:
    """過濾手冊中的版權與頁碼雜訊"""
    text = re.sub(r"Silvaco\s+Inc\.\s+All\s+Rights\s+Reserved\.", "", text, flags=re.IGNORECASE)
    text = re.sub(r"Victory\s+(?:Process|Device)\s+User\'s\s+Manual.*?\n", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^\s*\d+\s*$", "", text, flags=re.M)
    text = re.sub(r"\s*-\s*\d+\s*-\s*$", "", text, flags=re.M)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# --- 5. 視覺語義化：調用 Gemini 轉譯圖表 ---
def transcribe_image_to_text_direct(image_data: Dict[str, Any]) -> str:
    """
    將提取的二進位圖片與上下文脈絡傳遞給 Gemini 將其轉譯為精準的技術 Markdown。
    """
    prompt = f"""
# ROLE
You are an expert TCAD Document Analyzer and Senior Semiconductor Device Engineer.

# TASK
Analyze the attached technical image extracted from a Silvaco TCAD user manual. 
Translate this visual diagram into a dense, highly accurate text-based description.

# CONTEXT OF THE IMAGE (Surrounding text on the same page):
{image_data['context_text']}

# OUTPUT FORMAT REQUIRED (Markdown)
1. **Device Type & Structure**: Identify the device structure (e.g., 2D Planar NMOS, FinFET, 3D Mesh).
2. **Key Physical Parameters**: Extract visible dimensions, material regions, and doping profiles.
3. **Axis & Data Values**: Extract X-axis and Y-axis labels, units, and representative data points.
4. **TCAD Command Context**: Explain which TCAD statement this image demonstrates.

Provide only Markdown.
"""
    # 封裝二進位多模態物件
    image_part = types.Part.from_bytes(
        data=image_data["bytes"],
        mime_type=f"image/{image_data['ext']}"
    )

    def run_inference():
        return client.models.generate_content(
            model=VISION_MODEL_NAME,
            contents=[image_part, prompt]
        )
    
    response = call_gemini_with_retry(run_inference)
    return response.text.strip()

def transcribe_image_to_text(image_data: Dict[str, Any]) -> str:
    """記憶體快取封裝層"""
    img_key = image_data["id"]
    if img_key in GLOBAL_CACHE:
        return GLOBAL_CACHE[img_key]
        
    desc = transcribe_image_to_text_direct(image_data)
    with cache_lock:
        GLOBAL_CACHE[img_key] = desc
        save_cache(GLOBAL_CACHE)
    return desc

def generate_batch_embeddings(texts: List[str], batch_size: int = 50) -> List[List[float]]:
    """
    將大量的文本列表分組 (Batch) 一次發送給 Gemini 進行向量化。
    能極大地防止觸發 429 錯誤，並提升 50 倍以上的運行效率。
    """
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i + batch_size]
        print(f"   正在批次發送向量請求 ({i} ~ {min(i + batch_size, len(texts))} / {len(texts)})...")
        
        def run_embedding_call():
            return client.models.embed_content(
                model=EMBEDDING_MODEL_NAME,
                contents=batch_texts
            )
            
        try:
            response = call_gemini_with_retry(run_embedding_call)
            if hasattr(response, 'embeddings') and response.embeddings:
                batch_vectors = [emb.values for emb in response.embeddings]
                all_embeddings.extend(batch_vectors)
            elif hasattr(response, 'embedding'):
                all_embeddings.append(response.embedding.values)
            else:
                raise ValueError("cannot analysis embedding response structure")
            time.sleep(2.0)
            
        except Exception as e:
            print(f"   vectorize this betch fail: {e}")
            all_embeddings.extend([[] for _ in range(len(batch_texts))])
            
    return all_embeddings

# --- 6. Unstructured 結構化解析核心 (平行優化版) ---
def parse_pdf_with_unstructured(pdf_path: str) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """使用 Unstructured 進行文件版面分析，精準擷取 Title, Table, Image (預先掃描平行版)"""
    print(f"using Unstructured extract PDF: {os.path.basename(pdf_path)}")
    temp_img_dir = tempfile.mkdtemp()
    
    elements = partition_pdf(
        filename=pdf_path,
        strategy="hi_res",
        infer_table_structure=True,
        extract_images_in_pdf=True,
        extract_image_block_output_dir=temp_img_dir
    )
    
    # === 預先順序掃描所有圖片，並進行平行多執行緒轉譯 ===
    image_tasks = []
    context_buffer = []
    for element in elements:
        element_text = str(element).strip()
        if not element_text:
            continue
        if isinstance(element, Title):
            context_buffer = []
        elif isinstance(element, Image):
            img_path = element.metadata.image_path
            if img_path and os.path.exists(img_path):
                try:
                    with open(img_path, "rb") as f:
                        img_bytes = f.read()
                    ext = os.path.splitext(img_path)[1][1:] or "png"
                    img_context = "\n".join(context_buffer[-5:])
                    img_id = f"img_{hashlib.md5(img_bytes).hexdigest()[:10]}"
                    image_tasks.append({
                        "id": img_id,
                        "bytes": img_bytes,
                        "ext": ext,
                        "context_text": img_context
                    })
                except Exception:
                    pass
        elif isinstance(element, (Text, NarrativeText, ListItem)):
            context_buffer.append(element_text)

    # 過濾出未被快取的任務
    uncached_tasks = [task for task in image_tasks if task["id"] not in GLOBAL_CACHE]
    if uncached_tasks:
        print(f"    detect {len(uncached_tasks)} uncache picture, use threading pool transcript...")
        # 設為 5 執行緒，在加速與頻率限制 (Rate Limit) 之間取得黃金平衡
        max_workers = min(5, len(uncached_tasks))
        
        def worker(task):
            try:
                desc = transcribe_image_to_text_direct(task)
                with cache_lock:
                    GLOBAL_CACHE[task["id"]] = desc
                    save_cache(GLOBAL_CACHE)
            except Exception as e:
                print(f"    table&picture transcript fail ({task['id']}): {e}")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            executor.map(worker, uncached_tasks)

    # 此時所有圖片都已被快取在 GLOBAL_CACHE 中，以下迴圈將在微秒內完成！
    parents = []
    children_from_layout = []
    
    current_parent_id = f"p_init_{hashlib.md5(pdf_path.encode()).hexdigest()[:8]}"
    current_parent_title = "Introduction"
    current_parent_content = []
    context_buffer = [] 

    def save_current_parent():
        if current_parent_content:
            parents.append({
                "id": current_parent_id,
                "title": current_parent_title,
                "content": clean_noise_text("\n".join(current_parent_content)),
                "source": os.path.basename(pdf_path)
            })

    for element in elements:
        element_text = str(element).strip()
        if not element_text:
            continue

        if isinstance(element, Title):
            save_current_parent()
            parent_hash = hashlib.md5(f"{pdf_path}_{element_text}".encode()).hexdigest()[:10]
            current_parent_id = f"p_{parent_hash}"
            current_parent_title = element_text
            current_parent_content = [f"=== {element_text} ==="]
            context_buffer = []

        elif isinstance(element, Table):
            html_table = element.metadata.text_as_html if element.metadata.text_as_html else element_text
            current_parent_content.append(f"\n[Table Data]:\n{html_table}\n")
            child_id = f"c_table_{hashlib.md5(html_table.encode()).hexdigest()[:8]}"
            children_from_layout.append({
                "id": child_id,
                "parent_id": current_parent_id,
                "text": f"Table in section '{current_parent_title}':\n{html_table}",
                "type": "table"
            })

        elif isinstance(element, Image):
            img_path = element.metadata.image_path
            if img_path and os.path.exists(img_path):
                try:
                    with open(img_path, "rb") as f:
                        img_bytes = f.read()
                    img_id = f"img_{hashlib.md5(img_bytes).hexdigest()[:10]}"
                    
                    # 讀取高畫質快取
                    semantic_desc = transcribe_image_to_text({
                        "id": img_id,
                        "bytes": img_bytes,
                        "ext": os.path.splitext(img_path)[1][1:] or "png",
                        "context_text": ""
                    })
                    
                    child_id = f"c_{img_id}"
                    children_from_layout.append({
                        "id": child_id,
                        "parent_id": current_parent_id,
                        "text": f"Visual Diagram in '{current_parent_title}':\n{semantic_desc}",
                        "type": "image_description"
                    })
                    current_parent_content.append(f"\n[Image Description]:\n{semantic_desc}\n")
                except Exception as e:
                    print(f"   skip current picture: {e}")

        elif isinstance(element, (Text, NarrativeText, ListItem)):
            current_parent_content.append(element_text)
            context_buffer.append(element_text)

    save_current_parent()
    print(f" extract finish! extract {len(parents)} parents topic and {len(children_from_layout)} tables/pictures")
    return parents, children_from_layout


# --- 7. 主控流水線 ---
def build_hierarchical_rag_dataset(pdf_folder_path: str, output_json_path: str):
    print("=========================================")
    print(" TCAD RAG dataset builder pipeline ")
    print("=========================================")
    
    if not os.path.exists(pdf_folder_path):
        print(f"找不到來源資料夾: {pdf_folder_path}")
        return

    all_parents = []
    all_children = []
    
    for file_name in os.listdir(pdf_folder_path):
        if not file_name.lower().endswith(".pdf"):
            continue
            
        pdf_path = os.path.join(pdf_folder_path, file_name)
        parents, layout_children = parse_pdf_with_unstructured(pdf_path)
        
        all_parents.extend(parents)
        all_children.extend(layout_children)
        
        # 對純文字切分 Paragraph Child
        for p in parents:
            paragraphs = p["content"].split("\n\n")
            for idx, para in enumerate(paragraphs):
                para_clean = para.strip()
                if len(para_clean) < 30 or "[Table Data]:" in para_clean or "[Image Description]:" in para_clean:
                    continue 
                all_children.append({
                    "id": f"c_{p['id']}_para_{idx}",
                    "parent_id": p["id"],
                    "text": f"Context Title: {p['title']}\nContent: {para_clean}",
                    "type": "text"
                })

    # 批次向量化整合
    print(f"\n 正在為 {len(all_children)} 個子節點建立向量特徵 (採用高效批次引擎)...")
    
    all_texts = [child["text"] for child in all_children]
    all_vectors = generate_batch_embeddings(all_texts, batch_size=50)
    
    success_count = 0
    for child, vector in zip(all_children, all_vectors):
        child["vector"] = vector
        if vector and len(vector) > 0:
            success_count += 1

    print("正在整合資料庫並寫入本地 JSON...")
    rag_dataset = {
        "parents": {p["id"]: {"title": p["title"], "content": p["content"], "source": p["source"]} for p in all_parents},
        "children": [c for c in all_children if c.get("vector") and len(c.get("vector")) > 0]
    }
    
    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(rag_dataset, f, ensure_ascii=False, indent=4)
        
    print("=========================================")
    print(f"RAG 資料庫建置成功！")
    print(f"   - 總父節點 (Parent Chunks): {len(all_parents)}")
    print(f"   - 總向量子節點 (Child Chunks): {success_count}/{len(all_children)}")
    print(f"   - 產出路徑: {output_json_path}")
    print("=========================================")

if __name__ == "__main__":
    PDF_FOLDER = "./raw_docs"
    
    # 執行指示：確認要產出的檔名（例如 deckbuild_rag_dataset.json）
    OUTPUT_JSON = "./victoryprocess_rag_dataset.json"
    build_hierarchical_rag_dataset(PDF_FOLDER, OUTPUT_JSON)