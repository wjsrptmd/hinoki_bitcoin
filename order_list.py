def get_order_list() :
    orders = open("order_list.txt")
    lines = orders.readlines()
    if len(lines) == 0 : 
        print('주문 목록이 비어있습니다.')
        return []
    
    ret = []
    for l in lines :
        coin = l.strip()
        if len(coin) > 0 :
            if coin[0] != '#' :
                ret.append(l.strip())
    return ret