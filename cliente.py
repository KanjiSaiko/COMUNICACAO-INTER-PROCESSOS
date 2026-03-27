import socket
import sys
import struct
import datetime as dt
import processamento as pss

BROADCAST = '255.255.255.255'

def main():
    req = 0
    if len(sys.argv) > 1: 
        CLIENTE_PORTA = int(sys.argv[1]) #pega o primeiro argumento da linha de comando
    else:
        print("Nenhuma porta fornecida")
        sys.exit()

    #DESCOBERTA ATRAVES DE BROADCAST
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #udp
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1) #ativa broadcast
    sock.sendto(b"discover", (BROADCAST, CLIENTE_PORTA))

    CLIENTE_IP = sock.recvfrom(1024)[1][0]


    date = dt.datetime.now()
    print(f"{date.strftime('%Y-%m-%d %H:%M:%S')} server addr {CLIENTE_IP}")

    pss.processamento_cliente(req, sock, CLIENTE_IP, CLIENTE_PORTA, date)