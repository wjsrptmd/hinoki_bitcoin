from enum_class import CoinStatus, enumToString, stringToEnum
import json
import str_def

class COIN :
    def __init__(self, key) :
        self.key = key
        self.status = CoinStatus.none
        self.allocation = 0
        self.buy_money = 0
        self.buy_market = 0
        self.sell_money = 0
        self.sell_market = 0

    def setJsonData(self, jsonObj) :
        self.status = stringToEnum(jsonObj.get(str_def.status))
        self.allocation = int(jsonObj.get(str_def.allocation))
        self.buy_money = int(jsonObj.get(str_def.buy_money))
        self.buy_market = int(jsonObj.get(str_def.buy_market))
        self.sell_money = int(jsonObj.get(str_def.sell_money))
        self.sell_market = int(jsonObj.get(str_def.sell_market))

    def getJsonData(self) :
        data = {}
        data[str_def.status] = enumToString(self.status)
        data[str_def.allocation] = self.allocation
        data[str_def.buy_money] = self.buy_money
        data[str_def.buy_market] = self.buy_market
        data[str_def.sell_money] = self.sell_money
        data[str_def.sell_market] = self.sell_market
        return data

    def krw_key(self) :
        return str_def.krw + '-' + self.key