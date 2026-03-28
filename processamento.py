import socket
import struct
import sys
import interface

def processamento_server(sock, num_reqs, somatorio, date):
    #estrutura: {'address' : address, 'last_req': id_req, 'last_num_reqs' : last_num_reqs, 'last_sum': somatorio}
    tabela_1 = {} 
    tabela_2 = {'num_reqs' : 0, 'total_sum' : 0}
    i = 0
    while (True):
        try:
            message, addr = sock.recvfrom(1024)
            ip_client = addr[0]
            id_req, data = struct.unpack('!iQ', message)
            
            if(ip_client in tabela_1 and tabela_1[ip_client]['last_req'] == id_req): #DUPLICADA
                print(f"{date} client {addr} DUP!! id_req {id_req} value {data} num_reqs {num_reqs} total_sum {somatorio}")
                envio_somatorio = tabela_1[ip_client]['last_sum']
                
                sock.sendto(struct.pack('!Q', envio_somatorio), addr)

            else:
                if (ip_client not in  tabela_1) : #CASO IP NAO ESTEJA NA TABELA
                    tabela_1[ip_client] = {
                        'address': ip_client,
                        'last_req': None,
                        'last_num_reqs': 0,
                        'last_sum': 0
                    }

                num_reqs += 1
                somatorio += data

                tabela_1[ip_client]['last_req'] = id_req
                tabela_1[ip_client]['last_num_reqs'] = num_reqs
                tabela_1[ip_client]['last_sum'] = somatorio


                tabela_2 = {'num_reqs' : num_reqs, 'total_sum' : somatorio}

                interface.interface_server(date, ip_client, id_req, data, tabela_2)

                envio_somatorio = struct.pack('!iiQ', id_req, num_reqs, somatorio) #envia os valores para o cliente
                sock.sendto(envio_somatorio, addr)
    
        except socket.error:
            print(f"Recebido dado nao numerico: {data}")
            continue


def processamento_cliente(sock, CLIENTE_IP, CLIENTE_PORTA, date):
    req = 0
    while(True):
        numero = int(input())
        req += 1
        mensagem = struct.pack('!iQ', req, numero)
        while(True):
            sock.sendto(mensagem, (CLIENTE_IP, CLIENTE_PORTA)) #envia numero
            try:
                sock.settimeout(0.2) #timeout para esperar um ack ate 200ms

                #aguarda confirmacao
                data, addr = sock.recvfrom(1024) #recebe os dados
                ip_server = addr[0]
                id_req, num_reqs, somatorio = struct.unpack('!iiQ', data) #desempacota

                if (req == id_req):
                    break

            except socket.timeout:
                print("Timeout. Reenviando...")
                continue
        
        if somatorio:
            interface.interface_cliente(date, ip_server, id_req, numero, num_reqs, somatorio)
        

