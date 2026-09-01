import threading
import sys

N_WORKERS = 4

FIM = object()  # poison pill


class FilaTarefas:
    def __init__(self):
        self.itens = []
        self.lock = threading.Lock()
        self.tem_item = threading.Condition(self.lock)
        self.enfileiradas = 0

    def put(self, tarefa):
        with self.tem_item:
            self.itens.append(tarefa)
            if tarefa is not FIM:
                self.enfileiradas += 1
            self.tem_item.notify()

    def get(self):
        with self.tem_item:
            while not self.itens:
                self.tem_item.wait()
            return self.itens.pop(0)


def eh_primo(n):
    if n < 2:
        return False
    i = 2
    while i * i <= n:
        if n % i == 0:
            return False
        i += 1
    return True


def worker(fila, resultados, lock):
    while True:
        tarefa = fila.get()
        if tarefa is FIM:
            return
        resposta = eh_primo(tarefa)
        with lock:  # append de varias threads sem lock da corrida
            resultados.append((tarefa, resposta))


def main():
    fila = FilaTarefas()
    resultados = []
    lock = threading.Lock()

    threads = [threading.Thread(target=worker, args=(fila, resultados, lock))
               for _ in range(N_WORKERS)]
    for t in threads:
        t.start()

    print(f"pool com {N_WORKERS} threads. digite numeros (Ctrl+D pra encerrar)")
    for linha in sys.stdin:
        linha = linha.strip()
        if not linha:
            continue
        try:
            fila.put(int(linha))
        except ValueError:
            print(f"ignorado: {linha}")

    for _ in threads:  # uma pill por worker
        fila.put(FIM)
    for t in threads:
        t.join()

    print(f"\ntarefas enviadas: {fila.enfileiradas} | resultados: {len(resultados)}")
    assert len(resultados) == fila.enfileiradas, "perdeu ou duplicou tarefa"

    for n, primo in sorted(resultados):
        print(f"{n}: {'primo' if primo else 'nao primo'}")


if __name__ == "__main__":
    main()
