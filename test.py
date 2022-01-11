import pyupbit

access = "14uqyxiicQkLQl1f3qteM0CXNv3UDAWxNo8xyxfV"          # 본인 값으로 변경
secret = "Ft3DSPIikfGG0DSVYig5ljZqokky1eq8rNxqNE1V"          # 본인 값으로 변경
upbit = pyupbit.Upbit(access, secret)

print(upbit.get_balance("KRW-XRP"))     # KRW-XRP 조회
print(upbit.get_balance("KRW"))  