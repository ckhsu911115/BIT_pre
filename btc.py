import requests
import pandas as pd
import time
from ta.momentum import RSIIndicator
from flask import Flask, render_template_string
import threading

# Flask 應用初始化
app = Flask(__name__)

# Binance API 基本地址
BASE_URL = 'https://api.binance.com'

# 全局變量保存結果
sorted_results = []

# 獲取所有現貨交易對並過濾出以 "USDT" 結尾的交易對
def get_usdt_symbols():
    url = f"{BASE_URL}/api/v3/exchangeInfo"
    response = requests.get(url)
    data = response.json()
    symbols = [s['symbol'] for s in data['symbols'] if s['status'] == 'TRADING' and s['symbol'].endswith('USDT')]
    return symbols

# 獲取 K 線數據
def get_klines(symbol, interval='5m', limit=100):
    url = f"{BASE_URL}/api/v3/klines"
    params = {'symbol': symbol, 'interval': interval, 'limit': limit}
    response = requests.get(url, params=params)
    data = response.json()
    if not data or isinstance(data, dict):
        return pd.DataFrame()
    df = pd.DataFrame(data, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
    ])
    df['close'] = df['close'].astype(float)
    return df

# 計算 RSI 指標
def calculate_rsi(df):
    if df.empty:
        return df
    rsi = RSIIndicator(close=df['close'], window=14)
    df['RSI'] = rsi.rsi()
    return df

# 根據 RSI 排序並格式化輸出
def analyze_symbols():
    global sorted_results
    symbols = get_usdt_symbols()
    results = []

    for symbol in symbols:
        try:
            df = get_klines(symbol)
            if df.empty:
                continue

            df = calculate_rsi(df)
            last_rsi = df.iloc[-2]['RSI']  # 倒數第二根 K 線的 RSI 值

            results.append({'symbol': symbol, 'RSI': last_rsi})

        except Exception as e:
            print(f"處理 {symbol} 時出現錯誤: {e}")
        time.sleep(0.2)  # 控制請求速率

    # 排序 RSI 指標
    sorted_results = sorted(results, key=lambda x: x['RSI'], reverse=True)

# 每 10 分鐘執行一次掃描
def periodic_update():
    while True:
        print("開始掃描交易對...")
        analyze_symbols()
        print("掃描完成，等待 10 分鐘後再次執行...")
        time.sleep(600)  # 等待 10 分鐘

# Flask 路由定義
@app.route('/')
def index():
    global sorted_results
    table_html = """
    <table border="1">
        <tr>
            <th>交易對</th>
            <th>RSI</th>
        </tr>
    {% for result in results %}
        <tr>
            <td>{{ result.symbol }}</td>
            <td>{{ result.RSI }}</td>
        </tr>
    {% endfor %}
    </table>
    """
    return render_template_string(table_html, results=sorted_results)

if __name__ == "__main__":
    # 啟動後台定時更新任務
    threading.Thread(target=periodic_update, daemon=True).start()
    # 啟動 Flask 服務
    app.run(host='0.0.0.0', port=5000)
