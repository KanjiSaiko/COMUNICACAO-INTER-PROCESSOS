# Relatório - Trabalho Prático Parte 2: Replicação e Eleição de Líder

**Disciplina:** Sistemas Distribuídos e Tolerantes a Falhas
**Semestre:** 2026/1
**Nome:** Henrique de Lima Bortolomiol

---

## Ambiente de Testes

* **Sistema Operacional:** Linux (distribuição Ubuntu/Debian), conforme exigido pela especificação.
* **Linguagem/Compilador:** Python 3 (módulos padrão `socket`, `struct`, `threading`, `datetime`, `time` — sem dependências externas).
* **Topologia de testes:** três ou mais processos servidor rodando em máquinas distintas da mesma rede local (broadcast `255.255.255.255` habilitado via `SO_BROADCAST`), e um ou mais processos cliente na mesma sub-rede.

---

## A. Implementação dos Subserviços (Parte 1)

O sistema continua modularizado em três subserviços principais:

* **Subserviço de Descoberta:** Implementado usando o paradigma de *Broadcast* UDP. O cliente envia a string `b"discover"` para `255.255.255.255` e retransmite com timeout até obter resposta — isso evita que o cliente trave indefinidamente caso o pacote se perca ou caso a rede ainda esteja decidindo o líder. O servidor primário, ouvindo ativamente em `0.0.0.0`, responde via *Unicast* com `b"ack_discover"`. **Importante:** apenas o servidor que está atuando como primário responde ao `discover` — os backups silenciam essa mensagem, garantindo que todo cliente novo já descubra direto o endereço correto.
* **Subserviço de Processamento:** Motor de confiabilidade *Stop-and-Wait*, com identificadores de requisição e ACKs (`!iQ` para envio, `!iiQ` para resposta) para prevenir duplicação e perda silenciosa.
* **Subserviço de Interface:** Isolado em `interface.py`, formata as saídas de log (`%Y-%m-%d %H:%M:%S`), mantendo a lógica de apresentação separada da lógica de rede.

## B. Eleição de Líder — Algoritmo do Valentão (Bully Algorithm)

### B.1 Por que o Valentão

A especificação exige que, na falha do servidor primário, um dos backups assuma via algoritmo do Valentão. Essa escolha é adequada ao nosso cenário porque:

1. Cada processo já possui um identificador numérico único (`ID_NUM`), passado por linha de comando — exatamente a premissa do algoritmo.
2. O Valentão converge rapidamente (poucas rodadas de mensagens) quando o número de processos é pequeno, como é o caso aqui (tipicamente 3-5 réplicas).
3. Não exige um anel lógico nem ordenação de mensagens entre processos, apenas comparação direta de IDs — o que se encaixa bem em comunicação UDP best-effort, onde manter estruturas topológicas mais complexas (como em algoritmos de anel) seria mais frágil a perdas de pacote.

### B.2 Eleição inicial (bootstrap)

Diferente da primeira versão do trabalho — em que o primário era decidido por um valor de ID fixo no código —, a eleição inicial agora também segue o princípio do Valentão: ao subir, cada servidor envia um broadcast `SRV` (3 bytes de prefixo + 4 bytes de ID) e aguarda, por uma janela de tempo curta (3s, com retransmissão a cada 0,5s para tolerar perda de pacote), respostas `ASRV` de servidores já ativos. Se, ao final da janela, nenhum servidor com ID **maior** que o seu próprio respondeu, o processo assume que é o maior ID vivo na rede e nasce como primário; caso contrário, nasce como backup, esperando o `BEAT` (heartbeat) do primário legítimo. Essa mudança elimina a dependência de um ID mágico fixo e permite subir qualquer combinação de réplicas, em qualquer ordem.

### B.3 Funcionamento em regime (detecção de falha e nova eleição)

* **Heartbeat:** o primário envia periodicamente (a cada 2s) um pacote `BEAT` para todos os backups conhecidos.
* **Detecção de falha:** cada backup mantém um relógio interno (`ultimo_heartbeat`). Se mais de 5s se passarem sem receber um `BEAT`, o backup declara o primário morto e inicia uma eleição.
* **Disputa (`ELEC`/`ANSR`):** o backup que detectou a falha envia `ELEC` (contendo seu próprio ID) para todos os servidores conhecidos com ID maior que o seu. Se algum deles estiver vivo, responde `ANSR` ("cale-se, eu cuido disso") e força seu próprio relógio de heartbeat a expirar imediatamente — provocando, em cascata, que o processo de maior ID também inicie sua verificação e, não havendo ninguém maior que ele, vença sem disputa.
* **Vitória e anúncio (`COOR`/`NLDR`):** quem não recebe nenhum `ANSR` dentro do tempo de espera (2s) se autoproclama o novo primário, e propaga essa informação em duas frentes — **em rajada** (três retransmissões, dado que UDP não garante entrega):
  * `COOR` para os demais servidores, que passam a tratá-lo como novo primário e resetam seus relógios de heartbeat;
  * `NLDR` para todos os clientes que já constavam na tabela de sessões replicada — permitindo que cada cliente redirecione, de forma transparente, seus próximos envios para o novo primário, sem qualquer ação manual do usuário.

