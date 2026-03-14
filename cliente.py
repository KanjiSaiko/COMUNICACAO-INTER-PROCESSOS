import socket
import struct
import sys
import datetime as dt

def main():
    if len(sys.argv) > 1: 
        CLIENTE_PORTA = int(sys.argv[1]) #pega o primeiro argumento da linha de comando

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) #udp
        CLIENTE_IP = '255.255.255.255'
        date = dt.datetime.now()
        print(f"{date} server_addr {CLIENTE_IP}")
        while(True):
            numero = int(input())
            envio_int = struct.pack('!i', numero)
        
            try:
                sock.sendto(envio_int, (CLIENTE_IP, CLIENTE_PORTA)) #envia numero

                data, addr = sock.recvfrom(1024) #recebe somatorio
                id_req, num_reqs, somatorio = struct.unpack('!iii', data)
                
                if somatorio:
                    print(f"{date} server {CLIENTE_IP} id_req {id_req} value {numero} num_reqs {num_reqs} total_sum {somatorio}")
            except:
                print("Timer estourou")
    else:
        print("Nenhuma porta fornecida")