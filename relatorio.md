# Relatório - Lab 01 SO2

Implementado em Python usando `threading`. O GIL não atrapalha na maior parte dos exercícios porque eles são sobre sincronização (mutex, barreira, variável de condição), não sobre ganho de desempenho por paralelismo real de CPU. A única exceção é o exercício 6, que mede speedup - lá o GIL aparece e comento o resultado.

Cada exercício está na sua própria pasta (`exercicio1/`, `exercicio2/`, ...) e roda sozinho com `python3 arquivo.py`.

## Exercício 1 - Corrida de cavalos

Cada cavalo é uma thread. Uso duas barreiras (`threading.Barrier`):

- uma pra largada, garantindo que todo mundo começa junto;
- outra a cada rodada, com uma função de callback (`action`) que checa quem cruzou a linha de chegada.

O `action` é importante: numa primeira versão eu deixava cada thread checar sozinha quem tinha ganhado, depois de sair da barreira. Isso travava (testei e reproduzi o deadlock várias vezes) porque uma thread mais rápida conseguia começar a próxima rodada e mexer no placar enquanto outra ainda estava conferindo o resultado da rodada anterior, e algumas threads ficavam esperando numa barreira que ninguém mais ia alcançar. Passando a checagem pro `action` da barreira (que roda uma vez só, antes de soltar qualquer thread), isso some.

Desempate: se mais de um cavalo cruza a linha na mesma rodada, ganha quem foi mais longe; empatando de verdade, desempata por ordem alfabética do nome. Assim o resultado nunca depende de qual thread "chegou primeiro" no lock.

## Exercício 2 - Buffer produtor/consumidor

Buffer com um `Lock` e duas `Condition` (`tem_espaco` e `tem_item`). Produtor espera em `tem_espaco` se o buffer está cheio, consumidor espera em `tem_item` se está vazio - os dois com `wait()` de verdade, sem busy-wait. Uso `while` em vez de `if` antes do `wait()` porque com vários produtores/consumidores a condição pode não valer mais quando a thread acorda (outra pode ter chegado na frente).

Pra encerrar os consumidores no final, mando um item "poison pill" pra cada um.

Rodei o experimento variando o tamanho do buffer (4 produtores, 3 consumidores, 200 itens cada):

| N | itens/s | latência média (ms) |
|---|---|---|
| 1 | ~1500 | ~1.3 |
| 5 | ~1550 | ~3.4 |
| 20 | ~1550 | ~12.7 |
| 100 | ~1600 | ~47 |

A vazão não muda muito - quem limita é a velocidade dos consumidores, não o tamanho do buffer. Já a latência cresce bastante com N: um buffer maior deixa mais item acumulado esperando pra ser processado.

## Exercício 3 - Transferências entre contas

Um lock por conta. Pra transferir entre duas contas sem risco de deadlock, sempre travo primeiro a de índice menor - se não fizer isso, duas threads transferindo em sentidos opostos (A→B numa, B→A na outra) podem travar uma conta cada e ficar esperando a outra pra sempre.

Fiz também uma versão sem trava nenhuma, com um `time.sleep(0)` entre ler e escrever o saldo pra aumentar a chance de duas threads mexerem na mesma conta ao mesmo tempo. Uma execução:

```
com trava:  antes=20000 depois=20000 diff=0
sem trava:  antes=20000 depois=22140 diff=2140
```

A soma total só se mantém constante na versão com trava (tem um `assert` conferindo isso). Sem trava, updates se perdem porque ler+escrever o saldo não é uma operação atômica - rodando várias vezes a diferença muda de sinal e de tamanho, mas quase nunca fica em zero.

## Exercício 4 - Pipeline de três estágios

Três threads (captura, processamento, gravação) ligadas por duas filas limitadas. A fila é a mesma ideia do exercício 2: um `Lock` e duas `Condition`.

