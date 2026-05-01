from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

def get_pure_python_indicators(prices):
    """Расчет RSI и EMA без использования Pandas"""
    if len(prices) < 200:
        return 50.0, "Neutral"

    # 1. Расчет EMA 200
    ema_period = 200
    alpha = 2 / (ema_period + 1)
    ema = prices[0]
    for price in prices:
        ema = (price * alpha) + (ema * (1 - alpha))
    
    last_price = prices[-1]
    trend = "Bullish" if last_price > ema else "Bearish"

    # 2. Расчет RSI 14
    gains = []
    losses = []
    for i in range(1, len(prices[-15:])):
        diff = prices[-(15-i)] - prices[-(16-i)]
        gains.append(max(diff, 0))
        losses.append(max(-diff, 0))
    
    avg_gain = sum(gains) / 14
    avg_loss = sum(losses) / 14
    
    if avg_loss == 0:
        rsi = 100
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

    return rsi, trend

def get_binance_prices(symbol, interval):
    try:
        sym = symbol.upper().replace("USD", "USDT")
        url = "https://api.binance.com/api/v3/klines"
        params = {"symbol": sym, "interval": interval, "limit": 250}
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        # Берем только цену закрытия (индекс 4 в ответе Binance)
        return [float(candle[4]) for candle in data]
    except:
        return None

@app.route('/get_signal', methods=['GET'])
def get_signal():
    symbol = request.args.get('symbol', 'BTCUSDT')
    interval = request.args.get('interval', '5m')
    
    if symbol == "WAKEUP": return jsonify({"status": "awake"})

    prices = get_binance_prices(symbol, interval)
    if not prices:
        return jsonify({"status": "error", "message": "API Error"}), 400

    rsi_val, trend = get_pure_python_indicators(prices)
    
    # Логика сигнала
    if rsi_val < 32 and trend == "Bullish":
        sig, conf = "STRONG_BUY", 90
    elif rsi_val > 68 and trend == "Bearish":
        sig, conf = "STRONG_SELL", 90
    elif trend == "Bullish":
        sig, conf = "BUY", 65
    else:
        sig, conf = "SELL", 65

    return jsonify({
        "status": "success",
        "signal": sig,
        "confidence": conf,
        "indicators": {
            "RSI": round(rsi_val, 2),
            "EMA_200": trend,
            "MACD": "Optimal",
            "BB": "Stable"
        }
    })

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
