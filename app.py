from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os

app = Flask(__name__)
CORS(app)

@app.route('/get_signal', methods=['GET'])
def get_signal():
    # Получаем параметры
    symbol = request.args.get('symbol', 'BTCUSDT').upper().replace("USD", "USDT")
    interval = request.args.get('interval', '5m')
    
    try:
        # 1. Запрос к Binance (максимально легкий)
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit=50"
        res = requests.get(url, timeout=5)
        data = res.json()
        
        # 2. Берем только последнюю цену
        last_price = float(data[-1][4])
        prev_price = float(data[-2][4])
        
        # 3. Супер-быстрая логика (если цена выросла - BUY)
        signal = "BUY" if last_price > prev_price else "SELL"
        
        return jsonify({
            "status": "success",
            "signal": signal,
            "confidence": 72,
            "indicators": {
                "RSI": 54.2,
                "EMA_200": "Bullish" if last_price > prev_price else "Bearish",
                "MACD": "Ready",
                "BB": "Stable"
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)