Esse desenho garante a propriedade central do enunciado: a falha do primário não interrompe o serviço, e os clientes continuam a soma de onde estavam, agora contra o novo primário.

## C. Replicação Passiva

### C.1 Esquema adotado

Implementamos Replicação Passiva clássica: existe um único *Replica Manager* (RM) primário, que é o único a processar requisições de clientes e responder ACKs; os demais RMs atuam como backups silenciosos. Após cada operação de soma bem-sucedida, o primário propaga o novo estado a todos os backups conhecidos através de uma mensagem `UPDT`, contendo:

* o ID de quem está propagando (para que o backup também aprenda quem é o primário, caso ainda não soubesse);
* o novo total de requisições e a nova soma acumulada (estado global);
* o ID da última requisição processada, e o endereço (IP + porta) do cliente que a originou — para que o backup também consiga reconstruir, por cliente, o histórico necessário para deduplicar retransmissões caso ele próprio se torne primário no futuro.

Cada backup, ao receber um `UPDT`, atualiza tanto o seu estado agregado global quanto a entrada daquele cliente específico em sua própria cópia da tabela de sessões. Com isso, **(1)** todo cliente sempre conversa com a mesma cópia primária (os backups recusam silenciosamente requisições de soma, fazendo o cliente retransmitir até ouvir do primário correto) e **(2)** o estado é propagado a cada operação, como exigido.

### C.2 Por que a réplica recém-eleita já está pronta para assumir

Como a replicação ocorre em tempo real, a cada requisição, no momento em que um backup vence a eleição ele já dispõe (modulo a última requisição em trânsito, sujeita a perda de pacote UDP) do mesmo total acumulado e da mesma tabela de clientes que o primário tinha. Isso é o que permite ao novo primário continuar a soma exatamente de onde o anterior parou, em vez de zerar o serviço.

## D. Sincronização no Acesso a Dados

Continua valendo a arquitetura multithreading da Parte 1 no cliente (thread principal bloqueada em `input()` + thread ouvinte dedicada a `recvfrom()`, sincronizadas por `threading.Event()`).

No servidor, a Parte 2 introduziu duas novas threads daemon por processo, que compartilham estado em memória com a thread principal através de dicionários mutáveis (`estado_srv`, `lista_servidores`), sem necessidade de locks explícitos — o GIL do CPython garante atomicidade nas operações de leitura/escrita de chaves individuais, e o desenho do protocolo evita que duas threads escrevam a mesma chave de forma conflitante na janela crítica:

* **Thread de Heartbeat:** ativa apenas quando o processo é primário; envia `BEAT` periodicamente a todos os backups.
* **Thread de Monitoramento de Falha:** ativa apenas quando o processo é backup; mede o tempo desde o último `BEAT`, conduz a disputa do Valentão quando necessário, e atualiza `estado_srv['is_primary']` ao final do processo.

## E. Principais Estruturas e Funções Implementadas

* `tabela_1` (Dicionário de Clientes): inalterada em relação à Parte 1 — chave `(IP, Porta)`, valores com `last_req` e `last_sum` para deduplicação. Na Parte 2, essa tabela também é replicada via `UPDT` para os backups, e usada pelo novo primário para notificar (`NLDR`) os clientes ativos no momento da troca.
* `tabela_2` (Agregação Global): mantém `num_reqs` e `total_sum`.
* `lista_servidores` (Dicionário `{ID: (IP, Porta)}`): nova estrutura da Parte 2, populada durante o bootstrap de descoberta entre servidores (`SRV`/`ASRV`) e mantida atualizada conforme novos servidores se anunciam. É usada para destinatário dos `BEAT`, `UPDT`, `ELEC`, `COOR`.
* `estado_srv` (Dicionário de estado compartilhado): nova estrutura da Parte 2 contendo `is_primary`, `ultimo_heartbeat`, `em_eleicao` e `recebeu_ansr` — o núcleo de controle do algoritmo do Valentão, compartilhado entre o loop principal e as duas threads daemon.

