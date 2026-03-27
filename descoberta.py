import socket
import struct
import sys

def descoberta(SERVIDOR_PORTA):
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

    return sock, addr