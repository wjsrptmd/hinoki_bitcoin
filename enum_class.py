from enum import Enum
import str_def

def stringToEnum(str) :
    ret = CoinStatus.none
    if str == str_def.buy :
        ret = CoinStatus.buy
    elif str == str_def.sell :
        ret = CoinStatus.sell
    elif str == str_def.end:
        ret = CoinStatus.end
    return ret

def enumToString(value) :
    ret = str_def.none
    if value == CoinStatus.buy :
        ret = str_def.buy
    elif value == CoinStatus.sell :
        ret = str_def.sell
    elif value == CoinStatus.end :
        ret = str_def.end
    return ret

class CoinStatus (Enum) :
    none = 0,
    buy = 1,
    sell = 2,
    end = 3