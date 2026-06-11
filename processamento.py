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
    t_mon = threading.Thread(target=thread_monitora_falha, args=(sock, ID_NUM, lista_servidores, estado_srv, tabela_1), daemon=True)
    t_beat.start()
    t_mon.start()
    
    while (True):
        try:
            message, addr = sock.recvfrom(1024)
            ip_client = addr[0]

            #Cliente em descoberta
            if message == b"discover":
                if estado_srv['is_primary']: # SÓ O LÍDER RESPONDE!
                    sock.sendto(b"ack_discover", addr)
                continue

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

            #Tratamento de todas as mensagens de Controle (8 bytes = !4si)
            elif len(message) == 8:
                prefixo, id_recebido = struct.unpack('!4si', message)
                
                if prefixo == b"ASRV" and id_recebido != ID_NUM:
                    lista_servidores[id_recebido] = addr
                    print(f"Servidor veterano ID {id_recebido} confirmou presenca.")
                
                elif prefixo == b"BEAT":
                    if not estado_srv['is_primary']:
                        estado_srv['ultimo_heartbeat'] = time.time() # Reseta o relógio
                
                # --- NOVAS MENSAGENS DO VALENTAO ---
                
                elif prefixo == b"ELEC":
                    print(f"Recebi aviso de ELEICAO do ID {id_recebido}.")
                    # Se meu ID é MAIOR que o coitado que chamou a eleição:
                    if ID_NUM > id_recebido:
                        # 1. Mando ele ficar quieto (ANSR)
                        msg_ansr = struct.pack('!4si', b"ANSR", ID_NUM)
                        sock.sendto(msg_ansr, addr)
                        
                        # 2. O PULO DO GATO: Como eu sei que o líder morreu, 
                        # eu forço o MEU próprio cronômetro a estourar agora!
                        # Isso fará a minha thread de monitoramento iniciar a MINHA eleição.
                        estado_srv['ultimo_heartbeat'] = 0 
                
                elif prefixo == b"ANSR":
                    print(f"Servidor MAIOR (ID {id_recebido}) mandou eu calar a boca.")
                    # Acende a flag que avisa a thread que perdemos
                    estado_srv['recebeu_ansr'] = True 
                
                elif prefixo == b"COOR":
                    print(f">>> NOVO LIDER ASSUMIU: ID {id_recebido} <<<")
                    estado_srv['is_primary'] = False
                    estado_srv['em_eleicao'] = False
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

    # Adicionamos o 'endereco_servidor' no estado compartilhado!
    estado_atual = {
        'req_esperado': 0, 
        'numero_enviado': 0,
        'endereco_servidor': (CLIENTE_IP, CLIENTE_PORTA) 
    }

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
            sock.sendto(mensagem, estado_atual['endereco_servidor'])   
        
            if evento.wait(0.2):
                break #Sucesso

            else:
                print("Timeout") #Falha, loop repete



def ouvinte_servidor(sock, estado_atual, evento):
    while True:
        data, addr = sock.recvfrom(1024) 
        
        # 1. É o ACK normal do servidor? (12 bytes)
        if len(data) == 12:
            ip_server = addr[0]
            id_req, num_reqs, somatorio = struct.unpack('!iiQ', data) 
            
            if estado_atual['req_esperado'] == id_req:
                interface.interface_cliente(ip_server, id_req, estado_atual['numero_enviado'], num_reqs, somatorio)
                evento.set() 
                
        # 2. FASE 4: É o aviso de mudança de Líder? (8 bytes)
        elif len(data) == 8:
            prefixo, id_novo = struct.unpack('!4si', data)
            if prefixo == b"NLDR":
                # O PULO DO GATO: Muda o endereço de destino na memória!
                estado_atual['endereco_servidor'] = addr
                print(f"\n[SISTEMA] Conexão redirecionada! O Servidor Líder agora é o ID {id_novo} ({addr[0]}).")


