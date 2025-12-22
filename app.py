import streamlit as st
import google.generativeai as genai
import pandas as pd
from io import StringIO, BytesIO

# --- 設定頁面 ---
st.set_page_config(page_title="轉檔神器", page_icon="📄")

# --- 讀取 API Key ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("⚠️ 找不到 API Key，請檢查 Secrets 設定！")
    st.stop()

# --- 主介面 ---
st.title("📄 家用報價單轉 Excel 神器")
# 【關鍵檢查】這行會顯示目前安裝的版本
st.caption(f"目前 AI 核心版本 (SDK): {genai.__version__}") 

if genai.__version__ < "0.7.0":
    st.error("❌ 版本過舊！請執行「刪除 App 再重新建立」的步驟。")

def process_file(uploaded_file):
    # 使用 1.5 Flash 模型
    model = genai.GenerativeModel('gemini-1.5-flash')
    
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
    
    bytes_data = uploaded_file.getvalue()
    parts = [{"mime_type": uploaded_file.type, "data": bytes_data}, prompt]
    
    response = model.generate_content(parts)
    return response.text

uploaded_file = st.file_uploader("請上傳 PDF 或 圖片", type=["pdf", "jpg", "png", "jpeg"])

if uploaded_file is not None:
    if st.button("🚀 開始轉換", type="primary"):
        with st.spinner('AI 正在讀取中...'):
            try:
                csv_text = process_file(uploaded_file)
                clean_csv = csv_text.replace("```csv", "").replace("```", "").strip()
                df = pd.read_csv(StringIO(clean_csv))
                
                st.success("轉換成功！")
                st.dataframe(df)
                
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
                st.error(f"發生錯誤：{e}")
