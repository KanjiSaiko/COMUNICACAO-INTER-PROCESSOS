import socket
import struct
import sys
import datetime as dt
import time

CLIENTE_IP = "0.0.0.0"
date = dt.datetime.now()

if len(sys.argv) > 1: 
    CLIENTE_PORTA = int(sys.argv[1]) #pega o primeiro argumento da linha de comando
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #udp
    print(f"{date} server_addr {CLIENTE_IP}")
    numero = int(input())
    envio_int = struct.pack('!i', numero)
    sock.sendto(envio_int, (CLIENTE_IP, CLIENTE_PORTA))
    try:
        
        somatorio = struct.unpack('!i', sock.recv(1024))[0]
        
        if somatorio:
            print(f"{date} server {CLIENTE_IP} id_req {} num_req {} total_sum {somatorio}")
    except:
        print("Timer estourou")
else:
    print("Nenhuma porta fornecida")


def timer() :
    inicio = time.perf_counter()
    time.sleep(4)
    fim = fim = time.perf_counter()
    tempo_decorrido = fim - inicio
    return tempo_decorrido

