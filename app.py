import streamlit as st
import google.generativeai as genai
import pandas as pd
from io import StringIO, BytesIO

# --- 設定頁面 ---
st.set_page_config(page_title="智慧型轉檔神器", page_icon="🤖")

# --- 讀取 API Key ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("⚠️ 找不到 API Key，請檢查 Secrets 設定！")
    st.stop()

# --- 核心轉換函數 ---
def process_file_with_auto_model(uploaded_file):
    bytes_data = uploaded_file.getvalue()
    
    # 【關鍵修改】改用 "|" 當分隔符號，避免內容中的逗號(例如金額 3,000) 導致錯亂
    prompt = """
    你是一個專業的資料輸入員。請將這份圖片或PDF中的表格轉換為「直槓分隔」的 CSV 格式 (Pipe-separated values)。
    
    【嚴格規則】
    1. 使用 "|" (直槓) 作為欄位分隔符號，不要用逗號。
    2. 輸出的第一行必須是表頭 (例如: 項次|品名|數量|單價|總價...)。
    3. 不要有任何 Markdown 標記 (不要有 ```csv 或 ``` 符號)，只輸出純文字資料。
    4. 不要輸出任何開頭的解釋文字 (例如 "好的，這是結果...")。
    5. 必須完整列出表格明細。
    6. 若遇到跨頁表格，請自動合併。
    7. 底部若有付款條件、稅金等資訊，請整理在表格最下方。
    8. 金額請保留千分位符號 (如 3,000)。
    """
    
    parts = [{"mime_type": uploaded_file.type, "data": bytes_data}, prompt]

    # 自動輪替模型清單 (先試旗艦版，再試快速版)
    model_candidates = [
        "gemini-1.5-pro",          # 首選：理解力最強
        "gemini-1.5-flash",        # 次選：速度快
        "gemini-pro",              # 備案：舊版穩定
    ]
    
    last_error = None
    
    for model_name in model_candidates:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(parts)
            return response.text, model_name
        except Exception as e:
            last_error = e
            continue
            
    raise last_error

# --- 主介面 ---
st.title("🤖 智慧型轉檔神器 (增強版)")
# 顯示目前的 SDK 版本，確認環境正常
st.caption(f"目前運作環境: SDK {genai.__version__}") 

uploaded_file = st.file_uploader("請上傳 PDF 或 圖片", type=["pdf", "jpg", "png", "jpeg"])

if uploaded_file is not None:
    if st.button("🚀 開始轉換", type="primary"):
        status_box = st.empty()
        
        try:
            status_box.info("AI 正在閱讀文件中... (如果檔案較大請稍候)")
            
            # 1. 呼叫 AI
            raw_text, used_model = process_file_with_auto_model(uploaded_file)
            
            # 2. 清理資料 (移除可能殘留的標記)
            clean_text = raw_text.replace("```csv", "").replace("```", "").strip()
            
            # 3. 嘗試轉換成表格 (使用 | 分隔)
            # on_bad_lines='skip' 會自動跳過格式錯誤的行，避免程式崩潰
            try:
                df = pd.read_csv(StringIO(clean_text), sep="|", on_bad_lines='skip')
                
                # 簡單清理：移除全空的欄位
                df = df.dropna(axis=1, how='all')
                
                status_box.success(f"✅ 轉換成功！(使用模型: {used_model})")
                
                # 4. 顯示預覽
                st.dataframe(df)
                
                # 5. 製作 Excel 下載
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False, sheet_name='轉檔結果')
                
                st.download_button(
                    label="📥 下載 Excel 檔案",
                    data=output.getvalue(),
                    file_name="轉檔結果.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            except Exception as parse_error:
                st.error("表格格式轉換失敗，但 AI 有讀到內容。請查看下方的原始資料：")
                st.text_area("AI 回傳的原始文字 (可複製自行整理)", clean_text, height=300)
                st.error(f"錯誤代碼: {parse_error}")
            
        except Exception as e:
            status_box.error(f"AI 讀取失敗，請確認圖片清晰度。錯誤訊息：{e}")
