import socket
import sys

def descoberta(SERVIDOR_PORTA):
    IP_HOST = '255.255.255.255'

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    except socket.error:
        print('Erro ao criar socket')
        sys.exit()

    sock.bind((IP_HOST, SERVIDOR_PORTA))
    return sock, IP_HOST