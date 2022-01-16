from itertools import count
import time
import sys
import pyupbit
import access_keys
import order_list
import json
import os.path
import str_def
import pprint
import log_helper

from enum_class import CoinStatus
from coin import COIN

def write_json_file(coins, json_file) :
    data = {}
    for c in coins :
        if c.status != CoinStatus.none :
            data[c.key] = c.getJsonData()

    with open(json_file, 'w') as f :
        json.dump(data, f)
    return data

def get_coin_list(upbit, json_file) :
    orders = order_list.get_order_list()
    balances = upbit.get_balances()
    ret = []
    for order in orders :
        ret.append(COIN(order))

    for b in balances :
        coin_name = b['currency']
        if coin_name == str_def.krw :
            continue

        isIn = False
        for coin in ret :
            if coin.key == coin_name :
                coin.status = CoinStatus.sell
                coin.buy_market = float(b['avg_buy_price'])
                coin.buy_money = float(b['balance']) * coin.buy_market
                isIn = True

        if isIn == False :
            new_coin = COIN(coin_name)
            coin.status = CoinStatus.sell
            coin.buy_market = float(b['avg_buy_price'])
            coin.buy_money = float(b['balance']) * coin.buy_market
            ret.append[new_coin]

    f = open(json_file, 'r')
    data = json.load(f)
    for coin in ret :
        if coin.status == CoinStatus.sell :
            if coin.key in data :
                coin.setJsonData(data[coin.key])
    
    f.close()
    return ret

def get_total_allocation(upbit) :
    ret = 0
    balances = upbit.get_balances()
    for b in balances :
        coin_name = b['currency']
        if coin_name == str_def.krw :
            ret = int(float(b['balance']))
            break
    return ret

def is_end(coins) :
    if len(coins) == 0 :
        return True
    
    ret = True
    for c in coins :
        if c.status is not CoinStatus.none:
            ret = False
            break
    return ret

def get_current_price(ticker):
    return pyupbit.get_orderbook(ticker=ticker)["orderbook_units"][0]["ask_price"]    

# 종가기준으로 평균 계산
def get_days_avg_price(df, day_count):
    if day_count <= 0 :
        pprint.pprint('Error : day_count 가 0 이상이어야 합니다. df_count : ', day_count)
        return 0

    total_close = 0
    for d in df['close'] :
        total_close += float(d)
        
    return total_close / day_count

def is_time_to_buy(coin, cur_price, days, isLog) :    
    df = pyupbit.get_ohlcv(coin.krw_key(), interval="day", count=days)
    target_column = 'open'
    last_idx = len(df) - 1
    if last_idx - 1 >= 0 : 
        target_column = 'close'
        last_idx = last_idx - 1

    today_price = df[target_column][last_idx]
    day_avg_price = get_days_avg_price(df, days)

    if isLog :
        msg = str('매수대기 coin : %s, 평균가 : %s, 어제종가 : %s, 시가 : %s' %(coin.key, str(day_avg_price), str(today_price), str(cur_price)))
        pprint.pprint(msg)
        log_helper.WriteLog(msg)

    if day_avg_price < today_price :
        return False
    if today_price < cur_price :
        return False
    return True 

def is_time_to_sell(coin, cur_price, target_price, k, isLog) :
    t = (target_price * (1 + (k / 100)))
    if isLog :
        msg = str('매도대기 coin : %s, 시가 : %s, 목표가 : %s' %(coin.key, str(cur_price), str(t)))
        log_helper.WriteLog(msg)

    return cur_price >= (target_price * (1 + (k / 100)))

def allocate_coins(coins, max_allocation, upbit, min_buy) :
    allocation_count = 0
    for c in coins :
        if c.status != CoinStatus.sell :
            allocation_count += 1
            c.allocation = 0
            c.status = CoinStatus.none
    
    # 사용 가능 금액
    total_allocations = min(max_allocation, get_total_allocation(upbit))

    if allocation_count > 0 :
        avg_allocation = int(total_allocations / allocation_count)

        # allocation 할당
        for c in coins :
            if c.status == CoinStatus.none :
                buy_price = max(avg_allocation, min_buy)
                if total_allocations >= buy_price :
                    c.allocation = buy_price
                    total_allocations = total_allocations - buy_price
                    c.status = CoinStatus.buy


