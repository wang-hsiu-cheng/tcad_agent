FROM python:3.11-slim

RUN apt update && apt install -y --no-install-recommends \
    # 安裝 SSH 客戶端與基礎遠端通訊工具
    openssh-client \
    # OpenCV 與圖像解析所需之系統底層圖形庫
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    # unstructured 所需之檔案類型偵測庫 (重要遺漏！)
    libmagic-dev \
    # OCR 引擎與 PDF 深度處理相依軟體
    tesseract-ocr \
    tesseract-ocr-eng \
    libtesseract-dev \
    poppler-utils \
    # 編譯 C/C++ 原始碼所需之基礎工具
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 安裝 Python 套件
RUN pip install --upgrade pip && pip install --no-cache-dir \
    # 核心 Workflow 與通訊套件
    langgraph \
    fabric \
    python-dotenv \
    # 數據與矩陣運算套件
    numpy \
    pandas \
    google-genai \
    langchain-google-genai \
    # PDF 深度版面結構解析與視覺語義化套件 (補齊遺漏)
    unstructured[pdf] \
    PyMuPDF \
    docling \
    marker-pdf

# 建立 SSH 目錄並設定正確權限
RUN mkdir -p /root/.ssh && chmod 700 /root/.ssh

COPY . .

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]

CMD ["/bin/bash", "-ic"]