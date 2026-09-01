import threading
import random

FINISH_LINE = 40
CAVALOS = ["Relampago", "Trovao", "Furacao", "Foguete", "Tornado", "Cometa"]


class Corrida:
    def __init__(self, cavalos, linha_chegada):
        self.cavalos = cavalos
        self.linha_chegada = linha_chegada
        self.posicoes = {c: 0 for c in cavalos}
        self.lock = threading.Lock()
        self.largada = threading.Barrier(len(cavalos))
        # a action roda uma vez por rodada, antes de soltar as threads.
        # isso evita que uma thread mais rapida comece a proxima rodada
        # enquanto outra ainda esta conferindo o resultado da atual
        # (tentei sem isso e travava - cada thread checando sozinha)
        self.rodada = threading.Barrier(len(cavalos), action=self.checa_fim)
        self.vencedor = None
        self.fim = threading.Event()

    def checa_fim(self):
        if self.fim.is_set():
            return
        cruzaram = [c for c, p in self.posicoes.items() if p >= self.linha_chegada]
        if cruzaram:
            # desempate: quem foi mais longe primeiro; empatando de
            # verdade, ordem alfabetica (nunca "quem chegou primeiro")
            cruzaram.sort(key=lambda c: (-self.posicoes[c], c))
            self.vencedor = cruzaram[0]
            self.fim.set()

    def correr(self, cavalo):
        self.largada.wait()
        while not self.fim.is_set():
            passo = random.randint(1, 5)
            with self.lock:
                self.posicoes[cavalo] += passo
            self.rodada.wait()

    def start(self):
        threads = [threading.Thread(target=self.correr, args=(c,)) for c in self.cavalos]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        return self.vencedor


def pedir_aposta(cavalos):
    print("Cavalos:", ", ".join(cavalos))
    while True:
        aposta = input("Em quem voce aposta? ").strip()
        for c in cavalos:
            if c.lower() == aposta.lower():
                return c
        print("nome invalido, tenta de novo")


def main():
    aposta = pedir_aposta(CAVALOS)
    corrida = Corrida(CAVALOS, FINISH_LINE)
    vencedor = corrida.start()

    print("\nPlacar final:")
    for c, p in sorted(corrida.posicoes.items(), key=lambda x: -x[1]):
        print(f"  {c}: {p}")

    print(f"\nVencedor: {vencedor}")
    if vencedor == aposta:
        print("acertou a aposta!")
    else:
        print(f"errou, apostou em {aposta}")


if __name__ == "__main__":
    main()
