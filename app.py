from flask import Flask, request, jsonify
from flask_cors import CORS
import yfinance as yf
import os
import math

app = Flask(__name__)
CORS(app)

@app.route('/get_signal', methods=['GET'])
def get_signal():
    symbol = request.args.get('symbol', 'EURUSD').upper()
    interval = request.args.get('interval', '5m')
    
    if symbol == "WAKEUP": return jsonify({"status": "awake"})

    try:
        # 1. Загружаем данные (за 5 дней, чтобы точно хватило на индикаторы)
        yf_symbol = f"{symbol}=X"
        ticker = yf.Ticker(yf_symbol)
        df = ticker.history(period="5d", interval=interval)

        if df.empty:
            return jsonify({"status": "error", "message": "Market Closed or No Data"})

        # 2. Подготовка данных
        prices = df['Close'].tolist()
        highs = df['High'].tolist()
        lows = df['Low'].tolist()
        last_price = prices[-1]

        # --- ИНДИКАТОРЫ (Чистый Python) ---
        # SMA 20
        sma_20 = sum(prices[-20:]) / 20
        
        # RSI 14
        changes = [prices[i] - prices[i-1] for i in range(-14, 0)]
        gains = sum([c for c in changes if c > 0]) / 14
        losses = abs(sum([c for c in changes if c < 0])) / 14
        rsi = 100 - (100 / (1 + (gains/losses if losses > 0 else 1)))

        # Pivot Points
        p_high, p_low, p_close = highs[-2], lows[-2], prices[-2]
        pivot = (p_high + p_low + p_close) / 3
        s1 = (2 * pivot) - p_high
        r1 = (2 * pivot) - p_low

        # --- ЛОГИКА СИГНАЛА ---
        score = 0
        if rsi < 35: score += 40
        if rsi > 65: score -= 40
        if last_price > sma_20: score += 20
        else: score -= 20

        if score >= 40: sig = "STRONG_BUY"
        elif score >= 15: sig = "BUY"
        elif score <= -40: sig = "STRONG_SELL"
        elif score <= -15: sig = "SELL"
        else: sig = "NEUTRAL"

        # ОТВЕТ (Ключи строго под JavaScript)
        return jsonify({
            "status": "success",
            "signal": sig,
            "confidence": min(abs(score) + 40, 98),
            "indicators": {
                "EMA": "Bullish" if last_price > sma_20 else "Bearish",
                "RSI": str(round(rsi, 1)),
                "MACD": "FIRE" if abs(score) > 30 else "WAIT",
                "BB": "Support" if last_price <= s1 else ("Resist" if last_price >= r1 else "Mid")
            }
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
