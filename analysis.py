import yfinance as yf
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def calculate_rsi(data, window=14):
    """
    Calculate RSI indicator.
    """
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def get_market_trend():
    """
    Fetches international gold futures (GC=F) data and analyzes the trend.
    Returns a summary string.
    """
    try:
        logger.info("Fetching international gold data (GC=F)...")
        # Fetch data (1 month is enough for MA20 and RSI)
        ticker = yf.Ticker("GC=F")
        hist = ticker.history(period="2mo") # Fetch 2 months to ensure enough data for MA20/RSI
        
        if hist.empty:
            return "國際金價資料暫時無法取得。"
            
        # Get Close prices
        close = hist['Close']
        current_price = close.iloc[-1]
        
        # Calculate MA (Simple Moving Average)
        ma5 = close.rolling(window=5).mean().iloc[-1]
        ma20 = close.rolling(window=20).mean().iloc[-1]
        
        # Calculate RSI
        # Use simple calculation to avoid extra lib dependencies
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1]
        
        # Trend Analysis
        trend_msg = []
        trend_msg.append(f"國際金價: ${current_price:,.2f}")
        
        # MA Analysis
        if current_price > ma20:
            trend_msg.append("趨勢: 多頭 (站上月線)")
        else:
            trend_msg.append("趨勢: 空頭 (跌破月線)")
            
        if current_price > ma5:
            trend_msg.append("(短線強勢)")
        
        # RSI Analysis
        trend_msg.append(f"RSI: {current_rsi:.1f}")
        if current_rsi > 70:
            trend_msg.append("⚠️ 過熱 (超買區)")
        elif current_rsi < 30:
            trend_msg.append("🟢 超賣 (反彈機會)")
            
        return " | ".join(trend_msg)
        
    except Exception as e:
        logger.error(f"Failed to analyze market trend: {e}")
        return "國際行情分析失敗"

if __name__ == "__main__":
    print(get_market_trend())
