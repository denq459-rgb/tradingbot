from flask import Flask, jsonify, request
from flask_cors import CORS
from tradingview_ta import TA_Handler, Interval

app = Flask(__name__)
CORS(app)  # Разрешает вашему сайту делать запросы к этому серверу

@app.route('/get_signal', methods=['GET'])
def get_signal():
    symbol = request.args.get('symbol', 'BTCUSDT')
    time_val = request.args.get('interval', '5m')

    # Настройки по умолчанию (для крипты)
    exchange = "BINANCE"
    screener = "crypto"

    # Если в паре нет USDT (например, EURUSD), переключаемся на Forex данные
    if "USDT" not in symbol:
        exchange = "FX_IDC"
        screener = "forex"

    interval_map = {
        "1m": Interval.INTERVAL_1_MINUTE,
        "5m": Interval.INTERVAL_5_MINUTES,
        "15m": Interval.INTERVAL_15_MINUTES,
        "1h": Interval.INTERVAL_1_HOUR,
    }
    
    tv_interval = interval_map.get(time_val, Interval.INTERVAL_5_MINUTES)

    try:
        handler = TA_Handler(
            symbol=symbol,
            exchange=exchange,
            screener=screener,
            interval=tv_interval
        )
        analysis = handler.get_analysis()
        
        return jsonify({
            "status": "success",
            "signal": analysis.summary['RECOMMENDATION'],
            "indicators": {
                "RSI": analysis.indicators['RSI']
            }
        })
    except Exception as e:
        # Если всё равно ошибка, пробуем добавить USDT в конец (для подстраховки)
        return jsonify({"status": "error", "message": "Invalid Symbol: " + symbol})

if __name__ == '__main__':
    import os
    # Порт для Render: он сам назначит его через переменную окружения
    port = int(os.environ.get("PORT", 5001))
    app.run(host='0.0.0.0', port=port)
