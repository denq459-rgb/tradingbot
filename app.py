from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import pandas_ta as ta
import requests
import os

app = Flask(__name__)
CORS(app)

def get_binance_data(symbol, interval):
    try:
        # Корректировка символа
        sym = symbol.upper()
        if "USD" in sym and not sym.endswith("USDT"):
            sym = sym.replace("USD", "USDT")
            
        url = "https://api.binance.com/api/v3/klines"
        params = {"symbol": sym, "interval": interval, "limit": 300}
        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        df = pd.DataFrame(res.json(), columns=['time', 'open', 'high', 'low', 'close', 'vol', 'ct', 'qav', 'nt', 'tb', 'tq', 'i'])
        df['close'] = df['close'].astype(float)
        return df
    except Exception as e:
        print(f"Error: {e}")
        return None

@app.route('/get_signal', methods=['GET'])
def get_signal():
    symbol = request.args.get('symbol', 'BTCUSDT')
    interval = request.args.get('interval', '5m')
    
    if symbol == "WAKEUP": return jsonify({"status": "awake"})

    df = get_binance_data(symbol, interval)
    if df is None or df.empty:
        return jsonify({"status": "error", "message": "No data"}), 400

    # Расчет индикаторов
    rsi = ta.rsi(df['close'], length=14).iloc[-1]
    ema200 = ta.ema(df['close'], length=200).iloc[-1]
    macd = ta.macd(df['close'])
    curr_price = df['close'].iloc[-1]
    
    # Логика
    score = 0
    trend_val = "Bullish" if curr_price > ema200 else "Bearish"
    score += 25 if trend_val == "Bullish" else -25
    
    macd_val = macd['MACD_12_26_9'].iloc[-1]
    macd_sig = macd['MACDs_12_26_9'].iloc[-1]
    macd_status = "Bullish" if macd_val > macd_sig else "Bearish"
    score += 20 if macd_status == "Bullish" else -20
    
    if rsi < 30: score += 30
    elif rsi > 70: score -= 30

    # Итоговый сигнал
    if score >= 20: sig = "BUY"
    elif score <= -20: sig = "SELL"
    else: sig = "NEUTRAL"

    # ВАЖНО: Ключи должны совпадать с JavaScript!
    return jsonify({
        "status": "success",
        "signal": sig,
        "confidence": min(abs(score) + 40, 99),
        "indicators": {
            "RSI": float(rsi),
            "EMA_200": trend_val,
            "MACD": macd_status,
            "BB": "Normal" # Заглушка для примера
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