def main(argv) :
    log_helper.WriteLog('============ Start Program ============')

    # json 파일 체크
    json_file = 'context.json'
    if os.path.exists(json_file) == False :
        pprint.pprint(json_file + ' 파일이 없습니다.')
        return

    # 고정 변수
    min_buy = 6000 # 최소 주문금액 (단위 : 원)
    max_allocation = 60000 # 최대 주문금액 (단위 : 원) 
    day_count = 5 # 시세조회 횟수 (단위 : day)
    fees = 0.05 # 수수료 (%)
    plus_per = 1 # 수익률 (%)

    # aguments 가 있을 경우
    if len(argv) > 1 :
        if len(argv) == 6 :     
            min_buy = int(argv[1])
            max_allocation = int(argv[2])
            day_count = int(argv[3])
            fees = float(argv[4])
            plus_per = float(argv[5])       
        else :
            msg = 'arguments 개수는 0개 또는 5개 이어야 합니다.'
            pprint.pprint(msg)         
            log_helper.WriteLog(msg)   
            return

    msg = str('최소 주문금액 %d, 최대 주문금액 %d, 시세조회 횟수 %d, 수수료 %f, 수익률 %f' \
            %(min_buy, max_allocation, day_count, fees, plus_per))
    log_helper.WriteLog(msg)

    # upbit 인스턴스 생성
    a_key = access_keys.get_access()
    s_key = access_keys.get_secret()
    upbit = pyupbit.Upbit(a_key, s_key)

    # 내가 사고자 하는 코인 with 이미 매수한 코인
    coins = get_coin_list(upbit, json_file)

    time_to_log_count_limit = 5
    time_to_log_count = time_to_log_count_limit
    while is_end(coins) == False :
        is_log = False
        if time_to_log_count >= time_to_log_count_limit :
            is_log = True
            time_to_log_count = 0
            print(' ')
        time_to_log_count = time_to_log_count + 1

        allocate_coins(coins, max_allocation, upbit, min_buy)
        # 매수
        for c in coins :
            time.sleep(1)
            cur_price = get_current_price(c.krw_key())
            if c.status == CoinStatus.buy :
                if is_time_to_buy(c, cur_price, day_count, is_log) :
                    buy_money = c.allocation * (1 - (fees / 100))
                    ret = upbit.buy_market_order(c.krw_key(), buy_money)
                    if ret is None :
                        pprint.pprint("Error : 매수 실패")
                        continue

                    c.status = CoinStatus.sell
                    c.buy_money = buy_money
                    c.buy_market = cur_price

                    msg = str('[매수] %s 원\t\tcoin : %s\t%s' %(str(c.buy_money), c.key, str(c.buy_market)))
                    pprint.pprint(msg)
                    log_helper.WriteLog(msg)
                    
            elif c.status == CoinStatus.sell :
                if is_time_to_sell(c, cur_price, c.buy_market, plus_per, is_log) :
                    balance = upbit.get_balance(c.key)                
                    sell_money = balance * cur_price * (1 - (fees / 100))
                    if sell_money >= min_buy :
                        ret = upbit.sell_market_order(c.krw_key(), balance)
                        if ret is None :
                            pprint.pprint('Error : 매도 실패')
                            continue

                        c.status = CoinStatus.none
                        c.sell_money = sell_money
                        c.sell_market = cur_price
                        diff = c.sell_money - c.buy_money
                        msg = str('[매도] %s 원\t\t차익 : %s\t\tcoin : %s\t%s' %(str(c.sell_money), str(diff), c.key, str(c.sell_market)))
                        pprint.pprint(msg)
                        log_helper.WriteLog(msg)
            if is_log :
                pprint.pprint(write_json_file(coins, json_file))
            else :            
                write_json_file(coins, json_file)

        time.sleep(5)

    log_helper.WriteLog('============ Shutdown Program ============')


if __name__ == '__main__':
    main(sys.argv)