O encerramento usa poison pill em cascata. A captura, quando acaba os N itens, coloca o sentinela `FIM` na primeira fila. O processamento, ao receber o `FIM`, repassa ele pra segunda fila antes de sair. Sem esse repasse a gravação ficaria esperando em `wait()` pra sempre, já que ninguém mais ia colocar item nenhum pra ela.

Pra provar que não tem deadlock uso `join(timeout=30)` e depois checo `is_alive()`. Um `join()` sem timeout num programa travado só fica pendurado e não acusa nada, então o timeout é o que transforma o travamento em erro visível. Pra provar que nenhum item se perde comparo a lista de IDs gravados com `range(N)` - isso pega tanto item que sumiu quanto item duplicado.

Saída de uma execução:

```
itens gravados: 50 de 50
threads presas: 0
ok
```

## Exercício 5 - Pool de threads

Pool fixo de 4 threads consumindo uma fila de tarefas. A fila aqui não tem limite (a questão não pede), então só preciso de um `Lock` e uma `Condition` pra "tem tarefa" - só o `get` bloqueia, o `put` nunca espera.

A thread principal lê números do stdin até o EOF e enfileira cada um como uma tarefa de teste de primalidade. No EOF ela coloca uma poison pill **por worker**. Não dá pra mandar só uma: só uma thread ia pegar e as outras três ficariam esperando pra sempre.

Pra provar que a fila é thread-safe e que nada se perde, conto quantas tarefas enfileirei e comparo com quantos resultados voltaram. Se duas threads pegassem a mesma tarefa ou uma sumisse, a conta não fecharia. A lista de resultados também tem lock, porque `append` de várias threads ao mesmo tempo cai na mesma corrida do exercício 3.

```
$ printf '7\n10\n1000003\n15\nabc\n97\n' | python3 pool.py
ignorado: abc

tarefas enviadas: 5 | resultados: 5
7: primo
10: nao primo
15: nao primo
97: primo
1000003: primo
```

Testei também com `seq 1 500 | python3 pool.py` pra dar carga de verdade nas quatro threads, e a contagem fecha em 500.

## Exercício 6 - Soma e histograma em paralelo

Arquivo com 3 milhões de inteiros. Leio ele uma vez e divido a lista em P blocos, um por thread.

Cada thread faz o "map" no bloco dela com soma e histograma em variáveis locais, **sem lock nenhum**. Só no final de cada thread eu pego o lock uma única vez pra somar o parcial no resultado global. É essa a exclusão mútua mínima: P travamentos no total, não um por elemento. Se eu fosse somando direto na variável global a cada número, o lock viraria o gargalo e a versão paralela ficaria mais lenta que a sequencial.

Conferência: comparo a soma com a versão sequencial e checo se o total do histograma bate com a quantidade de números.

| P | tempo (s) | speedup |
|---|---|---|
| 1 | 0.14 | 1.00x |
| 2 | 0.14 | 1.01x |
| 4 | 0.15 | 0.93x |
| 8 | 0.15 | 0.93x |

O speedup fica em 1 e ainda piora um pouco com 8 threads. Isso é o GIL: em Python só uma thread executa bytecode por vez, então trabalho puro de CPU não paraleliza de verdade. O que sobra é o custo de criar e alternar entre as threads, que aparece como uma piora pequena. Pra ter speedup real aqui seria preciso usar `multiprocessing` (processos separados, cada um com seu interpretador) ou uma linguagem sem GIL como C.

## Exercício 7 - Jantar dos filósofos

Cinco filósofos, cinco garfos representados por `Lock`. O deadlock clássico é todo mundo pegar o garfo da esquerda ao mesmo tempo e ficar esperando o da direita pra sempre. Implementei as duas soluções pedidas:

**(a) Ordem global de aquisição.** Cada filósofo pega primeiro o garfo de índice menor. É o mesmo raciocínio do exercício 3: se ninguém segura um recurso "maior" esperando um "menor", o ciclo de espera não fecha.

**(b) Semáforo limitando a quatro.** Os garfos são pegos na ordem natural (esquerda, depois direita), mas um `Semaphore(4)` deixa no máximo quatro filósofos tentando comer ao mesmo tempo. Com cinco garfos e quatro concorrentes, sempre sobra garfo pra pelo menos um terminar.

