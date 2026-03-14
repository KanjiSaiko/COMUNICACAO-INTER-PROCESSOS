import socket
import struct
import sys
import datetime as dt
import pandas as pd

def salvaCSV(cliente, soma_server):
    table1 = pd.DataFrame(cliente)
    table2 = pd.DataFrame(soma_server)

    table1.to_csv('table1.csv', index=False, encoding='utf-8-sig')
    table2.to_csv('table2.csv', index=False, encoding='utf-8-sig')

def main():
    IP_HOST = '255.255.255.255'
    #estrutura de dados de clientes mantida pelo servidor
    last_req = 0

    #estrutura de dados da soma agregada mantida pelo servidor
    num_reqs = 0 #numero de requiscoes totais
    somatorio = 0
    id_req = 0 #id da req atual do cliente
    date = dt.datetime.now()

    cliente = {'ip', 'last_req', 'last_sum'}
    soma_server = {'num_reqs', 'total_sum'}

    if len(sys.argv) > 1: 
        SERVIDOR_PORTA = int(sys.argv[1]) #pega o primeiro argumento da linha de comando
        #criação do socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        except socket.error:
            print('Erro ao criar socket')
            sys.exit()

        sock.bind((IP_HOST, SERVIDOR_PORTA))

        print(f"{date} server {IP_HOST} num_reqss {num_reqs} total_somatorio {somatorio}")

        while True:
            try:
                data, addr = sock.recvfrom(1024)
                valor = struct.unpack('!i', data)[0]
                
                if(cliente['ip'] != addr) :
                    id_req = 1
                    cliente.update({'ip' : addr})
                    
                else: 
                    id_req = cliente[addr]['last_req']
                    id_req += 1
                    
                num_reqs += 1
                somatorio += valor

                cliente[addr] = {'last_req' : id_req, 'last_sum' : somatorio}
                soma_server = {'num_reqs' : num_reqs, 'total_sum' : somatorio}

                salvaCSV(cliente, soma_server)

                print(f"{date} client {addr} id_req {id_req} value {valor} num_reqs {num_reqs} total_sum {somatorio}")
                
                envio_somatorio = struct.pack('!iii', id_req, num_reqs, somatorio) #envia os valores para o cliente
                sock.sendto(envio_somatorio, (IP_HOST, SERVIDOR_PORTA))

            except socket.error:
                print(f"Recebido dado nao numerico: {data}")
                sys.exit()

    else:
        print("Nenhuma porta fornecida")