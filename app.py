import streamlit as st
import yfinance as yf
import pandas as pd
import ta

# 設定網頁標題
st.set_page_config(page_title="高勝率 AI 交易訊號儀表板", layout="wide")
st.title("📈 股票操盤手：日K + 5分K 最大效益策略分析")

# 側邊欄：輸入股票代碼
sidebar_ticker = st.sidebar.text_input("輸入股票代碼 (如 2330.TW)", value="2330.TW")
st.sidebar.markdown("### 策略邏輯：\n1. **日K MACD** 確認多頭趨勢\n2. **5分K 布林通道** 抓突破\n3. **5分K RSI & 成交量** 確認動能\n4. **SAR** 移動停利")

def get_data(ticker, period, interval):
    try:
        df = yf.download(ticker, period=period, interval=interval)
        if df.empty:
            return None
        return df
    except Exception as e:
        return None

def calculate_indicators(df):
    # MACD
    macd = ta.trend.MACD(close=df['Close'])
    df['MACD'] = macd.macd()
    df['MACD_Signal'] = macd.macd_signal()
    df['MACD_Hist'] = macd.macd_diff()
    
    # RSI
    df['RSI'] = ta.momentum.RSIIndicator(close=df['Close'], window=14).rsi()
    
    # Bollinger Bands
    indicator_bb = ta.volatility.BollingerBands(close=df['Close'], window=20, window_dev=2)
    df['BB_High'] = indicator_bb.bollinger_hband()
    df['BB_Low'] = indicator_bb.bollinger_lband()
    df['BB_Width'] = df['BB_High'] - df['BB_Low']
    
    # SAR
    df['SAR'] = ta.trend.PSARIndicator(df['High'], df['Low'], df['Close'], step=0.02, max_step=0.2).psar()
    
    # Volume MA
    df['Vol_MA5'] = df['Volume'].rolling(window=5).mean()
    
    return df

# 主程式邏輯
if sidebar_ticker:
    # 1. 取得日線資料 (判斷大趨勢)
    day_df = get_data(sidebar_ticker, "1y", "1d")
    
    # 2. 取得 5分K 資料 (判斷進出場)
    five_min_df = get_data(sidebar_ticker, "5d", "5m")

    if day_df is not None and five_min_df is not None:
        # 計算指標
        day_df = calculate_indicators(day_df)
        five_min_df = calculate_indicators(five_min_df)
        
        # 取得最新一筆資料
        last_day = day_df.iloc[-1]
        last_5m = five_min_df.iloc[-1]
        prev_5m = five_min_df.iloc[-2] # 前一根 5分K 用來確認突破

        # --- 策略判定核心 ---
        
        # 條件 1: 日 K 趨勢 (MACD 柱狀體 > 0 或 DIF > 0)
        day_trend_bullish = last_day['MACD_Hist'] > 0 or last_day['MACD'] > 0
        
        # 條件 2: 5分K 布林帶突破 (收盤價 > 上軌)
        bb_breakout = last_5m['Close'] > last_5m['BB_High']
        
        # 條件 3: 5分K 爆量 (成交量 > 5均量)
        volume_spike = last_5m['Volume'] > last_5m['Vol_MA5']
        
        # 條件 4: 5分K RSI 動能 (RSI > 50)
        rsi_bullish = last_5m['RSI'] > 50
        
        # 條件 5: 5分K SAR 翻多 (價格 > SAR)
        sar_bullish = last_5m['Close'] > last_5m['SAR']

        # --- 顯示儀表板 ---
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("1. 日線戰略 (大趨勢)")
            if day_trend_bullish:
                st.success(f"多頭市場 (MACD柱狀: {last_day['MACD_Hist']:.2f})")
            else:
                st.error(f"空頭/盤整 (MACD柱狀: {last_day['MACD_Hist']:.2f})")
                st.warning("⚠️ 日線偏空，建議觀望，勿做多當沖")

        with col2:
            st.subheader("2. 5分K 戰術 (進場訊號)")
            st.metric("目前價格", f"{last_5m['Close']:.2f}")
            
            # 訊號檢核表
            checks = {
                "布林突破": bb_breakout,
                "成交量放大": volume_spike,
                "RSI > 50": rsi_bullish,
                "站上 SAR": sar_bullish
            }
            
            for name, result in checks.items():
                icon = "✅" if result else "❌"
                st.write(f"{icon} {name}")

        with col3:
            st.subheader("3. AI 總結建議")
            if day_trend_bullish and all(checks.values()):
                st.balloons()
                st.markdown("### 🚀 強力買進訊號！")
                st.write(f"停損位 (SAR): **{last_5m['SAR']:.2f}**")
                st.info("策略：進場後沿著 SAR 移動停利，跌破即出場。")
            elif day_trend_bullish and sar_bullish and rsi_bullish:
                st.markdown("### 👀 觀察中 (等待帶量突破)")
            else:
                st.markdown("### 🛑 空手觀望")

        # 繪圖區 (5分K)
        st.subheader("5分鐘 K 線圖與布林通道")
        st.line_chart(five_min_df[['Close', 'BB_High', 'BB_Low', 'SAR']].tail(100))

    else:
        st.error("無法取得資料，請檢查股票代碼或是目前非交易時間。")
