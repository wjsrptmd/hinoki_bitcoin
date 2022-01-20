import time
import sys
from turtle import isdown
import pyupbit
import access_keys
import order_list
import json
import os.path
import str_def
import log_helper

from enum_class import CoinStatus
from coin import COIN

sleep_time = 1
buy_count = 30

def write_json_file(coins, json_file) :
    data = {}
    for c in coins :
        if c.status != CoinStatus.none :
            data[c.key] = c.getJsonData()

    with open(json_file, 'w') as f :
        json.dump(data, f)
    return data

def get_coin_list(upbit) :
    orders = order_list.get_order_list()
    balances = upbit.get_balances()
    ret = []
    for key in orders :
        c = COIN(key)
        c.status = CoinStatus.buy
        ret.append(c)

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
            new_coin.status = CoinStatus.end
            ret.append(new_coin)

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

def get_last_min_price(df) :
    min_val = -1.0
    val = -1
    isUp = True
    size = len(df)
    for i in range(0, size) :
        cur_val = (df['open'][i] + df['close'][i]) / 2
        if val < cur_val :
            if isUp == False :
                min_val = min(df['open'][i], df['close'][i])
            isUp = True
        elif val > cur_val :
            isUp = False
        val = cur_val
    
    if isUp == False :
        min_val = -1.0

    return min_val

def is_time_to_buy(coin, df, cur_price, diff, isLog) :    
    min_val = get_last_min_price(df)
    ret = False

    if min_val > 0 :
        if cur_price >= min_val and cur_price <= min_val * (1 + (diff/100)) :
            ret = True

    if coin.count > 0 :
        coin.count = coin.count - 1

    if coin.count > 0 :
        ret = False

    if isLog or ret :
        msg = str('매수대기 coin : %s, 변곡점 가격 : %f, 현재가격 : %f,  할당금액 : %f' %(coin.key, min_val, cur_price, coin.allocation))
        log_helper.WriteLog(msg)

    return ret

def is_down_flow(df) :
    val = -1
    isDown = False
    size = len(df)
    for i in range(0, size) :
        cur_val = (df['open'][i] + df['close'][i]) / 2
        if val == -1 :
            val = cur_val
            continue

        if val >= cur_val :
            isDown = True
        elif val < cur_val :
            isDown = False
        val = cur_val

    return isDown

def is_time_to_sell(coin, cur_price, diff, isLog) :
    ret = False
    cm = coin.buy_market * (1 + (diff / 100))
    isDown = coin.prev_price > cur_price
    down_str = '-'

    if isDown :
        down_str = '▽'
        if cm < cur_price :
            ret = True
    elif coin.prev_price < cur_price :
        down_str = '△'

    coin.prev_price = cur_price

    if isLog or ret:
        msg = str('매도대기 coin : %s, 매도 목표가 %f 원, 시가 %f 원 %s' %(coin.key, cm, cur_price, down_str))
        log_helper.WriteLog(msg)

    return ret

def allocate_coins(coins, max_allocation, upbit) :
    allocation_count = 0
    for c in coins :
        if c.status == CoinStatus.buy :
            allocation_count += 1
            c.allocation = 0
    
    # 사용 가능 금액
    total_allocations = get_total_allocation(upbit)

    if allocation_count > 0 :
        avg_allocation = int(total_allocations / allocation_count)

    # allocation 할당
    for c in coins :
        if c.status == CoinStatus.buy :
            buy_price = min(avg_allocation, max_allocation)
            if total_allocations >= buy_price :
                c.allocation = buy_price
                total_allocations = total_allocations - buy_price


