from flask import Flask, request, jsonify
import alpaca_trade_api as tradeapi
import os
import threading
import time
import datetime
import pytz

app = Flask(__name__)

API_KEY    = os.environ.get('ALPACA_API_KEY')
SECRET_KEY = os.environ.get('ALPACA_SECRET_KEY')
BASE_URL   = 'https://paper-api.alpaca.markets'

api = tradeapi.REST(API_KEY, SECRET_KEY, BASE_URL)

INITIAL_SEED = 100000  # ✅ 본인 시드로 변경
BUY_PERCENT  = 5

positions = {}

@app.route('/')
def home():
    return 'Trading Bot Running!'

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.json
    if not data:
        return jsonify({'error': 'No data'}), 400

    action     = data.get('action')
    ticker     = data.get('ticker')
    stop_price = data.get('stop_price')

    try:
        if action == 'BUY':
            bars  = api.get_latest_bar(ticker)
            price = bars.c

            amount = INITIAL_SEED * (BUY_PERCENT / 100)
            qty    = int(amount / price)

            if qty < 1:
                return jsonify({'error': '잔액 부족'}), 400

            api.submit_order(
                symbol=ticker,
                qty=qty,
                side='buy',
                type='market',
                time_in_force='gtc'
            )

            positions[ticker] = {
                'qty':         qty,
                'entry_price': price,
                'stop_price':  float(stop_price) if stop_price else None
            }

            return jsonify({
                'status':      'BUY 완료',
                'ticker':      ticker,
                'qty':         qty,
                'entry_price': price,
                'stop_price':  stop_price
            })

        elif action == 'SELL':
            try:
                position = api.get_position(ticker)
                qty      = int(float(position.qty))
            except:
                return jsonify({'error': '보유 주식 없음'}), 400

            api.submit_order(
                symbol=ticker,
                qty=qty,
                side='sell',
                type='market',
                time_in_force='gtc'
            )

            if ticker in positions:
                del positions[ticker]

            return jsonify({'status': 'SELL 익절 완료', 'ticker': ticker, 'qty': qty})

        else:
            return jsonify({'error': '알 수 없는 action'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500


def check_stoploss():
    while True:
        try:
            et  = pytz.timezone('America/New_York')
            now = datetime.datetime.now(et)

            # 장 마감 후 16:05 ~ 16:10 에만 체크
            if now.hour == 16 and 5 <= now.minute <= 10:
                for ticker, info in list(positions.items()):
                    stop_price = info.get('stop_price')
                    if not stop_price:
                        continue

                    bars  = api.get_latest_bar(ticker)
                    close = bars.c

                    if close < stop_price:
                        try:
                            position = api.get_position(ticker)
                            qty      = int(float(position.qty))

                            api.submit_order(
                                symbol=ticker,
                                qty=qty,
                                side='sell',
                                type='market',
                                time_in_force='gtc'
                            )

                            del positions[ticker]
                            print(f"{ticker} 손절! 종가 {close} < 손절선 {stop_price}")

                        except Exception as e:
                            print(f"손절 실패: {e}")

        except Exception as e:
            print(f"오류: {e}")

        time.sleep(60)


thread = threading.Thread(target=check_stoploss, daemon=True)
thread.start()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
