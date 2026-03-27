import sys
import datetime as dt
import processamento as pss
import descoberta as dsc
import socket

def main():

    #estrutura de dados da soma agregada mantida pelo servidor
    num_reqs = 0 #numero de requiscoes totais
    somatorio = 0
    id_req = 0 #id da req atual do cliente
    date = dt.datetime.now()

    if len(sys.argv) > 1: 
        SERVIDOR_PORTA = int(sys.argv[1]) #pega o primeiro argumento da linha de comando
    
    else:
        print("Nenhuma porta fornecida")
        sys.exit()
    
    

    #criacao do socket
    sock_client, IP_HOST = dsc.descoberta(SERVIDOR_PORTA)

    print(f"{date} num_reqs {num_reqs} total_sum {somatorio}")

    #processa requisicoes
    pss.processamento_server(sock_client, num_reqs, somatorio, IP_HOST, SERVIDOR_PORTA, date)        
