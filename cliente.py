import socket
import struct
import sys
import datetime as dt

CLIENTE_IP = "0.0.0.0"
data = dt.datetime.now()

if len(sys.argv) > 1: 
    CLIENTE_PORTA = int(sys.argv[1]) #pega o primeiro argumento da linha de comando
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #udp
    print(f"{data} server_addr {CLIENTE_IP}")
    numero = int(input())
    envio_int = struct.pack('!i', numero)
    sock.sendto(envio_int, (CLIENTE_IP, CLIENTE_PORTA))
    try:
        ack = sock.recv(1024)
        if ack:
            print(f"{data} server {CLIENTE_IP} id_req {} num_req {} total_sum {}")
else:
    print("Nenhum numero fornecido")