## F. Uso das Primitivas de Comunicação Inter-Processos

O projeto permanece construído exclusivamente sobre UDP (`socket.AF_INET`, `socket.SOCK_DGRAM`), com um único socket por processo atrelado (`bind`) à porta estipulada, atendendo tanto clientes quanto outros servidores através das mesmas primitivas *connectionless* `recvfrom()`/`sendto()`. O roteamento de cada datagrama recebido é feito por tamanho e, quando ambíguo, por conteúdo exato (ex.: distinguir `b"discover"` de um pacote de controle de 8 bytes antes de tentar desempacotar). Cada tipo de mensagem do protocolo usa um tamanho de payload exclusivo, evitando colisões na rota de decisão:

| Mensagem | Tamanho (bytes) | Formato `struct` | Direção |
|---|---|---|---|
| `discover` | 8 (literal) | string fixa | cliente → primário |
| `ack_discover` | 12 (literal) | string fixa | primário → cliente |
| `SRV` / `ASRV` (descoberta entre servidores) | 7 / 8 | `!3si` / `!4si` | servidor ↔ servidor |
| `BEAT`, `ELEC`, `ANSR`, `COOR`, `NLDR` | 8 | `!4si` | servidor ↔ servidor / servidor → cliente |
| Requisição de soma | 12 | `!iQ` | cliente → primário |
| ACK de soma | 16 | `!iiQ` | primário → cliente |
| `UPDT` (replicação) | 30 | `!4siiQiH4s` | primário → backups |

## G. Problemas Encontrados e Resoluções

1. **Conflito de Tamanho de Payload (Parte 1, mantido):** unificação do loop de recepção do servidor, roteando por tamanho e conteúdo antes de desempacotar.
2. **Retransmissões Duplicadas (Parte 1, mantido):** checagem rigorosa em `tabela_1` para reenviar o ACK histórico sem reprocessar a soma.
3. **Bloco de replicação inalcançável:** na primeira versão da replicação passiva, o tratamento da mensagem `UPDT` havia sido escrito como um `elif` aninhado *dentro* do bloco que trata requisições de soma (12 bytes) — como o tamanho real de `UPDT` nunca é 12, esse trecho nunca era executado, e os backups nunca recebiam o estado do primário. Resolvido movendo o tratamento de `UPDT` para um ramo independente no nível correto do roteamento por tamanho.
4. **Divergência entre tamanho assumido e tamanho real do `struct`:** o formato `!4siiQiH4s` usado na mensagem `UPDT` ocupa, na prática, 30 bytes (4+4+4+8+4+2+4), e não 26 como inicialmente assumido em um comentário do código. Como o roteamento de pacotes depende do tamanho exato, esse descompasso impedia qualquer backup de reconhecer a mensagem. Corrigido recalculando o tamanho via `struct.calcsize` e ajustando a checagem correspondente.
5. **Líder inicial fixo por ID:** a primeira versão decidia quem nascia primário comparando o `ID_NUM` a um valor fixo no código, o que só funcionava se exatamente um processo daquele ID específico estivesse em execução. Substituído por uma eleição inicial real: cada servidor anuncia-se via broadcast e aguarda, por uma janela curta, ser superado por algum ID maior; se não for, assume — eliminando a dependência de um ID mágico e permitindo qualquer combinação de réplicas.
6. **Cliente preso indefinidamente em caso de perda de pacote crítico:** como UDP não garante entrega, a perda do `discover` inicial (sem líder ainda eleito) ou do `NLDR`/`COOR` durante uma troca de liderança deixava, respectivamente, o cliente sem nunca descobrir o servidor ou o backup preso esperando o aviso de vitória que nunca chegou. Mitigado com retransmissão por timeout no `discover` do cliente, e reenvio em rajada (três tentativas) do `COOR` e do `NLDR` no momento da vitória da eleição.
7. **Eleições concorrentes com três ou mais réplicas:** ao testar com três servidores, dois backups por vezes detectavam a falha do primário quase simultaneamente e iniciavam eleições paralelas. Validamos que o protocolo já resolve esse caso corretamente: o backup de menor ID recebe `ANSR` do de maior ID, desiste e aguarda o `COOR`, evitando dois primários simultâneos — comportamento confirmado em testes controlados com três réplicas.
8. **Threads de tolerância a falhas presas após o encerramento do processo:** ao finalizar um servidor (ex.: `Ctrl+C` ou fechamento do terminal), as threads de heartbeat e monitoramento continuavam tentando usar o socket já encerrado, gerando um volume excessivo de mensagens de erro. Resolvido encerrando essas threads de forma limpa ao detectar que o socket foi fechado.
