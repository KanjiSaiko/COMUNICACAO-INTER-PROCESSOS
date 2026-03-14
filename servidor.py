import socket
import struct
import sys
import datetime as dt

IP_HOST = "0.0.0.0"

#estrutura de dados de clientes mantida pelo servidor
last_req = 0
last_num_reqs = 0
last_total_somatorio = 0

#estrutura de dados da soma agregada mantida pelo servidor
num_reqs = 0 #numero de requiscoes totais
somatorio = 0
id_req = 0 #id da req atual do cliente
date = dt.datetime.now()

cliente = {}

if len(sys.argv) > 1: 
    SERVIDOR_PORTA = int(sys.argv[1]) #pega o primeiro argumento da linha de comando

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((IP_HOST, SERVIDOR_PORTA))

    print(f"{date} server {IP_HOST} num_reqss {num_reqs} total_somatorio {somatorio}")

    while True:
        data, addr = sock.recvfrom(1024)  
        try:
            valor = struct.unpack('!i', data)[0]
            
            if(cliente["ip"] != addr) :
                id_req = 1
                cliente.update({"ip" : addr, "id_req" : id_req, "value" : valor})
                
                
            else: 
                id_req = cliente[addr]["id_req"]
                id_req += 1
                cliente[addr]["id_req"] = id_req
                cliente[addr]["value"] = valor
                
            num_reqs += 1
            somatorio += valor
            print(f"{date} client {addr} id_req {id_req} value {valor} num_reqss {num_reqs} total_sum {somatorio}")
            
            envio_somatorio = struct.pack('!i', somatorio)
            sock.sendto(somatorio, (IP_HOST, SERVIDOR_PORTA))

        except:
            print(f"Recebido dado nao numerico: {data}")

else:
    print("Nenhuma porta fornecida")


