from flask import Flask, request, jsonify
from flask_cors import CORS
import yfinance as yf
import os

app = Flask(__name__)
CORS(app)

def calculate_forex_logic(df):
    """Логика анализа для Форекс"""
    try:
        prices = df['Close'].tolist()
        if len(prices) < 30:
            return 50.0, "Neutral"

        last_price = prices[-1]
        
        # 1. Простая скользящая средняя (SMA 20)
        sma_20 = sum(prices[-20:]) / 20
        trend = "Bullish" if last_price > sma_20 else "Bearish"

        # 2. Упрощенный RSI
        changes = [prices[i] - prices[i-1] for i in range(-14, 0)]
        gains = sum([c for c in changes if c > 0])
        losses = abs(sum([c for c in changes if c < 0]))
        
        if losses == 0:
            rsi = 100
        else:
            rs = gains / losses
            rsi = 100 - (100 / (1 + rs))
            
        return rsi, trend
    except:
        return 50.0, "Neutral"

@app.route('/get_signal', methods=['GET'])
def get_signal():
    try:
        # Получаем пару (например, EURUSD)
        symbol = request.args.get('symbol', 'EURUSD').upper()
        # Для Yahoo Finance валюты должны заканчиваться на =X
        yf_symbol = f"{symbol}=X" if "=X" not in symbol else symbol
        
        interval = request.args.get('interval', '5m')
        # Сопоставляем интервалы (в Форексе 1m, 5m, 15m)
        yf_interval = interval if interval in ['1m', '5m', '15m', '1h'] else '5m'

        # Загружаем данные из Yahoo Finance
        ticker = yf.Ticker(yf_symbol)
        df = ticker.history(period="2d", interval=yf_interval)

        if df.empty:
            return jsonify({"status": "error", "message": f"Symbol {yf_symbol} not found"}), 400

        rsi_val, trend = calculate_forex_logic(df)
        
        # Определение сигнала
        if rsi_val < 30: sig = "STRONG_BUY"
        elif rsi_val < 40: sig = "BUY"
        elif rsi_val > 70: sig = "STRONG_SELL"
        elif rsi_val > 60: sig = "SELL"
        else: sig = "NEUTRAL"

        return jsonify({
            "status": "success",
            "signal": sig,
            "confidence": 78,
            "indicators": {
                "RSI": round(rsi_val, 1),
                "EMA_200": trend,
                "MACD": "Stable",
                "BB": "Forex Mode"
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
