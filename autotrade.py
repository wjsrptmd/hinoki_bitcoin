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
import sys

from enum_class import CoinStatus
from coin import COIN

sleep_time = 0.2

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
    time.sleep(sleep_time)
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

def get_last_min_price(df) :
    size = len(df)
    min_val = -1
    val = -1
    isUp = True
    for i in range(0, size) :
        cur_val = df['close'][i]
        if val < cur_val :
            if isUp == False :
                min_val = val
            isUp = True
        elif val > cur_val :
            isUp = False
        val = cur_val

    if isUp == False :
        min_val = -1
    return min_val

def is_time_to_buy(coin, cur_price, diff, isLog) :    
    df = pyupbit.get_ohlcv(coin.krw_key(), interval="minute1", count=100)
    min_val = get_last_min_price(df)
    ret = False
    if min_val > 0 :
        if cur_price >= min_val and cur_price <= min_val * (1 + diff/100) :
            ret = True
    
    if isLog or ret :
        msg = str('매수대기 coin : %s, 변곡점 가격 : %f, 할당금액 : %f' %(coin.key, min_val, coin.allocation))
        pprint.pprint(msg)
        log_helper.WriteLog(msg)
    
    return ret

def is_down_flow(df) :
    size = len(df)
    val = -1
    isDown = False
    for i in range(0, size) :
        cur_val = df['close'][i]
        if val == -1 :
            val = cur_val
            continue

        if val > cur_val :
            isDown = True
        elif val < cur_val :
            isDown = False
        val = cur_val

    return isDown

def is_time_to_sell(coin, cur_price, isLog) :
    df = pyupbit.get_ohlcv(coin.krw_key(), interval="minute1", count=100)
    ret = False
    if is_down_flow(df) :
        ret = coin.buy_market < cur_price
    
    if isLog or ret:
        msg = str('매도대기 coin : %s, %f 원, %f 원' %(coin.key, coin.buy_market, coin.buy_money))
        pprint.pprint(msg)
        log_helper.WriteLog(msg)
    return ret

def allocate_coins(coins, max_allocation, upbit) :
    allocation_count = 0
    for c in coins :
        if c.status != CoinStatus.sell :
            allocation_count += 1
            c.allocation = 0
            c.status = CoinStatus.none
    
    # 사용 가능 금액
    total_allocations = get_total_allocation(upbit)

    if allocation_count > 0 :
        avg_allocation = int(total_allocations / allocation_count)

        # allocation 할당
        for c in coins :
            if c.status == CoinStatus.none :
                buy_price = min(avg_allocation, max_allocation)
                if total_allocations >= buy_price :
                    c.allocation = buy_price
                    total_allocations = total_allocations - buy_price
                    c.status = CoinStatus.buy


def main(argv) :
    log_helper.WriteLog('============ Start Program ============')

    # json 파일 체크
    json_file = 'context.json'
    if os.path.exists(json_file) == False :
        msg = json_file + ' 파일이 없습니다.'
        pprint.pprint(msg)
        log_helper.WriteLog(msg)
        return

    # 고정 변수
    min_buy = 5000 # 최소 주문금액 (단위 : 원)
    max_allocation = 60000 # 최대 주문금액 (단위 : 원) 
    buy_diff = 1 # 매수 오차 (%)
    fees = 0.05 # 수수료 (%)

    # aguments 가 있을 경우
    if len(argv) > 1 :
        if len(argv) == 4 :     
            max_allocation = int(argv[1])
            buy_diff = float(argv[2])
            fees = float(argv[3])     
        else :
            msg = 'arguments 개수는 0개 또는 3개 이어야 합니다.'
            pprint.pprint(msg)         
            log_helper.WriteLog(msg)   
            return

    msg = str('최대 주문금액(코인하나당) %d, 매수 오차 %d, 수수료 %f' \
            %(max_allocation, buy_diff, fees))
    log_helper.WriteLog(msg)

    # upbit 인스턴스 생성
    a_key = access_keys.get_access()
    s_key = access_keys.get_secret()
    upbit = pyupbit.Upbit(a_key, s_key)

    # 내가 사고자 하는 코인 with 이미 매수한 코인
    coins = get_coin_list(upbit, json_file)

    time_to_log_count_limit = 30
    time_to_log_count = time_to_log_count_limit

    while is_end(coins) == False :
        try :
            is_log = False
            if time_to_log_count >= time_to_log_count_limit :
                is_log = True
                time_to_log_count = 0
                pprint.pprint(' ')
                log_helper.WriteLog(' ')
            time_to_log_count = time_to_log_count + 1
    
            allocate_coins(coins, max_allocation, upbit)
            # 매수
            for c in coins :         
                if c.status == CoinStatus.buy :
                    cur_price = get_current_price(c.krw_key())
                    time.sleep(sleep_time)
                    if is_time_to_buy(c, cur_price, buy_diff, is_log) :
                        buy_money = c.allocation * (1 - (fees / 100))
                        time.sleep(sleep_time)
                        ret = upbit.buy_market_order(c.krw_key(), buy_money)
                        if ret is None :
                            pprint.pprint("Error : 매수 실패")
                            log_helper.WriteLog("Error : 매수 실패")
                            log_helper.WriteLog(ret)
                            continue
                        
                        c.status = CoinStatus.sell
                        c.buy_money = buy_money
                        c.buy_market = cur_price
    
                        msg = str('[매수] coin : %s\t\t%s 원\t\t%s 원' %(c.key, str(c.buy_money), str(c.buy_market)))
                        pprint.pprint(msg)
                        log_helper.WriteLog(msg)
                        
                elif c.status == CoinStatus.sell :
                    cur_price = get_current_price(c.krw_key())
                    cur_price = cur_price * (1 - (fees / 100))
                    time.sleep(sleep_time)
                    if is_time_to_sell(c, cur_price, is_log) :
                        balance = upbit.get_balance(c.key)          
                        sell_money = balance * cur_price
                        if sell_money >= min_buy :
                            time.sleep(sleep_time)
                            ret = upbit.sell_market_order(c.krw_key(), balance)
                            if ret is None :
                                pprint.pprint('Error : 매도 실패')
                                log_helper.WriteLog("Error : 매도 실패")
                                log_helper.WriteLog(ret)
                                continue
                            
                            c.status = CoinStatus.none
                            c.sell_money = sell_money
                            c.sell_market = cur_price
                            diff = c.sell_money - c.buy_money
                            msg = str('[매도] coin : %s\t\t차익 : %s 원\t\t%s 원\t\t%s' %(c.key, str(diff), str(c.sell_money), str(c.sell_market)))
                            pprint.pprint(msg)
                            log_helper.WriteLog(msg)

                write_json_file(coins, json_file)
    
        except Exception as e :
            msg = str('Erro : ' + str(e))
            pprint.pprint(msg)
            log_helper.WriteLog(msg)    

    log_helper.WriteLog('============ Shutdown Program ============')


if __name__ == '__main__':
    main(sys.argv)