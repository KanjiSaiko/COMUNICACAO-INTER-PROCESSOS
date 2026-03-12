import socket
import struct

IP_HOST = "0.0.0.0"
PORTA = 5005

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

sock.bind((IP_HOST, PORTA))

somatorio = 0

while True:
    data, addr = sock.recvfrom(1024)
    try:
        valor = struct.unpack('!i', data)[0]
        somatorio += valor
        print(f"somatorio: {somatorio}")
    except:
        print(f"Recebido dado nao numerico: {data}")


