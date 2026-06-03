import socket
import struct
import sys

def servidor_servidor(sock, ID_NUM, SERVIDOR_PORTA):
    # Habilita o socket do servidor para enviar broadcast também
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    #Empacota a mensagem b"SRV" (3 bytes) + o ID numérico (4 bytes)
    msg_desc_srv = struct.pack('!3si', b"SRV", ID_NUM)
    # Dispara para a rede. (Substitua 4000 pela sua variável SERVIDOR_PORTA se preferir passar como parâmetro)
    sock.sendto(msg_desc_srv, ('255.255.255.255', SERVIDOR_PORTA)) 
    print(f"Buscando outros servidores na rede...")

def descoberta_server(SERVIDOR_PORTA):
    #criacao do socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
    except socket.error:
        print('Erro ao criar socket listen')
        sys.exit()

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
    sock.sendto(b"discover", ('255.255.255.255', CLIENTE_PORTA))

    CLIENTE_IP = sock.recvfrom(1024)[1][0]
    return sock, CLIENTE_IP