import socket
import struct
import interface
import threading
import sys
import datetime as dt
import time


def processamento_server(sock, num_reqs, somatorio, ID_NUM, sou_primario, lista_servidores_inicial=None):
    #estrutura: {'address' : address, 'last_req': id_req, 'last_num_reqs' : last_num_reqs, 'last_sum': somatorio}
    tabela_1 = {} 
    tabela_2 = {'num_reqs' : 0, 'total_sum' : 0}

    # Dicionario para guardar quem sao os outros servidores: {ID: (IP, Porta)}
    # Reaproveita o que já foi descoberto durante o bootstrap (servidor_servidor)
    lista_servidores = lista_servidores_inicial if lista_servidores_inicial else {}

    # ESTADO COMPARTILHADO ENTRE THREADS
    estado_srv = {
        'is_primary': sou_primario, # Decidido no bootstrap (descoberta.servidor_servidor), não hardcoded
        'ultimo_heartbeat': time.time(), # Relógio interno inicial
        'em_eleicao': False,
        'recebeu_ansr': False
    }

    if estado_srv['is_primary']:
        print(f"[INICIO] Servidor {ID_NUM} está ATIVO como PRIMÁRIO.")
    else:
        print(f"[INICIO] Servidor {ID_NUM} está ATIVO como BACKUP.")

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

            #Requisicao de dados do cliente (12 bytes = !iQ)
            elif len(message) == 12:
                # Backups não devem processar requisições de soma — apenas o
                # líder atende clientes. Se um cliente "perdido" (ainda não
                # recebeu o NLDR) mandar aqui, simplesmente ignoramos: ele
                # vai estourar o timeout e continuar tentando até receber o
                # redirecionamento do líder atual.
                if not estado_srv['is_primary']:
                    continue

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

                    # REPLICAÇÃO PASSIVA: O Primário propaga o novo estado E o cliente para os Backups
                    # Converte IP string (ex: '192.168.0.10') para 4 bytes binários
                    ip_bytes = socket.inet_aton(ip_client)
                    porta_cliente = addr[1]

                    # Formato: !4s i i Q i H 4s (Tamanho real: 30 bytes)
                    msg_update = struct.pack('!4siiQiH4s', b"UPDT", ID_NUM, num_reqs, somatorio, id_req, porta_cliente, ip_bytes)

                    for addr_bkp in lista_servidores.values():
                        sock.sendto(msg_update, addr_bkp)

            #Mensagem de ATUALIZACAO/replicação do Primário (30 bytes = !4siiQiH4s)
            elif len(message) == 30:
                prefixo, id_lider, reqs_sync, soma_sync, req_sync, port_sync, ip_bytes = struct.unpack('!4siiQiH4s', message)

                if prefixo == b"UPDT" and not estado_srv['is_primary']:
                    # Reverte os 4 bytes para string IP normal
                    ip_sync = socket.inet_ntoa(ip_bytes)
                    addr_sync = (ip_sync, port_sync)

                    # Sincroniza as variáveis de agregação globais do backup
                    num_reqs = reqs_sync
                    somatorio = soma_sync

                    # Sincroniza o cliente na tabela_1 do Backup!
                    if addr_sync not in tabela_1:
                        tabela_1[addr_sync] = {
                            'address': ip_sync,
                            'last_req': None,
                            'last_num_reqs': 0,
                            'last_sum': 0
                        }

                    tabela_1[addr_sync]['last_req'] = req_sync
                    tabela_1[addr_sync]['last_num_reqs'] = reqs_sync
                    tabela_1[addr_sync]['last_sum'] = soma_sync

                    print(f"[REPLICAÇÃO] Cliente {addr_sync} sincronizado. Soma={somatorio}")

                    # Também garante que o líder atual está na lista de servidores
                    # conhecidos (caso ainda não estivesse, por exemplo se o ASRV
                    # se perdeu durante o bootstrap).
                    if id_lider != ID_NUM and id_lider not in lista_servidores:
                        lista_servidores[id_lider] = addr
                continue

            else:
                print("Pacote de tamanho desconhecido descartado.")

        except OSError as e:
            # Socket fechado (ex: processo sendo encerrado) -> termina o loop
            print(f"Socket encerrado, finalizando processamento: {e}")
            return
        except struct.error as e:
            print(f"Pacote malformado descartado: {e}")
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
        try:
            # Aguarda qualquer pacote chegar
            data, addr = sock.recvfrom(1024) 
            ip_server = addr[0]

            # 1. É o ACK matemático normal do servidor? (Deve ter exatos 16 bytes)
            if len(data) == 16:
                id_req, num_reqs, somatorio = struct.unpack('!iiQ', data) 
     
                # Lê do estado compartilhado para saber o que a thread principal está esperando
                if estado_atual['req_esperado'] == id_req:
                    interface.interface_cliente(ip_server, id_req, estado_atual['numero_enviado'], num_reqs, somatorio)
                    evento.set() # Acende flag avisando que ACK da req chegou

            # 2. FASE 4: É o aviso de mudança de Líder? (Deve ter exatos 8 bytes)
            elif len(data) == 8:
                prefixo, id_novo = struct.unpack('!4si', data)
                if prefixo == b"NLDR":
                    # Muda o endereço de destino na memória para os próximos envios!
                    estado_atual['endereco_servidor'] = addr
                    print(f"\n[SISTEMA] Conexão redirecionada! O Servidor Líder agora é o ID {id_novo} ({addr[0]}).")
            
            # 3. Pacote ignorado (como o b"ack_discover" desgarrado de 12 bytes)
            else:
                pass 
                
        except struct.error:
            # Se ainda assim cair algum lixo com o mesmo tamanho mas formato inválido, ignora
            pass


