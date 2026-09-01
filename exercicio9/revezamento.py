import threading
import random
import time

RODADAS = 200


class Barreira:
    def __init__(self, n):
        self.n = n
        self.contador = 0
        self.geracao = 0  # sem isso, uma thread rapida entraria na rodada errada
        self.lock = threading.Lock()
        self.cond = threading.Condition(self.lock)

    def wait(self):
        with self.cond:
            geracao_atual = self.geracao
            self.contador += 1
            if self.contador == self.n:  # ultima a chegar libera todo mundo
                self.contador = 0
                self.geracao += 1
                self.cond.notify_all()
            else:
                while geracao_atual == self.geracao:
                    self.cond.wait()


def corredor(barreira, rodadas):
    for _ in range(rodadas):
        time.sleep(random.uniform(0.0005, 0.002))  # a perna da prova
        barreira.wait()


def rodar_equipe(k):
    barreira = Barreira(k)
    threads = [threading.Thread(target=corredor, args=(barreira, RODADAS)) for _ in range(k)]

    inicio = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)
    duracao = time.perf_counter() - inicio

    assert not any(t.is_alive() for t in threads), "equipe travou na barreira"
    return duracao


print("K | tempo(s) | rodadas/min")
for k in (2, 4, 8, 16):
    tempo = rodar_equipe(k)
    print(f"{k:2d} | {tempo:.2f} | {RODADAS / tempo * 60:.0f}")