Sobre starvation: na primeira versão o filósofo voltava direto pra fila depois de comer, e quem estava mais perto do lock acabava comendo várias vezes seguidas. Coloquei um tempo de "pensar" depois de cada refeição, que dá janela pros vizinhos entrarem.

Métricas de uma execução de 5 segundos por solução:

```
solucao a - ordem global de aquisicao
  filosofo 0: 136 refeicoes | maior espera 55.5 ms
  filosofo 1: 141 refeicoes | maior espera 36.8 ms
  filosofo 2: 152 refeicoes | maior espera 29.4 ms
  filosofo 3: 154 refeicoes | maior espera 29.9 ms
  filosofo 4: 133 refeicoes | maior espera 50.9 ms
  total: 716 | menor: 133 | maior: 154

solucao b - semaforo limitando a 4
  filosofo 0: 123 refeicoes | maior espera 55.3 ms
  filosofo 1: 120 refeicoes | maior espera 57.3 ms
  filosofo 2: 119 refeicoes | maior espera 52.9 ms
  filosofo 3: 121 refeicoes | maior espera 56.5 ms
  filosofo 4: 121 refeicoes | maior espera 60.2 ms
  total: 604 | menor: 119 | maior: 123
```

A comparação entre as duas é a parte interessante. A solução (a) come mais no total (716 contra 604), mas distribui pior - 133 contra 154 entre o pior e o melhor filósofo. A ordem global cria uma assimetria: o filósofo 4 é o único que pega o garfo da direita primeiro, porque 0 é menor que 4, e ele e o vizinho 0 ficam em desvantagem.

A solução (b) trata todo mundo igual e a diferença cai pra 4 refeições, mas o semáforo mantém um filósofo fora da disputa o tempo todo e a vazão cai. Resumindo: (a) é mais rápida, (b) é mais justa.

## Exercício 8 - Rajadas e backpressure

Extensão do exercício 2. O backpressure já sai de graça do buffer limitado - quando enche, o `put` bloqueia e o produtor para sozinho. O trabalho aqui foi provocar e medir isso.

Os produtores alternam entre rajada (15 a 30 itens quase sem pausa) e ociosidade (dormem de 0,2 a 0,4 s). E os consumidores ficam propositalmente lentos entre 3 s e 9 s de execução, simulando a queda na taxa de consumo. Uma thread monitora amostra a ocupação do buffer a cada 100 ms.

Também cronometro quanto tempo cada `put` ficou preso esperando espaço e somo tudo - esse número é a prova de que o backpressure agiu.

Ocupação ao longo do tempo (capacidade 10, trecho):

```
  0.8s |############                  | 4
  1.4s |###############               | 5
  2.0s |#####################         | 7
  2.4s |##############################| 10
  3.0s |##############################| 10
  ...   (fica preso em 10 de 3s ate 8.4s)
  8.4s |                              | 0
  8.8s |                              | 0

vezes que um produtor bloqueou: 620
tempo total bloqueado: 9.65s
ocupacao media: 6.6
```

Dá pra ver três fases. Antes dos 3 s a ocupação oscila entre 0 e 7: as rajadas enchem o buffer e a ociosidade dá tempo dos consumidores esvaziarem - sistema estável. Entre 3 s e 8,4 s a ocupação gruda no teto porque os consumidores ficaram lentos; os produtores não conseguem mais despejar item e passam a esperar, e os 9,65 s de tempo bloqueado somados confirmam. Depois dos 8,4 s os consumidores voltam ao normal e o buffer esvazia rápido, sem deixar fila residual.

O ponto principal: nenhum item foi descartado em momento nenhum. O backpressure regula a produção em vez de perder dado, que é a vantagem de bloquear o produtor em vez de jogar o item fora quando o buffer enche.

## Exercício 9 - Revezamento com barreira

