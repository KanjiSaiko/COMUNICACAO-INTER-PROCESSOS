import socket
import struct
import sys
import time

def servidor_servidor(sock, ID_NUM, SERVIDOR_PORTA, lista_servidores):
    """
    Faz a descoberta de outros servidores já ativos na rede E decide,
    de forma não hardcoded, se este processo deve nascer como líder
    (primário) ou como backup.

    Regra (consistente com o algoritmo do Valentão): se, depois de
    esperar um tempo por respostas ASRV, nenhum servidor com ID MAIOR
    que o meu se manifestou, eu me considero o maior ID vivo na rede
    e assumo como primário. Caso contrário, nasço como backup —
    o líder de fato vai se anunciar via BEAT/COOR em seguida.

    Retorna True se este processo deve iniciar como primário, False
    caso contrário. `lista_servidores` é preenchido com {ID: (IP, Porta)}
    de quem respondeu.
    """
    # Habilita o socket do servidor para enviar broadcast também
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    #Empacota a mensagem b"SRV" (3 bytes) + o ID numérico (4 bytes)
    msg_desc_srv = struct.pack('!3si', b"SRV", ID_NUM)
    # Dispara para a rede.
    sock.sendto(msg_desc_srv, ('255.255.255.255', SERVIDOR_PORTA))
    print(f"Buscando outros servidores na rede...")

    # Janela de bootstrap: escuta por respostas ASRV (ou até mesmo SRV de
    # quem chegou ao mesmo tempo) por um tempo limitado antes de decidir.
    # Retransmite o SRV periodicamente dentro da janela para reduzir o
    # risco de perda de pacote UDP levar a dois primários simultâneos.
    TIMEOUT_BOOTSTRAP = 3.0
    INTERVALO_RETRANSMISSAO = 0.5
    sock.settimeout(INTERVALO_RETRANSMISSAO)

    tempo_inicial = time.time()
    proxima_retransmissao = tempo_inicial + INTERVALO_RETRANSMISSAO
    while time.time() - tempo_inicial < TIMEOUT_BOOTSTRAP:
        try:
            message, addr = sock.recvfrom(1024)
        except socket.timeout:
            if time.time() >= proxima_retransmissao:
                sock.sendto(msg_desc_srv, ('255.255.255.255', SERVIDOR_PORTA))
                proxima_retransmissao = time.time() + INTERVALO_RETRANSMISSAO
            continue

        # Ignora pacotes "discover" de clientes durante o bootstrap: têm 8
        # bytes (mesmo tamanho de !4si) mas não devem ser confundidos com
        # pacotes de controle entre servidores (ASRV).
        if message == b"discover":
            continue

        if len(message) == 8:
            try:
                prefixo, id_recebido = struct.unpack('!4si', message)
            except struct.error:
                continue
            if prefixo == b"ASRV" and id_recebido != ID_NUM:
                lista_servidores[id_recebido] = addr
                print(f"[BOOTSTRAP] Servidor veterano ID {id_recebido} respondeu.")

        elif len(message) == 7:
            try:
                prefixo, id_recebido = struct.unpack('!3si', message)
            except struct.error:
                continue
            if prefixo == b"SRV" and id_recebido != ID_NUM:
                lista_servidores[id_recebido] = addr
                # Responde de volta para ele também me conhecer
                msg_ack_srv = struct.pack('!4si', b"ASRV", ID_NUM)
                sock.sendto(msg_ack_srv, addr)

    # Remove o timeout: a partir daqui o loop principal de processamento
    # volta a usar o socket em modo bloqueante.
    sock.settimeout(None)

    maior_id_conhecido = max(lista_servidores.keys(), default=ID_NUM)
    sou_primario = ID_NUM >= maior_id_conhecido

    if sou_primario:
        print(f"[BOOTSTRAP] Nenhum servidor com ID maior encontrado. "
              f"Servidor {ID_NUM} inicia como PRIMÁRIO.")
    else:
        print(f"[BOOTSTRAP] Servidor {ID_NUM} inicia como BACKUP "
              f"(servidor {maior_id_conhecido} deve ser o primário).")

    return sou_primario

def descoberta_server(SERVIDOR_PORTA):
    #criacao do socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
    except socket.error:
        print('Erro ao criar socket listen')
        sys.exit()

    # Aumenta o buffer de recepção do SO para reduzir o risco de descarte
    # silencioso de pacotes (incluindo BEAT/COOR/NLDR, que são críticos para
    # o failover) quando o servidor está sob carga alta de requisições e o
    # processamento (com print por requisição) não consegue esvaziar a fila
    # tão rápido quanto os pacotes chegam.
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8 * 1024 * 1024)  # 8 MB
    except OSError:
        pass  # Alguns SOs limitam o valor máximo; segue com o default se falhar

    #servidor ouvindo
    sock.bind(('0.0.0.0', SERVIDOR_PORTA))

    return sock

def descoberta_cliente(CLIENTE_PORTA):
    #criacao do socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)#udp
            
    except socket.error:
        print('Erro ao criar socket listen')
        sys.exit()

    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1) #ativa broadcast

    # Retransmite o "discover" até obter resposta do líder. Isso evita que
    # o cliente trave para sempre caso o pacote se perca, ou caso a rede
    # ainda esteja em processo de eleição quando o cliente sobe.
    TIMEOUT_DISCOVER = 1.0
    sock.settimeout(TIMEOUT_DISCOVER)

    while True:
        sock.sendto(b"discover", ('255.255.255.255', CLIENTE_PORTA))
        try:
            CLIENTE_IP = sock.recvfrom(1024)[1][0]
            break
        except socket.timeout:
            print("Nenhum líder respondeu ainda, tentando novamente...")
            continue

    sock.settimeout(None) # volta ao modo bloqueante para o resto da execução
    return sock, CLIENTE_IP