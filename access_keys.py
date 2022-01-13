access_file = open("my_acces.txt")
lines = access_file.readlines()

def get_access() :
    if len(lines) < 2 : 
        print("Error : my_access.txt access 값이 없습니다.")
        return ""

    return lines[1].strip()

def get_secret() :
    if len(lines) < 3 :
        print("Error : my_access.txt secret 값이 없습니다.")
        return ""

    return lines[2].strip()
