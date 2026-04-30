import socket
import struct
import interface
import threading
import sys
import datetime as dt
import time

def processamento_server(sock, num_reqs, somatorio):
    #estrutura: {'address' : address, 'last_req': id_req, 'last_num_reqs' : last_num_reqs, 'last_sum': somatorio}
    tabela_1 = {} 
    tabela_2 = {'num_reqs' : 0, 'total_sum' : 0}
    while (True):
        try:
            message, addr = sock.recvfrom(1024)
            ip_client = addr[0]

            # É um cliente novo pedindo descoberta? (Checa se é a string de 8 bytes)
            if message == b"discover":
                sock.sendto(b"ack_discover", addr)
                continue # Volta para o topo do loop para escutar a próxima mensagem

            # É um pacote de dados? (Checa se tem o tamanho exato do struct !iQ)
            elif len(message) == 12:
                id_req, data = struct.unpack('!iQ', message)
            
                if(addr in tabela_1 and tabela_1[addr]['last_req'] == id_req): #DUPLICADA
                    date = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    print(f"{date} client {ip_client} DUP!! id_req {id_req} value {data} num_reqs {num_reqs} total_sum {somatorio}")

                    envio_somatorio = tabela_1[addr]['last_sum']
                    envio_num_reqs = tabela_1[addr]['last_num_reqs']
                    envio_id = tabela_1[addr]['last_req']
                    
                    sock.sendto(struct.pack('!iiQ', envio_id, envio_num_reqs, envio_somatorio), addr)

                else:
                    if (addr not in  tabela_1) : #CASO IP NAO ESTEJA NA TABELA
                        tabela_1[addr] = {
                            'address': ip_client,
                            'last_req': None,
                            'last_num_reqs': 0,
                            'last_sum': 0
                        }

                    num_reqs += 1
                    somatorio += data

                    tabela_1[addr]['last_req'] = id_req
                    tabela_1[addr]['last_num_reqs'] = num_reqs
                    tabela_1[addr]['last_sum'] = somatorio


                    tabela_2 = {'num_reqs' : num_reqs, 'total_sum' : somatorio}

                    interface.interface_server(ip_client, id_req, data, tabela_2)

                    envio_somatorio = struct.pack('!iiQ', id_req, num_reqs, somatorio) #envia os valores para o cliente

                    # ---> INÍCIO DA SIMULAÇÃO DE DUPLICADA <---
                    # Força o servidor a atrasar o ACK da requisição número 3
                    #if id_req == 3:
                    #    print("Simulando rede lenta... segurando o ACK!")
                    #    time.sleep(1.0) # Dorme 1 segundo (O cliente estoura com 0.2s)
                    # ---> FIM DA SIMULAÇÃO DE DUPLICADA <---

                    sock.sendto(envio_somatorio, addr)
    
        except socket.error:
            print(f"Recebido dado nao numerico: {data}")
            continue


def processamento_cliente(sock, CLIENTE_IP, CLIENTE_PORTA):
    req = 0
    evento = threading.Event() 

    estado_atual = {'req_esperado': 0, 'numero_enviado': 0} #estrutura mutável compartilhada

    thread_ouvinte = threading.Thread(
        target=ouvinte_servidor, 
        args=(sock, estado_atual, evento),
        daemon=True) # Garante que a thread morra se o programa fechar
    thread_ouvinte.start()

    while(True):
        try:
            numero = int(input())
        except:
            print("\nEncerrando o cliente...")
            sys.exit(0) # Sai de forma limpa e sem erros vermelhos
        req += 1

        estado_atual['req_esperado'] = req
        estado_atual['numero_enviado'] = numero

        mensagem = struct.pack('!iQ', req, numero)
        while(True):
            evento.clear() #garante/apaga flag ACK
            sock.sendto(mensagem, (CLIENTE_IP, CLIENTE_PORTA)) #envia numero    
        
            if evento.wait(0.2):
                break #Sucesso

            else:
                print("Timeout") #Falha, loop repete



def ouvinte_servidor(sock, estado_atual, evento):
    while(True):
            #aguarda confirmacao
            data, addr = sock.recvfrom(1024) #recebe os dados
            ip_server = addr[0]
            id_req, num_reqs, somatorio = struct.unpack('!iiQ', data) #desempacota
 
            #Lê do estado compartilhado para saber o que a thread principal está esperando
            if (estado_atual['req_esperado'] == id_req):
                interface.interface_cliente(ip_server, id_req, estado_atual['numero_enviado'], num_reqs, somatorio)
                evento.set() #acende flag avisando que ACK da req chegou
