import yfinance as yf
from serpapi.google_search import GoogleSearch
from textblob import TextBlob
from fredapi import Fred
import pandas as pd
import requests
import os

# --- CONFIGURAÇÕES ---
SERPAPI_KEY = os.environ.get('SERPAPI_KEY')
FRED_API_KEY = os.environ.get('FRED_API_KEY')
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

fred = Fred(api_key=FRED_API_KEY)

RISK_TAXONOMY = {
    'CRITICAL': ['default', 'bankruptcy', 'liquidity crisis', 'margin call', 'bank run', 'solvency', 'collapse', 'insolvency', 'chapter 11', 'bond market crash'],
    'SEVERE': ['recession', 'inflation spike', 'stagflation', 'credit crunch', 'debt bubble', 'yield curve inversion', 'deflation', 'economic contraction'],
    'AI_SPECULATION': ['ai bubble', 'overvalued', 'hype', 'capex bubble', 'chip shortage', 'semiconductor cycle', 'ai valuation', 'tech bubble'],
    'MACRO': ['fed hike', 'quantitative tightening', 'interest rates', 'fiscal deficit', 'debt ceiling', 'treasury yield spike', 'hawkish fed'],
    'MARKET': ['volatility', 'flash crash', 'sell-off', 'panic', 'retail mania', 'short squeeze', 'gamma squeeze', 'market crash']
}

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.get(url, params={'chat_id': TELEGRAM_CHAT_ID, 'text': msg})

def get_market_data():
    m2 = fred.get_series('M2SL')
    # Extração de float puro
    liquidity = float((m2.iloc[-1] - m2.iloc[-2]) / m2.iloc[-2])
    tnx = yf.download("^TNX", period="1mo", progress=False)
    y10 = float(tnx['Close'].iloc[-1])
    return liquidity, y10

def get_sentiment():
    score = 0.0
    weights = {'CRITICAL': 5.0, 'SEVERE': 3.0, 'AI_SPECULATION': 2.0, 'MACRO': 1.0, 'MARKET': 1.0}
    for cat, tags in RISK_TAXONOMY.items():
        try:
            search = GoogleSearch({"engine": "google_news", "q": " OR ".join(tags[:5]), "api_key": SERPAPI_KEY, "num": 3})
            for story in search.get_dict().get('news_results', []):
                pol = TextBlob(story.get('title', '')).sentiment.polarity
                if pol < 0: score += (abs(pol) * weights[cat])
        except: continue
    return float(score)

def check_radar(ticker, name):
    df = yf.download(ticker, period="2y", progress=False)
    
    # Conversão forçada para float simples
    close_val = float(df['Close'].iloc[-1])
    mean_val = float(df['Close'].rolling(200).mean().iloc[-1])
    std_val = float(df['Close'].rolling(200).std().iloc[-1])
    
    z_score = (close_val - mean_val) / std_val
    
    liq, y10 = get_market_data()
    risk = get_sentiment()
    
    # Formatação garantida com tipos nativos do Python
    msg = f"--- Radar de Elite: {name} ---\nRisco: {float(risk):.2f} | Z-Score: {float(z_score):.2f} | Liq: {float(liq):.4f} | Yield: {float(y10):.2f}%"
    print(msg)
    
    if float(risk) > 40.0 or float(z_score) > 2.0:
        send_telegram(f"⚠️ ALERTA: {name} em zona de perigo!\n{msg}")

if __name__ == "__main__":
    check_radar("^GSPC", "S&P 500")
    check_radar("^IXIC", "NASDAQ")
