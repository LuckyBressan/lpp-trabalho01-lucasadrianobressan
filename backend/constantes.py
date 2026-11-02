from enum import StrEnum

MEL_POR_VENDA = 10
MOEDA_POR_VENDA = 30
CUSTO_COLMEIA = 50
TEMPO_OBRA = 8
INTERVALO_PRODUCAO = 5
LIMITE_APICULTOR = 2
LIMITE_COLMEIA = 6


class Fase(StrEnum):
    AGUARDANDO = "aguardando"
    ABERTA = "aberta"
    ENCERRADA = "encerrada"

class Papel(StrEnum):
    MESTRE = "mestre"
    JOGADOR = "jogador"