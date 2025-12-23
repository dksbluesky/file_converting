import streamlit as st
import google.generativeai as genai
import pandas as pd
from io import BytesIO

# --- 設定頁面 ---
st.set_page_config(page_title="智慧型轉檔神器", page_icon="🌟")

# --- 讀取 API Key ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("⚠️ 找不到 API Key，請檢查 Secrets 設定！")
    st.stop()

# --- 核心處理函數 (含自動切換模型功能) ---
def process_file_with_fallback(uploaded_file):
    bytes_data = uploaded_file.getvalue()
    
    # 提示詞：要求 AI 用 "###" 分隔，避免逗號干擾
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
    
    # 【關鍵功能】候選模型清單 (如果第一個失敗，自動試下一個)
    model_candidates = [
        "gemini-1.5-pro",          # 旗艦版 (最聰明)
        "gemini-1.5-flash",        # 快速版
        "gemini-pro",              # 舊版 (相容性最高)
        "gemini-pro-vision"        # 舊版視覺模型
    ]
    
    last_error = None
    
    # 迴圈測試每一個模型，直到成功為止
    for model_name in model_candidates:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(parts)
            return response.text, model_name # 回傳成功結果與使用的模型
        except Exception as e:
            last_error = e
            continue # 失敗了就試下一個
            
    # 如果全部都失敗，才報錯
    raise last_error

# --- APP 介面 ---
st.title("🌟 智慧型轉檔神器 (完美合體版)")
st.caption("已啟用：自動模型切換 + 強力表格解析")

uploaded_file = st.file_uploader("請上傳 PDF 或 圖片", type=["pdf", "jpg", "png", "jpeg"])

if uploaded_file is not None:
    if st.button("🚀 開始轉換", type="primary"):
        status_box = st.empty()
        status_box.info("AI 正在閱讀文件中... (正在尋找可用的模型)")
        
        try:
            # 1. 呼叫 AI (會自動嘗試多個模型)
            raw_text, used_model = process_file_with_fallback(uploaded_file)
            
            # 2. 清理資料
            clean_text = raw_text.replace("```csv", "").replace("```", "").strip()
            
            # 3. 【手動解析】不依賴 CSV 格式，自己切分 "###"
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
                    
                    # 防呆：欄位長度對齊
                    if len(row) < len(headers):
                        row += [''] * (len(headers) - len(row))
                    elif len(row) > len(headers):
                        row = row[:len(headers)]
                        
                    data.append(row)
                
                # 轉成 DataFrame
                df = pd.read_csv(BytesIO(b""))
                if data:
                    df = pd.DataFrame(data, columns=headers)

                status_box.success(f"✅ 轉換成功！(使用模型: {used_model})")
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
                st.warning("AI 回傳內容為空，請重試。")

        except Exception as e:
            status_box.error("所有模型都嘗試失敗，請稍後再試。")
            st.error(f"詳細錯誤訊息: {e}")

