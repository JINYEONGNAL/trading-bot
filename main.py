from flask import Flask, request, jsonify
import os
import threading
import time
import datetime
import pytz
from pybit.unified_trading import HTTP

app = Flask(__name__)

# 바이비트 테스트넷 설정
API_KEY    = os.environ.get('BYBIT_API_KEY')
SECRET_KEY = os.environ.get('BYBIT_SECRET_KEY')

session = HTTP(
    testnet=True,
    api_key=API_KEY,
    api_secret=SECRET_KEY
)

INITIAL_SEED = 10000  # ✅ 테스트넷 시드 금액 (USDT)
BUY_PERCENT  = 5      # 시드의 5% 매수

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
    ticker     = data.get('ticker', 'BTCUSDT')
    stop_price = data.get('stop_price')

    try:
        if action == 'BUY':
            # 현재 가격 조회
            result = session.get_tickers(category="spot", symbol=ticker)
            price  = float(result['result']['list'][0]['lastPrice'])

            # 시드의 5% 매수
            amount = INITIAL_SEED * (BUY_PERCENT / 100)
            qty    = round(amount / price, 6)

            if qty <= 0:
                return jsonify({'error': '수량 부족'}), 400

            # 매수 주문
            session.place_order(
                category="spot",
                symbol=ticker,
                side="Buy",
                orderType="Market",
                qty=str(qty)
            )

            positions[ticker] = {
                'qty':        qty,
                'entry_price': price,
                'stop_price': float(stop_price) if stop_price else None
            }

            return jsonify({
                'status':      'BUY 완료',
                'ticker':      ticker,
                'qty':         qty,
                'entry_price': price,
                'stop_price':  stop_price
            })

        elif action == 'SELL':
            # 보유 수량 조회
            result = session.get_wallet_balance(accountType="UNIFIED")
            coins  = result['result']['list'][0]['coin']
            symbol = ticker.replace('USDT', '')
            qty    = 0

            for coin in coins:
                if coin['coin'] == symbol:
                    qty = float(coin['walletBalance'])
                    break

            if qty <= 0:
                return jsonify({'error': '보유 코인 없음'}), 400

            # 매도 주문
            session.place_order(
                category="spot",
                symbol=ticker,
                side="Sell",
                orderType="Market",
                qty=str(round(qty, 6))
            )

            if ticker in positions:
                del positions[ticker]

            return jsonify({'status': 'SELL 완료', 'ticker': ticker, 'qty': qty})

        else:
            return jsonify({'error': '알 수 없는 action'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# 손절 체크
def check_stoploss():
    while True:
        try:
            for ticker, info in list(positions.items()):
                stop_price = info.get('stop_price')
                if not stop_price:
                    continue

                # 현재 가격 조회
                result = session.get_tickers(category="spot", symbol=ticker)
                price  = float(result['result']['list'][0]['lastPrice'])

                if price < stop_price:
                    try:
                        symbol = ticker.replace('USDT', '')
                        result2 = session.get_wallet_balance(accountType="UNIFIED")
                        coins   = result2['result']['list'][0]['coin']
                        qty     = 0

                        for coin in coins:
                            if coin['coin'] == symbol:
                                qty = float(coin['walletBalance'])
                                break

                        if qty > 0:
                            session.place_order(
                                category="spot",
                                symbol=ticker,
                                side="Sell",
                                orderType="Market",
                                qty=str(round(qty, 6))
                            )
                            del positions[ticker]
                            print(f"{ticker} 손절! 현재가 {price} < 손절선 {stop_price}")

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
