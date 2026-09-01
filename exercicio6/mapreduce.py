import threading
import random
import time
import os

ARQUIVO = "numeros.txt"
QTD = 3_000_000
MAX_VALOR = 100


def gerar_arquivo():
    if os.path.exists(ARQUIVO):
        return
    print(f"gerando {ARQUIVO}...")
    with open(ARQUIVO, "w") as f:
        for _ in range(QTD):
            f.write(f"{random.randrange(MAX_VALOR)}\n")


def ler_numeros():
    with open(ARQUIVO) as f:
        return [int(linha) for linha in f]


def bloco(numeros, p, i):
    tam = len(numeros) // p
    inicio = i * tam
    fim = len(numeros) if i == p - 1 else inicio + tam
    return numeros[inicio:fim]


def worker(parte, lock, total, hist):
    soma_local = 0
    hist_local = [0] * MAX_VALOR
    for n in parte:  # map: sem lock nenhum aqui
        soma_local += n
        hist_local[n] += 1

    with lock:  # reduce: um unico lock por thread
        total[0] += soma_local
        for i in range(MAX_VALOR):
            hist[i] += hist_local[i]


def rodar(numeros, p):
    lock = threading.Lock()
    total = [0]
    hist = [0] * MAX_VALOR

    threads = [threading.Thread(target=worker, args=(bloco(numeros, p, i), lock, total, hist))
               for i in range(p)]

    inicio = time.perf_counter()
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    duracao = time.perf_counter() - inicio

    return total[0], hist, duracao


def main():
    gerar_arquivo()
    numeros = ler_numeros()
    soma_certa = sum(numeros)

    base = None
    print(f"\n{len(numeros)} numeros lidos\n")
    print("P | tempo(s) | speedup")
    for p in (1, 2, 4, 8):
        soma, hist, tempo = rodar(numeros, p)
        assert soma == soma_certa, "soma errada"
        assert sum(hist) == len(numeros), "histograma perdeu numero"
        if base is None:
            base = tempo
        print(f"{p} | {tempo:.2f} | {base / tempo:.2f}x")

    print(f"\nsoma total: {soma_certa}")
    print("histograma (primeiros 10 valores):")
    for i in range(10):
        print(f"  {i}: {hist[i]}")


if __name__ == "__main__":
    main()
