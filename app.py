from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import pandas_ta as ta
import requests

app = Flask(__name__)
CORS(app)  # Разрешаем запросы от Telegram

def get_binance_data(symbol, interval):
    """Получение исторических данных с Binance"""
    try:
        # Форматируем символ (например, EURUSD -> EURUSDT)
        if not symbol.endswith('USDT') and 'USD' in symbol:
            symbol = symbol.replace('USD', 'USDT')
            
        url = f"https://api.binance.com/api/v3/klines"
        params = {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": 300 # Берем 300 свечей для точности EMA 200
        }
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        
        df = pd.DataFrame(data, columns=[
            'time', 'open', 'high', 'low', 'close', 'volume', 
            'close_time', 'qav', 'num_trades', 'taker_base', 'taker_quote', 'ignore'
        ])
        df['close'] = df['close'].astype(float)
        return df
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

@app.route('/get_signal', methods=['GET'])
def get_signal():
    symbol = request.args.get('symbol', 'BTCUSDT')
    interval = request.args.get('interval', '5m')
    
    # Проверка на прогрев сервера
    if symbol == "WAKEUP":
        return jsonify({"status": "awake"})

    df = get_binance_data(symbol, interval)
    
    if df is None or df.empty:
        return jsonify({"status": "error", "message": "Failed to get data"}), 400

    # --- РАСЧЕТ ИНДИКАТОРОВ ---
    # 1. RSI
    df['rsi'] = ta.rsi(df['close'], length=14)
    
    # 2. EMA 200
    df['ema200'] = ta.ema(df['close'], length=200)
    
    # 3. MACD
    macd = ta.macd(df['close'])
    df = pd.concat([df, macd], axis=1)
    
    # 4. Bollinger Bands
    bbands = ta.bbands(df['close'], length=20, std=2)
    df = pd.concat([df, bbands], axis=1)

    # Текущие значения
    last = df.iloc[-1]
    curr_price = last['close']
    rsi_val = last['rsi']
    ema_val = last['ema200']
    
    # Логика сигналов (Score System)
    score = 0 # Положительный - BUY, отрицательный - SELL
    
    # Тренд по EMA 200
    trend = "Bullish" if curr_price > ema_val else "Bearish"
    score += 25 if trend == "Bullish" else -25
    
    # RSI логика
    rsi_status = "Neutral"
    if rsi_val < 35:
        rsi_status = "Oversold"
        score += 30
    elif rsi_val > 65:
        rsi_status = "Overbought"
        score -= 30
        
    # MACD логика
    macd_val = last['MACD_12_26_9']
    macd_sig = last['MACDs_12_26_9']
    macd_status = "Bullish Cross" if macd_val > macd_sig else "Bearish Cross"
    score += 15 if macd_status == "Bullish Cross" else -15

    # Bollinger Bands логика
    bb_status = "Inside"
    if curr_price < last['BBL_20_2.0']:
        bb_status = "Lower Band Touch"
        score += 20
    elif curr_price > last['BBU_20_2.0']:
        bb_status = "Upper Band Touch"
        score -= 20

    # Финальный вердикт
    if score >= 50:
        final_signal = "STRONG_BUY"
    elif score >= 15:
        final_signal = "BUY"
    elif score <= -50:
        final_signal = "STRONG_SELL"
    elif score <= -15:
        final_signal = "SELL"
    else:
        final_signal = "NEUTRAL"

    # Рассчитываем уверенность (Confidence)
    confidence = min(abs(score) + 20, 98) # Ограничиваем 98%

    return jsonify({
        "status": "success",
        "signal": final_signal,
        "confidence": int(confidence),
        "indicators": {
            "RSI": float(rsi_val),
            "EMA_200": trend,
            "MACD": macd_status,
            "BB": bb_status
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
