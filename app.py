from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import requests
import os

app = Flask(__name__)
CORS(app)

# Функции расчета индикаторов без внешних библиотек
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_ema(series, period=200):
    return series.ewm(span=period, adjust=False).mean()

def get_binance_data(symbol, interval):
    try:
        sym = symbol.upper().replace("USD", "USDT")
        url = "https://api.binance.com/api/v3/klines"
        params = {"symbol": sym, "interval": interval, "limit": 300}
        res = requests.get(url, params=params, timeout=10)
        df = pd.DataFrame(res.json(), columns=['t', 'o', 'h', 'l', 'c', 'v', 'ct', 'q', 'n', 'tb', 'tq', 'i'])
        df['c'] = df['c'].astype(float)
        return df
    except Exception as e:
        print(f"Data error: {e}")
        return None

@app.route('/get_signal', methods=['GET'])
def get_signal():
    symbol = request.args.get('symbol', 'BTCUSDT')
    interval = request.args.get('interval', '5m')
    
    if symbol == "WAKEUP": return jsonify({"status": "awake"})

    df = get_binance_data(symbol, interval)
    if df is None or df.empty:
        return jsonify({"status": "error", "message": "No data"}), 400

    # Считаем индикаторы через чистый Pandas
    df['rsi'] = calculate_rsi(df['c'])
    df['ema200'] = calculate_ema(df['c'], 200)
    
    last_price = df['c'].iloc[-1]
    rsi_val = df['rsi'].iloc[-1]
    ema_val = df['ema200'].iloc[-1]

    # Логика сигнала
    trend = "Bullish" if last_price > ema_val else "Bearish"
    
    if rsi_val < 35 and trend == "Bullish":
        sig = "STRONG_BUY"
        conf = 85
    elif rsi_val > 65 and trend == "Bearish":
        sig = "STRONG_SELL"
        conf = 85
    elif trend == "Bullish":
        sig = "BUY"
        conf = 60
    else:
        sig = "SELL"
        conf = 60

    return jsonify({
        "status": "success",
        "signal": sig,
        "confidence": conf,
        "indicators": {
            "RSI": float(rsi_val) if not pd.isna(rsi_val) else 50.0,
            "EMA_200": trend,
            "MACD": "Ready",
            "BB": "Normal"
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