def thread_envia_heartbeat(sock, ID_NUM, lista_servidores, estado_srv):
    # Pacote BEAT (8 bytes: 4 da string + 4 do int ID)
    msg_beat = struct.pack('!4si', b"BEAT", ID_NUM) 
    
    while True:
        if estado_srv['is_primary']:
            # Se eu sou o lider, mando meu batimento para todos da lista
            for id_backup, addr in lista_servidores.items():
                sock.sendto(msg_beat, addr)
        
        time.sleep(2) # Dorme por 2 segundos antes de bater de novo


def thread_monitora_falha(sock, ID_NUM, lista_servidores, estado_srv, tabela_1):
    TIMEOUT_FALHA = 5.0   # Segundos sem ouvir o lider para considerar que ele morreu
    TIMEOUT_ELEICAO = 2.0 # Segundos esperando um "Cala a boca" (ANSR) de alguem maior
    
    while True:
        # Só faz algo se for backup e nao estiver no meio de uma eleicao
        if not estado_srv['is_primary'] and not estado_srv.get('em_eleicao', False):
            tempo_sem_sinal = time.time() - estado_srv['ultimo_heartbeat']
            
            if tempo_sem_sinal > TIMEOUT_FALHA:
                print("\n[ALERTA] LIDER DECLARADO MORTO! TIMEOUT ESTOUROU.")
                print(f"[VALENTÃO] Servidor {ID_NUM} iniciando eleição...\n")
                
                estado_srv['em_eleicao'] = True
                estado_srv['recebeu_ansr'] = False # Flag que diz se tomamos um "cala a boca"
                
                # Passo 1: Acha todo mundo que tem ID maior que o meu
                maiores = {id_srv: addr for id_srv, addr in lista_servidores.items() if id_srv > ID_NUM}
                
                if len(maiores) == 0:
                    # Otimização: Se eu sou o maior ID conhecido, nem perco tempo perguntando!
                    pass 
                else:
                    # Dispara a mensagem de ELEIÇÃO (ELEC) para os maiores
                    msg_elec = struct.pack('!4si', b"ELEC", ID_NUM)
                    for addr in maiores.values():
                        sock.sendto(msg_elec, addr)
                
                # Passo 2: Espera um pouquinho para ver se alguém maior responde com ANSR
                time.sleep(TIMEOUT_ELEICAO)
                
                # Passo 3: O Veredito!
                if not estado_srv['recebeu_ansr']:
                    # VITÓRIA! Ninguém maior respondeu (ou não existiam maiores). Eu assumo.
                    print(f"[VALENTÃO] Venci a eleição! EU SOU O NOVO PRIMÁRIO (Líder {ID_NUM})!")
                    estado_srv['is_primary'] = True
                    estado_srv['em_eleicao'] = False
                    
                    # Comunica a vitória (COOR) para todo mundo
                    msg_coor = struct.pack('!4si', b"COOR", ID_NUM)
                    for addr in lista_servidores.values():
                        sock.sendto(msg_coor, addr)
                        
                    # FASE 4: Avisa todos os clientes conhecidos na tabela_1!
                    msg_nldr = struct.pack('!4si', b"NLDR", ID_NUM)
                    for addr_cliente in tabela_1.keys():
                        sock.sendto(msg_nldr, addr_cliente)
                    print(f"[VALENTÃO] {len(tabela_1)} clientes notificados da mudança.")
                    
                else:
                    # DERROTA! Alguém maior assumiu a responsabilidade.
                    print(f"[VALENTÃO] Alguém maior respondeu. Aguardando novo líder assumir...")
                    estado_srv['em_eleicao'] = False
                    # Zera o heartbeat para dar tempo do novo líder assumir e mandar o BEAT
                    estado_srv['ultimo_heartbeat'] = time.time()
                    
        time.sleep(1) # Checa os cronômetros a cada 1 segundo

                
