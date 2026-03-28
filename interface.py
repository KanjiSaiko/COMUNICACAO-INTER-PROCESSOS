def interface_server(date, ip_client, id_req, valor, tabela_2):
    print(f"{date} client {ip_client} id_req {id_req} value {valor} num_reqs {tabela_2['num_reqs']} total_sum {tabela_2['total_sum']}")


def interface_cliente(date, ip_server, id_req, numero, num_reqs, somatorio):
    print(f"{date} server {ip_server} id_req {id_req} value {numero} num_reqs {num_reqs} total_sum {somatorio}")
