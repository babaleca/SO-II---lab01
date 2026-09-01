import threading
import random
import time

N_ITENS = 50
CAP = 5

FIM = object()  # poison pill


class Fila:
    def __init__(self, capacidade):
        self.capacidade = capacidade
        self.itens = []
        self.lock = threading.Lock()
        self.tem_espaco = threading.Condition(self.lock)
        self.tem_item = threading.Condition(self.lock)

    def put(self, item):
        with self.tem_espaco:
            while len(self.itens) >= self.capacidade:
                self.tem_espaco.wait()
            self.itens.append(item)
            self.tem_item.notify()

    def get(self):
        with self.tem_item:
            while not self.itens:
                self.tem_item.wait()
            item = self.itens.pop(0)
            self.tem_espaco.notify()
            return item


def captura(saida):
    for i in range(N_ITENS):
        time.sleep(random.uniform(0.001, 0.004))
        saida.put((i, random.randint(1, 100)))
    saida.put(FIM)


def processamento(entrada, saida):
    while True:
        item = entrada.get()
        if item is FIM:
            saida.put(FIM)  # repassa pro proximo estagio
            return
        i, valor = item
        time.sleep(random.uniform(0.001, 0.005))
        saida.put((i, valor * valor))


def gravacao(entrada, resultado):
    while True:
        item = entrada.get()
        if item is FIM:
            return
        time.sleep(random.uniform(0.001, 0.003))
        resultado.append(item)


def main():
    f1 = Fila(CAP)
    f2 = Fila(CAP)
    resultado = []

    threads = [
        threading.Thread(target=captura, args=(f1,)),
        threading.Thread(target=processamento, args=(f1, f2)),
        threading.Thread(target=gravacao, args=(f2, resultado)),
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)  # se travar, o join volta e o is_alive acusa

    presas = [t for t in threads if t.is_alive()]

    print(f"itens gravados: {len(resultado)} de {N_ITENS}")
    print(f"threads presas: {len(presas)}")

    assert not presas, "deadlock: alguma thread nao terminou"
    assert sorted(i for i, _ in resultado) == list(range(N_ITENS)), "perdeu item"
    print("ok")


if __name__ == "__main__":
    main()
