import streamlit as st
import google.generativeai as genai
import pandas as pd
from io import StringIO, BytesIO

# --- 設定頁面 ---
st.set_page_config(page_title="轉檔神器", page_icon="📝")

# --- 讀取 API Key ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("⚠️ 找不到 API Key，請檢查 Secrets 設定！")
    st.stop()

# --- 核心轉換函數 (自動切換模型版) ---
def process_file_with_auto_model(uploaded_file):
    bytes_data = uploaded_file.getvalue()
    
    # 定義提示詞
    prompt = """
    你是一個專業的資料輸入員。請將這份報價單/請購單圖片或PDF轉換為 CSV 格式。
    【重要規則】
    1. 輸出必須是標準 CSV 格式。
    2. 只要輸出 CSV 內容，不要有任何 Markdown 標記 (不要有 ```csv ... ```)。
    3. 必須包含表頭資訊：公司名稱、工程名稱、單號、日期 (若有)。
    4. 必須完整列出表格明細：項次、品名、型號、單位、數量、單價、總價、備註。
    5. 若遇到跨頁表格，請自動合併為一張表。
    6. 請務必包含底部的付款條件、稅金、驗收條款等文字資訊，將其整理在表格最下方的列。
    7. 所有金額保持數字格式 (可含千分位逗號)。
    """
    
    parts = [{"mime_type": uploaded_file.type, "data": bytes_data}, prompt]

    # 【關鍵功能】自動輪替模型清單
    # 如果第一個失敗，就試第二個，依此類推
    model_candidates = [
        "gemini-1.5-flash",        # 首選：最新快版
        "gemini-1.5-pro",          # 次選：最新旗艦版
        "gemini-pro-vision",       # 備案：舊版穩定模型 (專門看圖)
    ]
    
    last_error = None
    
    # 迴圈測試每個模型
    for model_name in model_candidates:
        try:
            # 建立模型物件
            model = genai.GenerativeModel(model_name)
            
            # 嘗試產生內容
            response = model.generate_content(parts)
            
            # 如果成功，回傳結果並告訴使用者是用哪個模型成功的
            return response.text, model_name
            
        except Exception as e:
            # 失敗了，記錄錯誤，繼續試下一個
            last_error = e
            continue
            
    # 如果全部都失敗，拋出最後一個錯誤
    raise last_error

# --- 主介面 ---
st.title("📄 家用報價單轉 Excel 神器")
st.caption(f"環境版本: {genai.__version__} (已更新)") 

uploaded_file = st.file_uploader("請上傳 PDF 或 圖片", type=["pdf", "jpg", "png", "jpeg"])

if uploaded_file is not None:
    if st.button("🚀 開始轉換", type="primary"):
        status_box = st.empty() # 建立一個空區塊來顯示狀態
        
        try:
            status_box.info("AI 正在嘗試讀取中... (這可能需要 30 秒)")
            
            # 1. 呼叫自動切換模型函數
            csv_text, used_model = process_file_with_auto_model(uploaded_file)
            
            # 顯示成功訊息
            status_box.success(f"✅ 轉換成功！(使用模型: {used_model})")
            
            # 2. 清理資料
            clean_csv = csv_text.replace("```csv", "").replace("```", "").strip()
            
            # 3. 轉成 DataFrame
            df = pd.read_csv(StringIO(clean_csv))
            
            # 4. 顯示預覽
            st.dataframe(df)
            
            # 5. 製作 Excel 下載
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='報價單資料')
            
            st.download_button(
                label="📥 下載 Excel 檔案",
                data=output.getvalue(),
                file_name="報價單.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
        except Exception as e:
            status_box.error(f"很抱歉，所有 AI 模型都嘗試過了但失敗。錯誤訊息：{e}")

