import threading
import random
import time

N_RECURSOS = 4
N_THREADS = 6
T_WATCHDOG = 3       # segundos sem progresso pra suspeitar
OPERACOES = 300


class Estado:
    def __init__(self):
        self.progresso = 0
        self.segurando = {}   # thread -> lista de recursos
        self.esperando = {}   # thread -> recurso
        self.lock = threading.Lock()

    def marcar_espera(self, nome, recurso):
        with self.lock:
            self.esperando[nome] = recurso

    def marcar_posse(self, nome, recurso):
        with self.lock:
            self.esperando[nome] = None
            self.segurando.setdefault(nome, []).append(recurso)

    def soltar(self, nome):
        with self.lock:
            self.segurando[nome] = []
            self.progresso += 1


def trabalhar(recursos, estado, ordenar, parar):
    nome = threading.current_thread().name
    for _ in range(OPERACOES):
        if parar.is_set():
            return
        a, b = random.sample(range(N_RECURSOS), 2)
        if ordenar:
            a, b = min(a, b), max(a, b)  # ordem total: evita o ciclo de espera

        estado.marcar_espera(nome, a)
        recursos[a].acquire()
        estado.marcar_posse(nome, a)

        time.sleep(0.001)  # janela pra outra thread pegar o segundo recurso

        estado.marcar_espera(nome, b)
        recursos[b].acquire()
        estado.marcar_posse(nome, b)

        time.sleep(0.001)
        recursos[b].release()
        recursos[a].release()
        estado.soltar(nome)


def watchdog(estado, parar, achou):
    ultimo = -1
    parado_desde = time.perf_counter()
    while not parar.is_set():
        time.sleep(0.5)
        with estado.lock:
            atual = estado.progresso
        if atual != ultimo:
            ultimo = atual
            parado_desde = time.perf_counter()
            continue
        if time.perf_counter() - parado_desde >= T_WATCHDOG:
            print(f"\n[watchdog] sem progresso ha {T_WATCHDOG}s (progresso parado em {atual})")
            with estado.lock:
                for nome in sorted(estado.esperando):
                    esp = estado.esperando[nome]
                    seg = estado.segurando.get(nome, [])
                    if esp is not None:
                        print(f"  {nome}: segura {seg} e espera recurso {esp}")
            achou.set()
            return


def rodar(ordenar, titulo):
    print(f"\n=== {titulo} ===")
    recursos = [threading.Lock() for _ in range(N_RECURSOS)]
    estado = Estado()
    parar = threading.Event()
    achou = threading.Event()

    threads = [threading.Thread(target=trabalhar, args=(recursos, estado, ordenar, parar),
                                name=f"t{i}", daemon=True) for i in range(N_THREADS)]
    wd = threading.Thread(target=watchdog, args=(estado, parar, achou), daemon=True)

    for t in threads:
        t.start()
    wd.start()

    for t in threads:
        t.join(timeout=15)
    parar.set()
    wd.join(timeout=5)

    vivas = [t.name for t in threads if t.is_alive()]
    print(f"operacoes concluidas: {estado.progresso}")
    print(f"threads travadas: {vivas if vivas else 'nenhuma'}")
    print(f"watchdog acusou deadlock: {'sim' if achou.is_set() else 'nao'}")


rodar(ordenar=False, titulo="sem ordem de travamento")
rodar(ordenar=True, titulo="com ordem total de travamento")
