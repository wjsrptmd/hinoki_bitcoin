import os
import datetime
import pprint

def WriteLog(msg) :
    now = datetime.datetime.now()
    log_folder = 'log'  
    log_file = log_folder + '/' + now.strftime('%Y-%m-%d') + '_log.txt'
    os.makedirs(log_folder, exist_ok=True)

    f = open(log_file, 'a')
    now_time = now.strftime('%Y-%m-%d %H:%M:%S    ')
    f.write(now_time + msg + '\n')    
    f.close()

    pprint.pprint(msg)