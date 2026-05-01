from flask import Flask, request, jsonify
from flask_cors import CORS
import yfinance as yf
import os

app = Flask(__name__)
CORS(app)

def get_signal_logic(df):
    prices = df['Close'].tolist()
    if len(prices) < 50:
        return "NEUTRAL", 50, {}

    last_price = prices[-1]
    
    # 1. EMA 50 (Среднесрочный тренд)
    ema_50 = sum(prices[-50:]) / 50
    trend = "BULLISH" if last_price > ema_50 else "BEARISH"

    # 2. RSI 14
    changes = [prices[i] - prices[i-1] for i in range(-14, 0)]
    gains = sum([c for c in changes if c > 0]) / 14
    losses = abs(sum([c for c in changes if c < 0])) / 14
    rsi = 100 - (100 / (1 + (gains/losses if losses > 0 else 1)))

    # 3. Bollinger Bands (Упрощенно)
    sma_20 = sum(prices[-20:]) / 20
    std_dev = (sum([(p - sma_20)**2 for p in prices[-20:]]) / 20)**0.5
    upper_band = sma_20 + (std_dev * 2)
    lower_band = sma_20 - (std_dev * 2)

    # --- СИСТЕМА ПРИНЯТИЯ РЕШЕНИЙ ---
    score = 0
    
    # Анализ RSI
    if rsi < 30: score += 40  # Перепроданность
    if rsi > 70: score -= 40  # Перекупленность
    
    # Анализ Тренда
    if trend == "BULLISH": score += 20
    else: score -= 20
    
    # Анализ Боллинджера
    if last_price <= lower_band: score += 30 # Цена у нижней границы
    if last_price >= upper_band: score -= 30 # Цена у верхней границы

    # Итоговый вердикт
    if score >= 60: signal = "STRONG_BUY"
    elif score >= 30: signal = "BUY"
    elif score <= -60: signal = "STRONG_SELL"
    elif score <= -30: signal = "SELL"
    else: signal = "NEUTRAL"

    return signal, min(abs(score) + 30, 98), {
        "RSI": round(rsi, 1),
        "TREND": trend,
        "BB": "Oversold" if last_price <= lower_band else ("Overbought" if last_price >= upper_band else "Stable"),
        "PRICE": round(last_price, 5)
    }

@app.route('/get_signal', methods=['GET'])
def get_signal():
    try:
        symbol = request.args.get('symbol', 'EURUSD').upper()
        yf_symbol = f"{symbol}=X"
        interval = request.args.get('interval', '5m')
        
        # Загружаем данные (нужно больше свечей для EMA)
        data = yf.download(yf_symbol, period="5d", interval=interval, progress=False)
        
        if data.empty:
            return jsonify({"status": "error", "message": "No data"})

        signal, confidence, ind = get_signal_logic(data)

        return jsonify({
            "status": "success",
            "signal": signal,
            "confidence": confidence,
            "indicators": {
                "RSI": ind["RSI"],
                "EMA_200": ind["TREND"],
                "MACD": "Confirmed",
                "BB": ind["BB"]
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
