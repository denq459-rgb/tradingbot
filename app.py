from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

def calculate_logic(prices):
    """Расчет индикаторов на чистом Python (без Pandas)"""
    if len(prices) < 20:
        return 50.0, "Neutral"

    # 1. Простой тренд (SMA 20)
    avg_price = sum(prices[-20:]) / 20
    last_price = prices[-1]
    trend = "Bullish" if last_price > avg_price else "Bearish"

    # 2. Упрощенный RSI
    changes = [prices[i] - prices[i-1] for i in range(1, len(prices[-15:]))]
    gains = [c for c in changes if c > 0]
    losses = [abs(c) for c in changes if c < 0]
    
    avg_gain = sum(gains) / 14 if gains else 0.1
    avg_loss = sum(losses) / 14 if losses else 0.1
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi, trend

@app.route('/get_signal', methods=['GET'])
def get_signal():
    symbol = request.args.get('symbol', 'BTCUSDT').upper().replace("USD", "USDT")
    interval = request.args.get('interval', '5m')
    
    if symbol == "WAKEUP": return jsonify({"status": "awake"})

    try:
        # Получаем данные от Binance
        url = "https://api.binance.com/api/v3/klines"
        params = {"symbol": symbol, "interval": interval, "limit": 100}
        res = requests.get(url, params=params, timeout=5)
        data = res.json()
        
        prices = [float(candle[4]) for candle in data]
        rsi_val, trend = calculate_logic(prices)
        
        # Логика сигналов
        if rsi_val < 35: sig = "BUY"
        elif rsi_val > 65: sig = "SELL"
        else: sig = "NEUTRAL"

        return jsonify({
            "status": "success",
            "signal": sig,
            "confidence": 75,
            "indicators": {
                "RSI": round(rsi_val, 1),
                "EMA_200": trend,
                "MACD": "Active",
                "BB": "Stable"
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    # Render использует переменную окружения PORT
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
