
def interface_server(date, addr, id_req, valor, num_reqs, somatorio):
    print(f"{date} client {addr} id_req {id_req} value {valor} num_reqs {num_reqs} total_sum {somatorio}")


def interface_cliente(date, addr, id_req, numero, num_reqs, somatorio):
    print(f"{date} server {addr} id_req {id_req} value {numero} num_reqs {num_reqs} total_sum {somatorio}")