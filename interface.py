import datetime as dt


def interface_server(ip_client, id_req, valor, tabela_2):
    date = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"{date} client {ip_client} id_req {id_req} value {valor} num_reqs {tabela_2['num_reqs']} total_sum {tabela_2['total_sum']}")


def interface_cliente(ip_server, id_req, numero, num_reqs, somatorio):
    date = dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"{date} server {ip_server} id_req {id_req} value {numero} num_reqs {num_reqs} total_sum {somatorio}")
