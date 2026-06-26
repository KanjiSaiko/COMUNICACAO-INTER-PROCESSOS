# Makefile para automatizacao da execucao do Sistema Distribuido

# Variaveis padrao caso o usuario esqueca de passar os parametros
PORT ?= 4000
ID ?= 1
FILE ?= RAND_NUM_1.txt

# Regra padrao (exibe ajuda)
help:
	@echo "Uso do Makefile para o Sistema de Agregacao UDP:"
	@echo "------------------------------------------------"
	@echo "make run-server PORT=<porta> ID=<id>  : Inicia uma instancia do Servidor"
	@echo "make run-client PORT=<porta>          : Inicia um Cliente interativo"
	@echo "make run-client-stress PORT=<porta>   : Inicia um Cliente em lote (arquivo txt)"
	@echo ""
	@echo "Exemplo: make run-server PORT=4000 ID=3"

# Executa o servidor
run-server:
	python3 servidor.py $(PORT) $(ID)

# Executa o cliente interativo
run-client:
	python3 cliente.py $(PORT)

# Executa o cliente em lote para teste de estresse (ler do arquivo)
run-client-stress:
	python3 cliente.py $(PORT) < $(FILE)