No exercício 1 usei a `threading.Barrier` pronta. Aqui a questão deixa implementar na mão, então fiz a barreira com `Lock` e `Condition`.

O detalhe que dá trabalho é que a barreira precisa ser reutilizável, porque a corrida tem várias pernas seguidas. Só contar quantas threads chegaram não basta: quando a última chega e libera todo mundo, uma thread rápida pode dar a volta e entrar na barreira de novo antes das outras acordarem, e seria contada na rodada errada. Por isso guardo um número de geração, e cada thread espera enquanto a geração não mudar em vez de esperar o contador zerar.

Cada equipe corre 200 rodadas e eu cronometro, convertendo pra rodadas por minuto:

| K | tempo (s) | rodadas/min |
|---|---|---|
| 2 | 0.33 | 36888 |
| 4 | 0.37 | 32850 |
| 8 | 0.39 | 30413 |
| 16 | 0.41 | 29026 |

A vazão cai conforme a equipe cresce, mas cai devagar: de 2 pra 16 threads são 8 vezes mais corredores e a perda é de uns 20%.

O motivo é que a barreira é sempre limitada pela thread mais lenta da rodada. Como cada perna leva um tempo aleatório, quanto mais threads na equipe maior a chance de alguma sortear um tempo alto, e todas as outras ficam paradas esperando. A queda ser suave e não proporcional a K mostra que o custo da barreira em si (o lock e o `notify_all`) é pequeno perto do tempo da perna.

## Exercício 10 - Watchdog e ordem total de travamento

Seis threads disputando quatro recursos. Na versão com problema, cada thread sorteia dois recursos e pega na ordem que sorteou. Cedo ou tarde duas escolhem o mesmo par em ordens opostas, travam um recurso cada e esperam pra sempre.

O watchdog não tem como olhar dentro dos locks, então ele mede progresso: um contador global de operações concluídas. Se o contador não muda por 3 segundos, alguma coisa travou.

Só dizer "travou" não ajuda, então cada thread registra num dicionário compartilhado o que está segurando e o que está esperando, antes de bloquear. Quando o watchdog dispara, ele imprime esse mapa e dá pra enxergar o ciclo. As threads são daemon, senão o programa nunca terminaria depois do deadlock.

```
=== sem ordem de travamento ===

[watchdog] sem progresso ha 3s (progresso parado em 0)
  t0: segura [1] e espera recurso 3
  t1: segura [3] e espera recurso 1
  t2: segura [2] e espera recurso 3
  t3: segura [] e espera recurso 2
  t4: segura [] e espera recurso 1
  t5: segura [] e espera recurso 3
operacoes concluidas: 0
threads travadas: ['t0', 't1', 't2', 't3', 't4', 't5']
watchdog acusou deadlock: sim

=== com ordem total de travamento ===
operacoes concluidas: 1800
threads travadas: nenhuma
watchdog acusou deadlock: nao
```

O t0 segurando o recurso 1 e esperando o 3, com o t1 segurando o 3 e esperando o 1, é exatamente o ciclo de espera da teoria. As outras quatro threads travaram por tabela, esperando recursos que esses dois nunca vão soltar - por isso o progresso ficou em 0.

A correção é a mesma ideia dos exercícios 3 e 7: ordem total de travamento, sempre o recurso de índice menor primeiro. Com ela foram 1800 operações concluídas, nenhuma thread travada e o watchdog não acusou nada.

## Conclusão

Uma coisa que apareceu em três exercícios diferentes (3, 7 e 10) foi a ordem total de travamento. É uma solução simples de escrever e resolve deadlock em qualquer situação em que as threads precisam de mais de um recurso ao mesmo tempo - basta todo mundo pegar na mesma ordem pra que o ciclo de espera não consiga fechar.

O outro padrão que se repetiu foi a poison pill (exercícios 2, 4 e 5) pra encerrar threads que estão bloqueadas esperando item. E a lição prática nesse caso é sempre mandar uma pill por thread, ou repassar ela adiante quando o pipeline tem mais de um estágio.
