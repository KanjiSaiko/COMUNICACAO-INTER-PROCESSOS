import socket
import struct
import interface
import threading
import sys
import datetime as dt
import time


def processamento_server(sock, num_reqs, somatorio, ID_NUM):
    #estrutura: {'address' : address, 'last_req': id_req, 'last_num_reqs' : last_num_reqs, 'last_sum': somatorio}
    tabela_1 = {} 
    tabela_2 = {'num_reqs' : 0, 'total_sum' : 0}

    lista_servidores = {} # Dicionario para guardar quem sao os outros servidores: {ID: (IP, Porta)}

    is_primary = (ID_NUM == 3) #Se for 3, e lider. Se for outro, e backup
    while (True):
        try:
            message, addr = sock.recvfrom(1024)
            ip_client = addr[0]

            #Cliente em descoberta
            if message == b"discover":
                sock.sendto(b"ack_discover", addr)
                continue # Volta para o topo do loop para escutar a próxima mensagem

            #Servidor Novo fazendo descoberta
            elif len(message) == 7:
                prefixo, id_recebido = struct.unpack('!3si', message)
                if prefixo == b"SRV" and id_recebido != ID_NUM: # Ignora o próprio eco do broadcast
                    lista_servidores[id_recebido] = addr
                    print(f"Novo servidor descoberto! ID: {id_recebido} em {addr}")
                    
                    # Responde diretamente (unicast) para ele saber que nós existimos
                    msg_ack_srv = struct.pack('!4si', b"ASRV", ID_NUM) 
                    sock.sendto(msg_ack_srv, addr)
                continue

            #Resposta de um Servidor Antigo para o broadcast
            elif len(message) == 8:
                prefixo, id_recebido = struct.unpack('!4si', message)
                if prefixo == b"ASRV" and id_recebido != ID_NUM:
                    lista_servidores[id_recebido] = addr
                    print(f"Servidor veterano ID {id_recebido} confirmou presenca em {addr}")
                continue

            #Requisicao de dados do cliente
            elif len(message) == 12:
                id_req, data = struct.unpack('!iQ', message)
                # Verifica se o cliente existe e se o pacote é <= ao último processado (Pacotes velhos/Duplicatas)
                if addr in tabela_1 and tabela_1[addr]['last_req'] is not None and id_req <= tabela_1[addr]['last_req']:
                    
                    if(tabela_1[addr]['last_req'] == id_req): #DUPLICADA
                        date = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        print(f"{date} client {ip_client} DUP!! id_req {id_req} value {data} num_reqs {num_reqs} total_sum {somatorio}")

                        envio_somatorio = tabela_1[addr]['last_sum']
                        envio_num_reqs = tabela_1[addr]['last_num_reqs']
                        envio_id = tabela_1[addr]['last_req']
                        
                        sock.sendto(struct.pack('!iiQ', envio_id, envio_num_reqs, envio_somatorio), addr)

                    else: #pacote fantasma -> descartado
                        pass

                else: #pacote novo
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

                    envio_somatorio = struct.pack('!iiQ', id_req, num_reqs, somatorio) #envia ack com os valores para o cliente
                    sock.sendto(envio_somatorio, addr)
            else:
                print("Backup nao processa requisicoes")
    
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
