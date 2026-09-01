import threading
import random
import time

CAP = 10
N_PRODUTORES = 3
N_CONSUMIDORES = 2
ITENS_POR_PRODUTOR = 400

FIM = object()


class Buffer:
    def __init__(self, capacidade):
        self.capacidade = capacidade
        self.itens = []
        self.lock = threading.Lock()
        self.tem_espaco = threading.Condition(self.lock)
        self.tem_item = threading.Condition(self.lock)
        self.tempo_bloqueado = 0.0  # quanto os produtores esperaram no total
        self.vezes_bloqueado = 0

    def put(self, item):
        with self.tem_espaco:
            inicio = time.perf_counter()
            bloqueou = False
            while len(self.itens) >= self.capacidade:
                bloqueou = True
                self.tem_espaco.wait()
            if bloqueou:  # backpressure: produtor segurou porque estava cheio
                self.tempo_bloqueado += time.perf_counter() - inicio
                self.vezes_bloqueado += 1
            self.itens.append(item)
            self.tem_item.notify()

    def get(self):
        with self.tem_item:
            while not self.itens:
                self.tem_item.wait()
            item = self.itens.pop(0)
            self.tem_espaco.notify()
            return item

    def ocupacao(self):
        with self.lock:
            return len(self.itens)


def produtor(buf):
    restantes = ITENS_POR_PRODUTOR
    while restantes > 0:
        rajada = min(random.randint(15, 30), restantes)  # rajada
        for _ in range(rajada):
            buf.put(random.randint(1, 100))
            time.sleep(0.001)
        restantes -= rajada
        time.sleep(random.uniform(0.2, 0.4))  # ociosidade


def consumidor(buf, inicio_geral):
    while True:
        item = buf.get()
        if item is FIM:
            return
        # consumidor fica lento no meio da execucao
        if 3 < time.perf_counter() - inicio_geral < 9:
            time.sleep(0.02)
        else:
            time.sleep(0.004)


def monitor(buf, parar, amostras, inicio_geral):
    while not parar.is_set():
        amostras.append((time.perf_counter() - inicio_geral, buf.ocupacao()))
        time.sleep(0.1)


def barra(valor, maximo):
    return "#" * int(valor / maximo * 30)


def main():
    buf = Buffer(CAP)
    amostras = []
    parar = threading.Event()
    inicio = time.perf_counter()

    prods = [threading.Thread(target=produtor, args=(buf,)) for _ in range(N_PRODUTORES)]
    cons = [threading.Thread(target=consumidor, args=(buf, inicio)) for _ in range(N_CONSUMIDORES)]
    mon = threading.Thread(target=monitor, args=(buf, parar, amostras, inicio))

    for t in prods + cons:
        t.start()
    mon.start()

    for t in prods:
        t.join()
    for _ in cons:
        buf.put(FIM)
    for t in cons:
        t.join()
    parar.set()
    mon.join()

    print("ocupacao do buffer ao longo do tempo (cap = %d)\n" % CAP)
    for t, oc in amostras[::2]:  # uma amostra a cada 200ms
        print(f"{t:5.1f}s |{barra(oc, CAP):<30}| {oc}")

    print(f"\nvezes que um produtor bloqueou: {buf.vezes_bloqueado}")
    print(f"tempo total bloqueado: {buf.tempo_bloqueado:.2f}s")
    print(f"ocupacao media: {sum(o for _, o in amostras) / len(amostras):.1f}")


if __name__ == "__main__":
    main()
