import threading
import random
import time

N = 5
DURACAO = 5


class Jantar:
    def __init__(self, solucao):
        self.solucao = solucao
        self.garfos = [threading.Lock() for _ in range(N)]
        self.limite = threading.Semaphore(N - 1)  # so na solucao b
        self.refeicoes = [0] * N
        self.maior_espera = [0.0] * N
        self.parar = threading.Event()

    def pegar_ordem_global(self, i):
        esq, dir = i, (i + 1) % N
        a, b = min(esq, dir), max(esq, dir)  # sempre o menor indice primeiro
        self.garfos[a].acquire()
        self.garfos[b].acquire()
        return a, b

    def pegar_com_semaforo(self, i):
        esq, dir = i, (i + 1) % N
        self.limite.acquire()
        self.garfos[esq].acquire()
        self.garfos[dir].acquire()
        return esq, dir

    def filosofo(self, i):
        while not self.parar.is_set():
            inicio = time.perf_counter()
            if self.solucao == "a":
                a, b = self.pegar_ordem_global(i)
            else:
                a, b = self.pegar_com_semaforo(i)
            espera = time.perf_counter() - inicio
            self.maior_espera[i] = max(self.maior_espera[i], espera)

            time.sleep(random.uniform(0.005, 0.02))  # comendo
            self.refeicoes[i] += 1

            self.garfos[b].release()
            self.garfos[a].release()
            if self.solucao == "b":
                self.limite.release()

            time.sleep(random.uniform(0.005, 0.02))  # pensando, evita starvation

    def rodar(self):
        threads = [threading.Thread(target=self.filosofo, args=(i,)) for i in range(N)]
        for t in threads:
            t.start()
        time.sleep(DURACAO)
        self.parar.set()
        for t in threads:
            t.join(timeout=10)
        assert not any(t.is_alive() for t in threads), "deadlock"


def relatar(nome, jantar):
    print(f"\n{nome}")
    for i in range(N):
        print(f"  filosofo {i}: {jantar.refeicoes[i]} refeicoes | "
              f"maior espera {jantar.maior_espera[i] * 1000:.1f} ms")
    total = sum(jantar.refeicoes)
    print(f"  total: {total} | menor: {min(jantar.refeicoes)} | maior: {max(jantar.refeicoes)}")


for sol, nome in (("a", "solucao a - ordem global de aquisicao"),
                  ("b", "solucao b - semaforo limitando a 4")):
    j = Jantar(sol)
    j.rodar()
    relatar(nome, j)