def main(argv) :
    log_helper.WriteLog('============ Start Program ============')
    
    # json 파일 체크
    json_file = 'context.json'
    if os.path.exists(json_file) == False :
        msg = json_file + ' 파일이 없습니다.'
        log_helper.WriteLog(msg)
        return

    # 고정 변수
    min_buy = 5000 # 최소 주문금액 (단위 : 원)
    max_allocation = 60000 # 최대 주문금액 (단위 : 원) 
    buy_diff = 1 # 매수 오차 (%)
    sell_diff = 1 # 매도 오차 (%)
    fees = 0.05 # 수수료 (%)

    # aguments 가 있을 경우
    if len(argv) > 1 :
        if len(argv) == 5 :     
            max_allocation = int(argv[1])
            buy_diff = float(argv[2])
            sell_diff = float(argv[3])
            fees = float(argv[4])     
        else :
            msg = 'arguments 개수는 0개 또는 4개 이어야 합니다.'
            log_helper.WriteLog(msg)   
            return

    msg = str('최대 주문금액(코인하나당) %d, 매수 오차 %f, 매도 오차 %f, 수수료 %f' \
            %(max_allocation, buy_diff, sell_diff, fees))
    log_helper.WriteLog(msg)

    # upbit 인스턴스 생성
    a_key = access_keys.get_access()
    s_key = access_keys.get_secret()
    upbit = pyupbit.Upbit(a_key, s_key)

    # 내가 사고자 하는 코인 with 이미 매수한 코인
    coins = get_coin_list(upbit)
    
    time_to_log_count_limit = 1
    time_to_log_count = time_to_log_count_limit
    
    isFinish = False
    while isFinish == False :
        is_log = False
        if time_to_log_count >= time_to_log_count_limit :
            is_log = True
            time_to_log_count = 0
            log_helper.WriteLog(' ')
        time_to_log_count = time_to_log_count + 1

        allocate_coins(coins, max_allocation, upbit)

        # 매수
        for c in coins :   
            try :
                msg = ''
                cur_price = pyupbit.get_current_price(c.krw_key())

                if c.status == CoinStatus.buy :                    
                    df = pyupbit.get_ohlcv(c.krw_key(), interval="minute1", count=20)  
                    if c.allocation >= min_buy and is_time_to_buy(c, df, cur_price, buy_diff, is_log) :
                        buy_money = c.allocation * (0.9)
                        ret = upbit.buy_market_order(c.krw_key(), buy_money)
                        if ret is None :
                            log_helper.WriteLog("Error : 매수 실패")
                            log_helper.WriteLog(ret)
                            continue
                        
                        c.status = CoinStatus.sell
                        c.buy_money = buy_money * (1 + (fees) / 100)
                        c.buy_market = cur_price
                        msg = str('[매수] coin : %s\t\t%s 원\t\t%s 원' %(c.key, str(c.buy_money), str(c.buy_market)))
                        log_helper.WriteLog(msg)

                elif c.status == CoinStatus.sell :
                    if is_time_to_sell(c, cur_price, sell_diff, is_log) :
                        balance = upbit.get_balance(c.key)          
                        sell_money = balance * cur_price
                        ret = upbit.sell_market_order(c.krw_key(), balance)
                        if ret is None :
                            log_helper.WriteLog("Error : 매도 실패")
                            log_helper.WriteLog(ret)
                            continue
                        c.status = CoinStatus.buy
                        c.sell_money = sell_money
                        c.sell_market = cur_price
                        c.count = buy_count
                        diff = (c.sell_market - c.buy_market) * balance * (1 - (fees / 100))
                        msg = str('[매도] coin : %s\t\t차익 : %s 원\t\t%s 원\t\t%s' %(c.key, str(diff), str(c.sell_money), str(c.sell_market)))
                        log_helper.WriteLog(msg)

                elif c.status == CoinStatus.end :
                    balance = upbit.get_balance(c.key)          
                    sell_money = balance * cur_price
                    ret = upbit.sell_market_order(c.krw_key(), balance)
                    if ret is None :
                        log_helper.WriteLog("Error : 매도 실패")
                        log_helper.WriteLog(ret)
                        continue
                    c.status = CoinStatus.none
                    diff = (c.sell_market - c.buy_market) * balance * (1 - (fees / 100))
                    msg = str('[매도] coin : %s\t\t차익 : %s 원\t\t%s 원\t\t%s' %(c.key, str(diff), str(c.sell_money), str(c.sell_market)))
                    log_helper.WriteLog(msg)

                write_json_file(coins, json_file)
                time.sleep(0.1)
            except Exception as e :
                msg = str('Error : ' + str(e))
                log_helper.WriteLog(msg)
        time.sleep(sleep_time)
        isFinish = is_end(coins)

    log_helper.WriteLog('============ Shutdown Program ============')


if __name__ == '__main__':
    main(sys.argv)