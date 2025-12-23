import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="API Key 診斷室", page_icon="🏥")
st.title("🏥 API Key 終極診斷")

# 1. 檢查 Key 格式
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    # 隱藏部分密碼，只顯示頭尾確認
    masked_key = f"{api_key[:5]}...{api_key[-5:]}"
    st.info(f"正在測試 Key: {masked_key}")
    genai.configure(api_key=api_key)
except Exception as e:
    st.error(f"❌ Secrets 設定讀取失敗：{e}")
    st.stop()

if st.button("🩺 開始診斷 (Check Models)", type="primary"):
    st.write("正在嘗試連線 Google 伺服器...")
    
    try:
        # 2. 直接向 Google 詢問可用清單
        all_models = list(genai.list_models())
        
        # 3. 過濾出能用的「對話模型」
        chat_models = []
        for m in all_models:
            if 'generateContent' in m.supported_generation_methods:
                chat_models.append(m.name)
        
        if chat_models:
            st.success(f"✅ 連線成功！您的新 Key 可以使用以下 {len(chat_models)} 個模型：")
            st.json(chat_models)
            st.balloons()
            
            st.markdown("---")
            st.markdown("### 👇 這是您下次寫程式要用的正確名稱")
            st.code(f"model = genai.GenerativeModel('{chat_models[0].replace('models/', '')}')")
        else:
            st.warning("⚠️ 連線成功，但这組 Key 權限不足，找不到任何可用的對話模型。")
            
    except Exception as e:
        st.error("❌ 連線失敗 (Fatal Error)")
        st.error(f"錯誤訊息：{e}")
        st.markdown("### 🚑 解決辦法")
        st.markdown("這個錯誤通常代表：**您的 API Key 無效** 或 **Google Cloud 專案未啟用 API**。請務必去 [Google AI Studio](https://aistudio.google.com/app/apikey) 重新申請一個「新專案」的 Key。")
