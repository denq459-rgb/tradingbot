from flask import Flask, request, jsonify
from flask_cors import CORS
import yfinance as yf
import os
import math

app = Flask(__name__)
CORS(app)

def calculate_pro_logic(df):
    try:
        # Извлекаем данные
        prices = df['Close'].dropna().tolist()
        highs = df['High'].dropna().tolist()
        lows = df['Low'].dropna().tolist()

        if len(prices) < 50:
            return "NEUTRAL", 50, {"RSI": 50, "Trend": "Wait", "Squeeze": "WAIT", "Pivot": "Mid"}

        last_close = prices[-1]

        # 1. Pivot Points (Уровни банков)
        # Используем данные предыдущего дня (вчерашняя свечка)
        p_high, p_low, p_close = highs[-2], lows[-2], prices[-2]
        pivot = (p_high + p_low + p_close) / 3
        r1 = (2 * pivot) - p_low
        s1 = (2 * pivot) - p_high

        # 2. TTM Squeeze (Имитация: Bollinger vs Keltner)
        sma_20 = sum(prices[-20:]) / 20
        std_dev = math.sqrt(sum([(x - sma_20)**2 for x in prices[-20:]]) / 20)
        atr = sum([highs[i] - lows[i] for i in range(-14, 0)]) / 14
        
        upper_bb, lower_bb = sma_20 + (2 * std_dev), sma_20 - (2 * std_dev)
        upper_kc, lower_kc = sma_20 + (1.5 * atr), sma_20 - (1.5 * atr)
        
        is_squeeze = upper_bb < upper_kc and lower_bb > lower_kc

        # 3. RSI и Тренд
        ema_50 = sum(prices[-50:]) / 50
        changes = [prices[i] - prices[i-1] for i in range(-14, 0)]
        gains = sum([c for c in changes if c > 0]) / 14
        losses = abs(sum([c for c in changes if c < 0])) / 14
        rsi = 100 - (100 / (1 + (gains/losses if losses > 0 else 1)))

        # Логика сигналов
        score = 0
        if last_close <= s1: score += 30
        if last_close >= r1: score -= 30
        if not is_squeeze:
            if rsi < 35: score += 20
            if rsi > 65: score -= 20
        if last_close > ema_50: score += 15
        else: score -= 15

        if score >= 50: sig = "STRONG_BUY"
        elif score >= 20: sig = "BUY"
        elif score <= -50: sig = "STRONG_SELL"
        elif score <= -20: sig = "SELL"
        else: sig = "NEUTRAL"

        return sig, min(abs(score) + 40, 98), {
            "RSI": round(rsi, 1),
            "Trend": "Bullish" if last_close > ema_50 else "Bearish",
            "Squeeze": "FIRE" if not is_squeeze else "WAIT",
            "Pivot": "Support" if last_close <= s1 else ("Resist" if last_close >= r1 else "Mid")
        }
    except Exception as e:
        print(f"Logic Error: {e}")
        return "NEUTRAL", 50, {"RSI": 0, "Trend": "Error", "Squeeze": "ERR", "Pivot": "ERR"}

@app.route('/get_signal', methods=['GET'])
def get_signal():
    try:
        symbol = request.args.get('symbol', 'EURUSD').upper()
        yf_symbol = f"{symbol}=X"
        interval = request.args.get('interval', '5m')
        
        # Получаем чуть больше данных для корректного расчета индикаторов
        df = yf.download(yf_symbol, period="5d", interval=interval, progress=False)
        
        if df.empty:
            return jsonify({"status": "error", "message": "No data from Yahoo"})

        signal, confidence, ind = calculate_pro_logic(df)

        # ВАЖНО: Ключи должны совпадать с JS (RSI, EMA, MACD, BB)
        return jsonify({
            "status": "success",
            "signal": signal,
            "confidence": confidence,
            "indicators": {
                "RSI": str(ind["RSI"]),
                "EMA": ind["Trend"],
                "MACD": ind["SQUEEZE"], # Отправляем Squeeze в поле MACD
                "BB": ind["Pivot"]      # Отправляем Pivot в поле BB
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
