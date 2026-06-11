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

    # ESTADO COMPARTILHADO ENTRE THREADS
    estado_srv = {
        'is_primary': (ID_NUM == 3), # Provisório até fazermos a eleição real
        'ultimo_heartbeat': time.time() # Relógio interno inicial
    }

    # Inicia as threads de tolerância a falhas
    t_beat = threading.Thread(target=thread_envia_heartbeat, args=(sock, ID_NUM, lista_servidores, estado_srv), daemon=True)
    t_mon = threading.Thread(target=thread_monitora_falha, args=(estado_srv,), daemon=True)
    t_beat.start()
    t_mon.start()
    
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
                
                elif prefixo == b"BEAT":
                    if not estado_srv['is_primary']:
                        # Zera o cronômetro do backup! O líder está vivo.
                        estado_srv['ultimo_heartbeat'] = time.time()
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

                #Mensagem de ATUALIZACAO do Primario (20 bytes = !4siiQ)
                elif len(message) == 20:
                    prefixo, id_lider, reqs_sync, soma_sync = struct.unpack('!4siiQ', message)

                    if prefixo == b"UPDT" and not estado_srv['is_primary']:
                        # O Backup recebe a ordem do líder e atualiza suas próprias variáveis
                        num_reqs = reqs_sync
                        somatorio = soma_sync
                        print(f"[REPLICAÇÃO] Sincronizado pelo Líder {id_lider}: Reqs={num_reqs}, Soma={somatorio}")
                    continue

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

                    if estado_srv['is_primary']:
                        msg_update = struct.pack('!4siiQ', b"UPDT", ID_NUM, num_reqs, somatorio)
                        for id_bkp, addr_bkp in lista_servidores.items():
                            sock.sendto(msg_update, addr_bkp)
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


def thread_envia_heartbeat(sock, ID_NUM, lista_servidores, estado_srv):
    # Pacote BEAT (8 bytes: 4 da string + 4 do int ID)
    msg_beat = struct.pack('!4si', b"BEAT", ID_NUM) 
    
    while True:
        if estado_srv['is_primary']:
            # Se eu sou o lider, mando meu batimento para todos da lista
            for id_backup, addr in lista_servidores.items():
                sock.sendto(msg_beat, addr)
        
        time.sleep(2) # Dorme por 2 segundos antes de bater de novo


def thread_monitora_falha(estado_srv):
    TIMEOUT_FALHA = 5.0 # Segundos de tolerância
    
    while True:
        if not estado_srv['is_primary']:
            # Se eu sou backup, verifico ha quanto tempo nao ouco o lider
            tempo_sem_sinal = time.time() - estado_srv['ultimo_heartbeat']
            
            if tempo_sem_sinal > TIMEOUT_FALHA:
                print("\n[ALERTA] LIDER DECLARADO MORTO! TIMEOUT ESTOUROU.")
                print("[ALERTA] INICIANDO ALGORITMO DO VALENTÃO...\n")
                
                # Reseta o timer temporariamente para nao floodar o terminal 
                # enquanto a eleição da Fase 3 acontece
                estado_srv['ultimo_heartbeat'] = time.time() 
                
        time.sleep(1) # Checa o cronometro a cada 1 segundo

                
