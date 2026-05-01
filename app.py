from flask import Flask, request, jsonify
from flask_cors import CORS
import yfinance as yf
import os
import math

app = Flask(__name__)
CORS(app)

def calculate_advanced_logic(df):
    prices = df['Close'].tolist()
    highs = df['High'].tolist()
    lows = df['Low'].tolist()
    volumes = df['Volume'].tolist()
    
    if len(prices) < 50:
        return "NEUTRAL", 50, {}

    last_close = prices[-1]
    
    # --- 1. PROFESSIONAL PIVOT POINTS (Уровни банков) ---
    # Берем данные за вчерашний полный день
    prev_high = highs[-2]
    prev_low = lows[-2]
    prev_close = prices[-2]
    
    pivot = (prev_high + prev_low + prev_close) / 3
    r1 = (2 * pivot) - prev_low  # Сопротивление 1
    s1 = (2 * pivot) - prev_high # Поддержка 1

    # --- 2. TTM SQUEEZE LOGIC (Индикатор взрыва волатильности) ---
    # (Упрощенная модель: Bollinger vs Keltner)
    sma_20 = sum(prices[-20:]) / 20
    std_dev = math.sqrt(sum([(p - sma_20)**2 for p in prices[-20:]]) / 20)
    
    upper_bb = sma_20 + (2 * std_dev)
    lower_bb = sma_20 - (2 * std_dev)
    
    # Канал Кельтнера (упрощенно)
    atr = sum([highs[i] - lows[i] for i in range(-14, 0)]) / 14
    upper_kc = sma_20 + (1.5 * atr)
    lower_kc = sma_20 - (1.5 * atr)
    
    # Если Боллинджер внутри Кельтнера - рынок "сжат" (Squeeze)
    is_squeeze = upper_bb < upper_kc and lower_bb > lower_kc

    # --- 3. RSI & TREND ---
    ema_50 = sum(prices[-50:]) / 50
    changes = [prices[i] - prices[i-1] for i in range(-14, 0)]
    gains = sum([c for c in changes if c > 0]) / 14
    losses = abs(sum([c for c in changes if c < 0])) / 14
    rsi = 100 - (100 / (1 + (gains/losses if losses > 0 else 1)))

    # --- СИСТЕМА ПРИНЯТИЯ РЕШЕНИЯ ---
    score = 0
    
    # Анализ уровней
    if last_close <= s1: score += 30 # Цена на сильной поддержке
    if last_close >= r1: score -= 30 # Цена на сильном сопротивлении
    
    # Анализ Squeeze
    if not is_squeeze: # Входим только если рынок вышел из спячки
        if rsi < 35: score += 25
        if rsi > 65: score -= 25
    
    # Тренд
    if last_close > ema_50: score += 15
    else: score -= 15

    # Финальный сигнал
    if score >= 50: signal = "STRONG_BUY"
    elif score >= 20: signal = "BUY"
    elif score <= -50: signal = "STRONG_SELL"
    elif score <= -20: signal = "SELL"
    else: signal = "NEUTRAL"

    return signal, min(abs(score) + 40, 98), {
        "RSI": round(rsi, 1),
        "PIVOT": "Support" if last_close <= s1 else ("Resist" if last_close >= r1 else "Mid"),
        "SQUEEZE": "FIRE" if not is_squeeze else "WAIT",
        "TREND": "Bullish" if last_close > ema_50 else "Bearish"
    }

@app.route('/get_signal', methods=['GET'])
def get_signal():
    try:
        symbol = request.args.get('symbol', 'EURUSD').upper()
        yf_symbol = f"{symbol}=X"
        interval = request.args.get('interval', '5m')
        
        data = yf.download(yf_symbol, period="5d", interval=interval, progress=False)
        
        if data.empty:
            return jsonify({"status": "error", "message": "No data"})

        signal, confidence, ind = calculate_advanced_logic(data)

        return jsonify({
            "status": "success",
            "signal": signal,
            "confidence": confidence,
            "indicators": {
                "RSI": ind["RSI"],
                "EMA_200": ind["TREND"],
                "MACD": ind["SQUEEZE"],
                "BB": ind["PIVOT"]
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
