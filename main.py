from flask import Flask, request, jsonify
import pyupbit
import os
import threading
import time

app = Flask(__name__)

ACCESS_KEY = os.environ.get('UPBIT_ACCESS_KEY')
SECRET_KEY = os.environ.get('UPBIT_SECRET_KEY')

upbit = pyupbit.Upbit(ACCESS_KEY, SECRET_KEY)

BUY_PERCENT = 100  # 보유 현금의 100% 매수

@app.route('/')
def home():
    return 'Upbit Trading Bot Running!'

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if not data:
        return jsonify({'error': 'No data'}), 400

    action = data.get('action')
    ticker = data.get('ticker', 'KRW-BTC')

    try:
        if action == 'BUY':
            krw_balance = upbit.get_balance("KRW")
            if krw_balance is None or krw_balance < 5000:
                return jsonify({'error': '잔액 부족 (최소 5000원)'}), 400

            buy_amount = krw_balance * (BUY_PERCENT / 100)
            result = upbit.buy_market_order(ticker, buy_amount)
            print(f"매수 완료: {ticker} / {buy_amount}원 / {result}")

            return jsonify({
                'status': 'BUY 완료',
                'ticker': ticker,
                'amount': buy_amount,
                'result': str(result)
            })

        elif action == 'SELL':
            coin = ticker.replace('KRW-', '')
            coin_balance = upbit.get_balance(coin)

            if coin_balance is None or coin_balance <= 0:
                return jsonify({'error': '보유 코인 없음'}), 400

            result = upbit.sell_market_order(ticker, coin_balance)
            print(f"매도 완료: {ticker} / {coin_balance}개 / {result}")

            return jsonify({
                'status': 'SELL 완료',
                'ticker': ticker,
                'qty': coin_balance,
                'result': str(result)
            })

        else:
            return jsonify({'error': '알 수 없는 action'}), 400

    except Exception as e:
        print(f"오류: {e}")
        return jsonify({'error': str(e)}), 500


def keep_alive():
    while True:
        try:
            import requests
            url = os.environ.get('RAILWAY_URL', 'http://localhost:5000')
            requests.get(url + '/')
        except:
            pass
        time.sleep(300)

thread = threading.Thread(target=keep_alive, daemon=True)
thread.start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
