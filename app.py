import streamlit as st
import google.generativeai as genai
import pandas as pd
from io import StringIO, BytesIO

# --- 設定頁面 ---
st.set_page_config(page_title="家人專用轉檔神器", page_icon="📝")

# --- 讀取 API Key ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("找不到 API Key，請檢查 Secrets 設定！")

def process_file_to_df(uploaded_file):
    # 【關鍵修改】改用相容性最高的 "gemini-pro" 模型
    # 先求能跑，再求快。這個模型比較舊，但最穩定。
    model = genai.GenerativeModel('gemini-pro')
    
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
    
    # 讀取檔案
    bytes_data = uploaded_file.getvalue()
    
    # gemini-pro 對圖片的處理方式稍微不同，這裡做通用處理
    parts = [
        {"mime_type": uploaded_file.type, "data": bytes_data},
        prompt
    ]
    
    response = model.generate_content(parts)
    return response.text

# --- APP 介面 ---
st.title("📝 家用報價單轉 Excel 神器 (穩定版)")
st.write("目前使用通用相容模式，請上傳檔案試試看！")

uploaded_file = st.file_uploader("請上傳 PDF 或 圖片", type=["pdf", "jpg", "png", "jpeg"])

if uploaded_file is not None:
    if st.button("🚀 開始轉換", type="primary"):
        with st.spinner('AI 正在讀取中...'):
            try:
                # 1. 呼叫 AI
                csv_text = process_file_to_df(uploaded_file)
                
                # 2. 清理資料
                clean_csv = csv_text.replace("```csv", "").replace("```", "").strip()
                
                # 3. 轉成 DataFrame
                df = pd.read_csv(StringIO(clean_csv))
                
                # 4. 顯示結果
                st.success("轉換成功！")
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
                st.error(f"發生錯誤：{e}")

