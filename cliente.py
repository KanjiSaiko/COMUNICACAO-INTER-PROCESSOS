import socket
import sys
import datetime as dt
import processamento as pss

def main():
    req = 0
    if len(sys.argv) > 1: 
        CLIENTE_PORTA = int(sys.argv[1]) #pega o primeiro argumento da linha de comando
    else:
        print("Nenhuma porta fornecida")
        sys.exit()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #udp
    CLIENTE_IP = '255.255.255.255'
    date = dt.datetime.now()
    print(f"{date} server_addr {CLIENTE_IP}")

    pss.processamento_cliente(req, sock, CLIENTE_IP, CLIENTE_PORTA, date)