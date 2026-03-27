import socket
import struct
import sys
import pandas as pd
import interface

def salvaCSV(cliente, soma_server):
    table1 = pd.DataFrame(cliente)
    table2 = pd.DataFrame(soma_server)

    table1.to_csv('table1.csv', index=False, encoding='utf-8-sig')
    table2.to_csv('table2.csv', index=False, encoding='utf-8-sig')

def processamento_server(sock, num_reqs, somatorio, IP_HOST, SERVIDOR_PORTA, date):
    #estrutura: {(address : req), (last_sum : somatorio)}
    cliente = {}
    soma_server = {'num_reqs', 'total_sum'}
    while (True):
        try:
            message, addr = sock.recvfrom(1024)
            id_req, data = message.split(":", 1)
            valor = struct.unpack('!i', data)[0]
            
            if(addr in cliente and cliente[addr] == id_req): #DUPLICADA
                print(f"{date} client {addr} DUP!! id_req {id_req} value {valor} num_reqs {num_reqs} total_sum {somatorio}")
            else:
                if (addr not in  cliente) : #CASO IP NAO ESTEJA NA TABELA
                    cliente[addr] = id_req 
                num_reqs += 1
                somatorio += valor

                cliente[addr] = {'last_sum' : somatorio}
                soma_server = {'num_reqs' : num_reqs, 'total_sum' : somatorio}

                salvaCSV(cliente, soma_server)

                interface.interface_server(date, addr, id_req, valor, num_reqs, somatorio)

                envio_somatorio = struct.pack('!iii', id_req, num_reqs, somatorio) #envia os valores para o cliente
                sock.sendto(envio_somatorio, (IP_HOST, SERVIDOR_PORTA))

        except socket.error:
            print(f"Recebido dado nao numerico: {data}")
            sys.exit()


def processamento_cliente(sock, CLIENTE_IP, CLIENTE_PORTA, date):
    req = 0
    while(True):
        numero = int(input())
        envio_int = struct.pack('!i', numero)
        req += 1
        mensagem = f'{req}:{envio_int}'
        try:
            sock.sendto(mensagem, (CLIENTE_IP, CLIENTE_PORTA)) #envia numero

            data, addr = sock.recvfrom(1024) #recebe somatorio
            id_req, num_reqs, somatorio = struct.unpack('!iii', data)
            
            if somatorio:
                interface.interface_cliente(date, addr, id_req, numero, num_reqs, somatorio)
        except:
            print("Timer estourou")
            sys.exit()

