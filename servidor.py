import sys
import datetime as dt
import processamento as pss
import descoberta as dsc

def main():

    num_reqs = 0 #numero de requiscoes totais
    somatorio = 0
    date = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    if len(sys.argv) > 2: 
        SERVIDOR_PORTA = int(sys.argv[1]) #pega o primeiro argumento da linha de comando
        ID_NUM = int(sys.argv[2]) #segundo argumento sendo o id numerico para o algoritmo valentao
    
    else:
        print("Nenhuma porta ou ID fornecido")
        sys.exit()
    
    #criacao do socket
    sock_client = dsc.descoberta_server(SERVIDOR_PORTA)

    #comunicacao servidor-servidor + bootstrap de eleicao inicial
    lista_servidores_inicial = {}
    sou_primario = dsc.servidor_servidor(sock_client, ID_NUM, SERVIDOR_PORTA, lista_servidores_inicial)

    print(f"{date} num_reqs {num_reqs} total_sum {somatorio}")

    #processa requisicoes
    pss.processamento_server(sock_client, num_reqs, somatorio, ID_NUM, sou_primario, lista_servidores_inicial)


if __name__ == "__main__":
    main()