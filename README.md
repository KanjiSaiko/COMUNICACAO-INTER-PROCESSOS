# Relatório - Trabalho Prático Parte 1: Comunicação Confiável Inter-Processos

**Disciplina:** Sistemas Distribuídos e Tolerantes a Falhas
**Semestre:** 2026/1
**Nome:** Henrique de Lima Bortolomiol

---

## A. Implementação dos Subserviços

O sistema foi modularizado em três subserviços principais para garantir separação de responsabilidades:

* **Subserviço de Descoberta:** Implementado usando o paradigma de *Broadcast* UDP. O cliente altera as opções do socket (`SO_BROADCAST`) e envia a string `b"discover"` para o endereço `255.255.255.255`. O servidor, ouvindo ativamente na interface `0.0.0.0`, intercepta a mensagem e responde via *Unicast* com `b"ack_discover"`, estabelecendo assim o conhecimento do IP pelo cliente.
* **Subserviço de Processamento:** Responsável pelo motor de confiabilidade *Stop-and-Wait*. Utiliza a biblioteca `struct` para garantir o tráfego estrito de bytes e o empacotamento exato de inteiros sem sinal de 64 bits (`!iQ` para envio, `!iiQ` para resposta), prevenindo *overflows* na agregação.
* **Subserviço de Interface:** Isolado no arquivo `interface.py`, formata as saídas de log do sistema. Utiliza a biblioteca `datetime` (`%Y-%m-%d %H:%M:%S`) para garantir o rigor visual exigido pela especificação, separando a lógica de apresentação da lógica de rede.

## B. Sincronização no Acesso a Dados

A principal área que exigiu sincronização foi a interface do cliente. Para cumprir o requisito de não-bloqueio entre a leitura do teclado e a recepção de confirmações (ACKs), adotamos uma arquitetura multithreading:
* **Thread Principal:** Bloqueia na entrada padrão (`input()`), empacota a mensagem e gerencia o temporizador de retransmissão.
* **Thread Ouvinte (Daemon):** Fica dedicada passivamente ao `recvfrom()`, desempacotando respostas e validando identificadores.
* **Sincronização:** Utilizamos a primitiva `threading.Event()` para sinalizar o sucesso do envio entre as threads, evitando condições de corrida. Além disso, um dicionário de estado compartilhado em memória (`estado_atual`) foi implementado para que a thread ouvinte saiba qual ID de requisição validar sem a necessidade de instanciar múltiplas threads.

## C. Principais Estruturas e Funções Implementadas

No servidor, o gerenciamento de estado exigiu a implementação de estruturas de dados robustas mantidas inteiramente em memória:
* `tabela_1` (Dicionário de Clientes): Mapeia o estado histórico de cada conexão. **Decisão de Arquitetura:** Utilizamos a tupla `(IP, Porta)` fornecida pelo socket como chave primária, em vez de apenas o endereço IP. Isso garante o correto isolamento das sessões e previne falhas lógicas caso múltiplos clientes rodem na mesma máquina local ou caso um cliente sofra reinicialização (ganhando uma nova porta efêmera do SO). A tabela armazena o `last_req` e a `last_sum` para tratar retransmissões duplicadas.
* `tabela_2` (Agregação Global): Mantém o `num_reqs` total e o `total_sum` de forma consistente para acesso rápido durante o empacotamento das respostas.

## D. Uso das Primitivas de Comunicação Inter-Processos

O projeto foi construído exclusivamente sobre a API UDP (`socket.AF_INET`, `socket.SOCK_DGRAM`). 
Diferentemente do TCP, onde primitivas como `listen()` e `accept()` gerenciam o estado da conexão, nosso servidor utiliza um único socket atrelado (`bind`) universalmente à porta estipulada. Toda a comunicação flui através das primitivas *connectionless* `recvfrom()` e `sendto()`. Como o UDP não oferece garantias de entrega, toda a confiabilidade foi transferida para a camada de aplicação através de identificadores de requisição e temporizadores de ACK.

## E. Problemas Encontrados e Resoluções

Durante o desenvolvimento, lidamos com os seguintes desafios lógicos e de redes:
1. **Conflito de Tamanho de Payload (`struct.error`):** Inicialmente, o servidor falhava ao tentar desempacotar pacotes de descoberta (8 bytes) usando a máscara de processamento de 12 bytes (`!iQ`). A solução foi unificar o loop de recepção do servidor e utilizar a verificação de tamanho (`len(message) == 12`) e de conteúdo (`message == b"discover"`) para rotear o pacote internamente antes de tentar desempacotá-lo.
2. **Retransmissões Duplicadas e Alteração de Estado:** Ao simular perda de ACKs injetando atrasos artificiais no servidor, notamos que o servidor somava requisições retransmitidas múltiplas vezes. Resolvemos isso implementando uma checagem rigorosa na `tabela_1`. Quando um ID já processado é detectado, o servidor extrai o estado histórico (soma e número de requisições anteriores) e reenvia o ACK sem modificar os contadores globais.