def thread_envia_heartbeat(sock, ID_NUM, lista_servidores, estado_srv):
    # Pacote BEAT (8 bytes: 4 da string + 4 do int ID)
    msg_beat = struct.pack('!4si', b"BEAT", ID_NUM) 
    
    while True:
        if estado_srv['is_primary']:
            # Se eu sou o lider, mando meu batimento para todos da lista
            for id_backup, addr in lista_servidores.items():
                try:
                    sock.sendto(msg_beat, addr)
                except OSError:
                    # Socket foi fechado (processo encerrando) -> encerra a thread
                    return
        
        time.sleep(2) # Dorme por 2 segundos antes de bater de novo


def thread_monitora_falha(sock, ID_NUM, lista_servidores, estado_srv, tabela_1):
    TIMEOUT_FALHA = 5.0   # Segundos sem ouvir o lider para considerar que ele morreu
    TIMEOUT_ELEICAO = 2.0 # Segundos esperando um "Cala a boca" (ANSR) de alguem maior
    
    while True:
        try:
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

                        # Comunica a vitória (COOR) para todo mundo. Como UDP não
                        # garante entrega, manda em rajada para reduzir a chance
                        # de algum backup nunca descobrir o novo líder.
                        msg_coor = struct.pack('!4si', b"COOR", ID_NUM)
                        for _ in range(3):
                            for addr in lista_servidores.values():
                                sock.sendto(msg_coor, addr)
                            time.sleep(0.1)

                        # FASE 4: Avisa todos os clientes conhecidos na tabela_1!
                        # Também em rajada: se o cliente perder esse pacote, ele
                        # fica preso em timeout tentando falar com o líder morto.
                        msg_nldr = struct.pack('!4si', b"NLDR", ID_NUM)
                        for _ in range(3):
                            for addr_cliente in tabela_1.keys():
                                sock.sendto(msg_nldr, addr_cliente)
                            time.sleep(0.1)
                        print(f"[VALENTÃO] {len(tabela_1)} clientes notificados da mudança.")

                    else:
                        # DERROTA! Alguém maior assumiu a responsabilidade.
                        print(f"[VALENTÃO] Alguém maior respondeu. Aguardando novo líder assumir...")
                        estado_srv['em_eleicao'] = False
                        # Zera o heartbeat para dar tempo do novo líder assumir e mandar o BEAT
                        estado_srv['ultimo_heartbeat'] = time.time()

        except OSError:
            # Socket foi fechado (processo encerrando) -> encerra a thread
            return

        time.sleep(1) # Checa os cronômetros a cada 1 segundo