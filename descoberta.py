import socket
import struct
import sys

def descoberta_server(SERVIDOR_PORTA):
    #criacao do socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
    except socket.error:
        print('Erro ao criar socket listen')
        sys.exit()

    #servidor ouvindo
    sock.bind(('0.0.0.0', SERVIDOR_PORTA))

    while True:
        message, addr = sock.recvfrom(1024)
        if (message == b"discover"):
            sock.sendto(b"ack_discover", addr)
            break

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