import threading
import random
import time
import statistics
from collections import deque

FIM = object()  # sinal pra um consumidor parar


class Buffer:
    def __init__(self, capacidade):
        self.capacidade = capacidade
        self.fila = deque()
        self.lock = threading.Lock()
        self.tem_espaco = threading.Condition(self.lock)
        self.tem_item = threading.Condition(self.lock)

    def put(self, item):
        with self.tem_espaco:
            while len(self.fila) >= self.capacidade:
                self.tem_espaco.wait()
            self.fila.append(item)
            self.tem_item.notify()

    def get(self):
        with self.tem_item:
            while not self.fila:
                self.tem_item.wait()
            item = self.fila.popleft()
            self.tem_espaco.notify()
            return item


def produtor(buf, n_itens):
    for _ in range(n_itens):
        time.sleep(random.uniform(0.0005, 0.003))
        buf.put(time.perf_counter())


def consumidor(buf, lock, latencias):
    while True:
        item = buf.get()
        if item is FIM:
            break
        with lock:
            latencias.append(time.perf_counter() - item)
        time.sleep(random.uniform(0.0005, 0.003))


def rodar(capacidade, n_produtores=4, n_consumidores=3, itens_por_produtor=200):
    buf = Buffer(capacidade)
    lock = threading.Lock()
    latencias = []

    produtores = [
        threading.Thread(target=produtor, args=(buf, itens_por_produtor))
        for _ in range(n_produtores)
    ]
    consumidores = [
        threading.Thread(target=consumidor, args=(buf, lock, latencias))
        for _ in range(n_consumidores)
    ]

    inicio = time.perf_counter()
    for t in produtores + consumidores:
        t.start()
    for t in produtores:
        t.join()

    for _ in consumidores:
        buf.put(FIM)
    for t in consumidores:
        t.join()
    duracao = time.perf_counter() - inicio

    total = n_produtores * itens_por_produtor
    assert len(latencias) == total, "perdeu item no meio do caminho"

    vazao = total / duracao
    latencia_media_ms = statistics.mean(latencias) * 1000
    return vazao, latencia_media_ms


if __name__ == "__main__":
    print(f"{'N':>5} | {'itens/s':>10} | {'latencia media (ms)':>20}")
    for capacidade in (1, 5, 20, 100):
        vazao, latencia = rodar(capacidade)
        print(f"{capacidade:>5} | {vazao:>10.1f} | {latencia:>20.3f}")
