from flask import Flask, jsonify, request
from flask_cors import CORS
from tradingview_ta import TA_Handler, Interval

app = Flask(__name__)
CORS(app)  # Разрешает вашему сайту делать запросы к этому серверу

@app.route('/get_signal', methods=['GET'])
def get_signal():
    # Получаем параметры из запроса (например: ?symbol=BTCUSDT&interval=1m)
    symbol = request.args.get('symbol', 'BTCUSDT')
    time_val = request.args.get('interval', '1m')

    # Словарь для перевода времени в формат, понятный библиотеке TradingView
    interval_map = {
        "1m": Interval.INTERVAL_1_MINUTE,
        "5m": Interval.INTERVAL_5_MINUTES,
        "15m": Interval.INTERVAL_15_MINUTES,
        "1h": Interval.INTERVAL_1_HOUR,
    }
    
    tv_interval = interval_map.get(time_val, Interval.INTERVAL_1_MINUTE)

    try:
        # Подключаемся к аналитике TradingView
        handler = TA_Handler(
            symbol=symbol,
            exchange="BINANCE", # Для крипты используем BINANCE
            screener="crypto",
            interval=tv_interval
        )
        
        analysis = handler.get_analysis()
        
        # Возвращаем результат в формате JSON
        return jsonify({
            "status": "success",
            "signal": analysis.summary['RECOMMENDATION'], # STRONG_BUY, BUY, NEUTRAL, etc.
            "indicators": {
                "RSI": analysis.indicators['RSI'],
                "MACD": analysis.indicators['MACD.macd']
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    import os
    # Порт для Render: он сам назначит его через переменную окружения
    port = int(os.environ.get("PORT", 5001))
    app.run(host='0.0.0.0', port=port)
