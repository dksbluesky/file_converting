import streamlit as st
import google.generativeai as genai
import pandas as pd
from io import StringIO, BytesIO

# --- 設定頁面 ---
st.set_page_config(page_title="智慧型轉檔神器", page_icon="🚀")

# --- 讀取 API Key ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("⚠️ 找不到 API Key，請檢查 Secrets 設定格式是否正確 (不能換行)！")
    st.stop()

# --- 核心處理 ---
def process_file(uploaded_file):
    # 直接使用最穩定的 1.5 Flash 模型
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # 【關鍵修正】強制要求 AI 用 "|" (直槓) 分隔，解決金額逗號造成的表格錯亂
    prompt = """
    你是一個專業的資料輸入員。請將這份圖片或 PDF 中的表格轉換為 CSV 純文字格式。
    
    【嚴格規則】
    1. 欄位之間請務必使用 "|" (直槓) 作為分隔符號，絕對不要使用逗號。
       例如：項次|品名|數量|單價|總價
    2. 第一行必須是表頭。
    3. 只輸出表格資料，不要有任何 Markdown 標記 (如 ```csv )，也不要任何解釋文字。
    4. 若遇到跨頁，請自動合併。
    5. 金額請保留千分位符號 (如 1,000)。
    6. 文件底部的付款條件、稅金等資訊，請整理在表格的最下方。
    """
    
    bytes_data = uploaded_file.getvalue()
    parts = [{"mime_type": uploaded_file.type, "data": bytes_data}, prompt]
    
    response = model.generate_content(parts)
    return response.text

# --- APP 介面 ---
st.title("🚀 智慧型轉檔神器 (最終版)")
st.caption("解決了金額逗號問題，並修正了連線設定")

uploaded_file = st.file_uploader("請上傳 PDF 或 圖片", type=["pdf", "jpg", "png", "jpeg"])

if uploaded_file is not None:
    if st.button("開始轉換", type="primary"):
        status_box = st.empty()
        status_box.info("AI 正在讀取中... 請稍候")
        
        try:
            # 1. 呼叫 AI
            raw_text = process_file(uploaded_file)
            
            # 2. 清理資料
            clean_text = raw_text.replace("```csv", "").replace("```", "").strip()
            
            # 3. 轉成表格 (使用 | 分隔)
            # on_bad_lines='skip' 會自動略過格式爛掉的行，避免報錯
            df = pd.read_csv(StringIO(clean_text), sep="|", on_bad_lines='skip')
            
            # 移除全空的欄位
            df = df.dropna(axis=1, how='all')
            
            status_box.success("✅ 轉換成功！")
            st.dataframe(df)
            
            # 4. 下載按鈕
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='報價單')
            
            st.download_button(
                label="📥 下載 Excel",
                data=output.getvalue(),
                file_name="報價單.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
        except Exception as e:
            status_box.error(f"發生錯誤：{e}")
            st.error("如果顯示 404 錯誤，請務必檢查 Secrets 裡的 API Key 是否有多餘的換行！")
            # 顯示 AI 回傳的原始文字，方便除錯
            if 'raw_text' in locals():
                st.text_area("AI 讀到的原始內容：", raw_text, height=200)
