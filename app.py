import streamlit as st
import google.generativeai as genai
import pandas as pd
from io import BytesIO

# --- 設定頁面 ---
st.set_page_config(page_title="智慧型轉檔神器", page_icon="🤖")

# --- 讀取 API Key ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("⚠️ 找不到 API Key，請檢查 Secrets 設定！")
    st.stop()

# --- 關鍵功能：自動尋找可用的模型 ---
def get_valid_model():
    """
    不指定特定模型名稱，而是向 Google 查詢目前這個 API Key 能用什麼模型。
    優先順序：Flash -> Pro -> 任何能用的
    """
    try:
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
        
        # 顯示找到的模型（除錯用）
        print(f"您的 API Key 可用模型: {available_models}")

        # 優先選擇順序
        for preferred in ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']:
            # 模糊比對，只要名稱裡包含該關鍵字就用
            for model_name in available_models:
                if preferred in model_name:
                    return model_name
        
        # 如果都沒有，就回傳第一個找到的
        if available_models:
            return available_models[0]
        else:
            return None
    except Exception as e:
        st.error(f"無法取得模型清單，可能是 API Key 權限問題。錯誤: {e}")
        return "models/gemini-pro" # 最後的掙扎，硬試一個

# --- 核心處理函數 ---
def process_file(uploaded_file, model_name):
    bytes_data = uploaded_file.getvalue()
    
    # 建立模型
    model = genai.GenerativeModel(model_name)
    
    # 提示詞：使用 ### 分隔，確保格式不亂
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
    
    parts = [{"mime_type": uploaded_file.type, "data": bytes_data}, prompt]
    
    response = model.generate_content(parts)
    return response.text

# --- APP 介面 ---
st.title("🤖 智慧型轉檔神器 (自動偵測版)")

uploaded_file = st.file_uploader("請上傳 PDF 或 圖片", type=["pdf", "jpg", "png", "jpeg"])

if uploaded_file is not None:
    if st.button("🚀 開始轉換", type="primary"):
        status_box = st.empty()
        status_box.info("🔍 正在尋找您的帳號可用的 AI 模型...")
        
        try:
            # 1. 自動取得模型
            target_model = get_valid_model()
            
            if not target_model:
                status_box.error("❌ 找不到任何可用的 AI 模型，請確認您的 API Key 是否有開通 Generative AI 權限。")
                st.stop()
                
            status_box.info(f"✅ 使用模型: {target_model} 正在讀取檔案中...")
            
            # 2. 呼叫 AI
            raw_text = process_file(uploaded_file, target_model)
            
            # 3. 清理資料
            clean_text = raw_text.replace("```csv", "").replace("```", "").strip()
            
            # 4. 手動解析 (使用 ### 分隔)
            data = []
            lines = clean_text.split('\n')
            
            if len(lines) > 0:
                # 抓取第一行當表頭
                headers = lines[0].split('###')
                headers = [h.strip() for h in headers]
                
                # 處理剩下的行
                for line in lines[1:]:
                    if not line.strip(): continue
                    
                    row = line.split('###')
                    row = [r.strip() for r in row]
                    
                    # 防呆補齊
                    if len(row) < len(headers):
                        row += [''] * (len(headers) - len(row))
                    elif len(row) > len(headers):
                        row = row[:len(headers)]
                        
                    data.append(row)
                
                # 轉成 DataFrame
                df = pd.read_csv(BytesIO(b""))
                if data:
                    df = pd.DataFrame(data, columns=headers)

                status_box.success(f"✅ 轉換成功！")
                st.dataframe(df)
                
                # 5. 下載按鈕
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
                st.warning("AI 回傳內容為空，請重試。")

        except Exception as e:
            st.error(f"發生錯誤: {e}")

