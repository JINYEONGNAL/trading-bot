from flask import Flask, request, jsonify
import alpaca_trade_api as tradeapi
import os

app = Flask(__name__)

# Alpaca 설정
API_KEY    = os.environ.get('ALPACA_API_KEY')
SECRET_KEY = os.environ.get('ALPACA_SECRET_KEY')
BASE_URL   = 'https://paper-api.alpaca.markets'

api = tradeapi.REST(API_KEY, SECRET_KEY, BASE_URL)

@app.route('/')
def home():
    return 'Trading Bot Running!'

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if not data:
        return jsonify({'error': 'No data'}), 400

    action = data.get('action')   # BUY or SELL
    ticker = data.get('ticker')   # 예: AAPL
    qty    = data.get('qty', 1)   # 수량 기본 1주

    try:
        if action == 'BUY':
            api.submit_order(
                symbol=ticker,
                qty=qty,
                side='buy',
                type='market',
                time_in_force='gtc'
            )
            return jsonify({'status': 'BUY 완료', 'ticker': ticker})

        elif action == 'SELL':
            api.submit_order(
                symbol=ticker,
                qty=qty,
                side='sell',
                type='market',
                time_in_force='gtc'
            )
            return jsonify({'status': 'SELL 완료', 'ticker': ticker})

        else:
            return jsonify({'error': '알 수 없는 action'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
