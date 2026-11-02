from enum import StrEnum

CUSTO_COLMEIA = 50
TEMPO_OBRA = 8
INTERVALO_PRODUCAO = 5
LIMITE_APICULTORES = 2


class Fase(StrEnum):
    AGUARDANDO = "aguardando"
    ABERTA = "aberta"
    ENCERRADA = "encerrada"

class Papel(StrEnum):
    MESTRE = "mestre"
    JOGADOR = "jogador"