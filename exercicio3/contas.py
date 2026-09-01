import threading
import random
import time

N_CONTAS = 20
N_THREADS = 8
TRANSFERENCIAS = 2000
SALDO_INICIAL = 1000


def contas_iniciais():
    return [SALDO_INICIAL] * N_CONTAS


def par_aleatorio(n):
    i = random.randrange(n)
    j = random.randrange(n)
    while j == i:
        j = random.randrange(n)
    return i, j


def transferir_seguro(contas, locks, i, j, valor):
    # trava sempre a conta de indice menor primeiro. se nao fizer isso,
    # duas threads transferindo em sentidos opostos (A->B e B->A) podem
    # travar uma conta cada e ficar esperando a outra pra sempre -> deadlock
    a, b = (i, j) if i < j else (j, i)
    with locks[a]:
        with locks[b]:
            contas[i] -= valor
            contas[j] += valor


def transferir_sem_trava(contas, i, j, valor):
    saldo_i = contas[i]
    saldo_j = contas[j]
    time.sleep(0)  # da tempo de outra thread mexer nas mesmas contas no meio
    contas[i] = saldo_i - valor
    contas[j] = saldo_j + valor


def worker_seguro(contas, locks):
    for _ in range(TRANSFERENCIAS):
        i, j = par_aleatorio(len(contas))
        valor = random.randint(1, 50)
        transferir_seguro(contas, locks, i, j, valor)


def worker_sem_trava(contas):
    for _ in range(TRANSFERENCIAS):
        i, j = par_aleatorio(len(contas))
        valor = random.randint(1, 50)
        transferir_sem_trava(contas, i, j, valor)


def rodar_seguro():
    contas = contas_iniciais()
    locks = [threading.Lock() for _ in contas]
    total_antes = sum(contas)

    threads = [threading.Thread(target=worker_seguro, args=(contas, locks)) for _ in range(N_THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    total_depois = sum(contas)
    assert total_depois == total_antes, "saldo total mudou, tem bug na sincronizacao"
    return total_antes, total_depois


def rodar_sem_trava():
    contas = contas_iniciais()
    total_antes = sum(contas)

    threads = [threading.Thread(target=worker_sem_trava, args=(contas,)) for _ in range(N_THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    return total_antes, sum(contas)


if __name__ == "__main__":
    antes, depois = rodar_seguro()
    print(f"com trava:  antes={antes} depois={depois} diff={depois - antes}")

    antes, depois = rodar_sem_trava()
    print(f"sem trava:  antes={antes} depois={depois} diff={depois - antes}")
