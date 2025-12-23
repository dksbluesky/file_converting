import streamlit as st
import google.generativeai as genai
import pandas as pd
from io import BytesIO

# --- 設定頁面 ---
st.set_page_config(page_title="智慧型轉檔神器", page_icon="💪")

# --- 讀取 API Key ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("⚠️ 找不到 API Key，請檢查 Secrets 設定！")
    st.stop()

# --- 核心處理函數 ---
def process_file(uploaded_file):
    # 使用 1.5 Flash 模型
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # 【關鍵策略】請 AI 用特殊的「###」符號來分隔，絕對不會跟內容衝突
    prompt = """
    你是一個專業的資料輸入員。請將這份圖片或 PDF 中的表格轉換為純文字資料。
    
    【嚴格規則】
    1. 每一欄之間，請使用 "###" (三個井字號) 作為分隔符號。
       (例如：項次###品名###數量###單價###總價)
    2. 每一列資料換一行。
    3. 第一行必須是表頭。
    4. 不要輸出任何 Markdown 標記 (如 ```csv )，只要純文字。
    5. 金額請保留千分位符號 (如 1,000)，不要隨意移除。
    6. 若遇到跨頁，請自動合併。
    7. 底部若有付款條件、稅金等資訊，請整理在表格最下方的列。
    """
    
    bytes_data = uploaded_file.getvalue()
    parts = [{"mime_type": uploaded_file.type, "data": bytes_data}, prompt]
    
    response = model.generate_content(parts)
    return response.text

# --- APP 介面 ---
st.title("💪 智慧型轉檔神器 (強效版)")
st.caption("目前使用模型: gemini-1.5-flash | 狀態: API 連線正常")

uploaded_file = st.file_uploader("請上傳 PDF 或 圖片", type=["pdf", "jpg", "png", "jpeg"])

if uploaded_file is not None:
    if st.button("🚀 開始轉換", type="primary"):
        status_box = st.empty()
        status_box.info("AI 正在閱讀文件中... (連線成功，處理資料中)")
        
        try:
            # 1. 呼叫 AI
            raw_text = process_file(uploaded_file)
            
            # 2. 清理資料 (移除可能殘留的標記)
            clean_text = raw_text.replace("```csv", "").replace("```", "").strip()
            
            # 3. 【手動解析】不依賴 pd.read_csv，自己切分資料
            data = []
            lines = clean_text.split('\n')
            
            if len(lines) > 0:
                # 自動抓取第一行當作表頭
                headers = lines[0].split('###')
                # 移除頭尾空白
                headers = [h.strip() for h in headers]
                
                # 處理剩下的每一行
                for line in lines[1:]:
                    if not line.strip(): continue # 跳過空行
                    
                    row = line.split('###')
                    row = [r.strip() for r in row]
                    
                    # 補齊欄位 (防呆機制：如果欄位不夠，自動補空值，避免報錯)
                    if len(row) < len(headers):
                        row += [''] * (len(headers) - len(row))
                    # 如果欄位太多，切掉多餘的
                    elif len(row) > len(headers):
                        row = row[:len(headers)]
                        
                    data.append(row)
                
                # 轉成 DataFrame
                df = pd.read_csv(BytesIO(b"")) # 建立空的
                if data:
                    df = pd.DataFrame(data, columns=headers)

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
            else:
                st.warning("AI 回傳的內容似乎是空的，請再試一次。")

        except Exception as e:
            status_box.error(f"發生未預期的錯誤：{e}")
            # 顯示 AI 回傳的原始文字，方便除錯
            if 'raw_text' in locals():
                with st.expander("查看 AI 原始回傳內容 (除錯用)"):
                    st.text(raw_text)
