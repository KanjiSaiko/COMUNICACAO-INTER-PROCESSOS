import sys
import datetime as dt
import processamento as pss
import descoberta as dsc

def main():
    date = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if len(sys.argv) > 1: 
        CLIENTE_PORTA = int(sys.argv[1]) #pega o primeiro argumento da linha de comando
    else:
        print("Nenhuma porta fornecida")
        sys.exit()

    #DESCOBERTA ATRAVES DE BROADCAST
    sock, CLIENTE_IP = dsc.descoberta_cliente(CLIENTE_PORTA)


    print(f"{date} server addr {CLIENTE_IP}")

    pss.processamento_cliente(sock, CLIENTE_IP, CLIENTE_PORTA)


if __name__ == "__main__":
    main()