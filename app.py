import streamlit as st
import google.generativeai as genai
import pandas as pd
from io import StringIO, BytesIO

# --- 設定頁面 ---
st.set_page_config(page_title="轉檔神器 (自動偵測版)", page_icon="🤖")

# --- 讀取 API Key ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("⚠️ 找不到 API Key，請檢查 Secrets 設定！")
    st.stop()

# --- 核心邏輯：自動尋找可用模型 ---
def get_available_model():
    """
    不猜測模型名稱，直接問 API 有哪些模型可用，並挑選支援視覺辨識的。
    """
    try:
        status_text = "正在掃描您的 API Key 可用模型..."
        print(status_text)
        
        # 列出所有模型
        all_models = list(genai.list_models())
        
        # 優先順序：找最新的 1.5 系列 -> 找 Pro -> 找任意可用的
        priority_keywords = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro-vision"]
        
        # 1. 先試著找我們最想要的
        for keyword in priority_keywords:
            for m in all_models:
                if keyword in m.name and "vision" not in m.name: # 1.5 系列通常全能
                    return m.name
                if keyword in m.name:
                    return m.name
        
        # 2. 如果都沒有，隨便找一個支援 generateContent 的
        for m in all_models:
            if "generateContent" in m.supported_generation_methods:
                if "gemini" in m.name: # 確保是 Gemini 系列
                    return m.name
        
        return None
    except Exception as e:
        return None

# --- 轉換函數 ---
def process_file(uploaded_file, model_name):
    model = genai.GenerativeModel(model_name)
    
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
    
    # 建立內容 (處理圖片或PDF)
    parts = [{"mime_type": uploaded_file.type, "data": bytes_data}, prompt]
    
    response = model.generate_content(parts)
    return response.text

# --- 主介面 ---
st.title("🤖 智慧型轉檔神器")

# 1. 程式啟動時，自動偵測模型
if "valid_model" not in st.session_state:
    with st.spinner("正在為您的 API Key 配對最佳模型..."):
        detected_model = get_available_model()
        if detected_model:
            st.session_state["valid_model"] = detected_model
            st.success(f"✅ 配對成功！目前使用模型：{detected_model}")
        else:
            # 如果自動偵測失敗，回退到最原始的設定
            st.session_state["valid_model"] = "gemini-1.5-flash"
            st.warning("⚠️ 無法自動偵測模型清單 (可能權限不足)，將嘗試使用預設值。")
else:
    st.caption(f"目前使用模型: {st.session_state['valid_model']} (SDK: {genai.__version__})")

uploaded_file = st.file_uploader("請上傳 PDF 或 圖片", type=["pdf", "jpg", "png", "jpeg"])

if uploaded_file is not None:
    if st.button("🚀 開始轉換", type="primary"):
        with st.spinner('AI 正在讀取中...'):
            try:
                # 使用剛剛偵測到的模型名稱
                target_model = st.session_state.get("valid_model", "gemini-1.5-flash")
                
                csv_text = process_file(uploaded_file, target_model)
                
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
                st.markdown("---")
                st.info("💡 如果出現 404 錯誤，通常代表您的 API Key 權限不足或過期。建議去 Google AI Studio 重新申請一組 Key。")

