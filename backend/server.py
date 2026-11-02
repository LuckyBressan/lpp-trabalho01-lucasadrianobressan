import socketio

from constantes import CUSTO_COLMEIA, INTERVALO_PRODUCAO, TEMPO_OBRA, LIMITE_APICULTOR, LIMITE_COLMEIA, MEL_POR_VENDA, MOEDA_POR_VENDA
from constantes import Fase, Papel

from pathlib import Path

# Pra facilitar minha vida eu monto uma variável de path client
CLIENT = Path(__file__).resolve().parent.parent / "client"

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
app = socketio.ASGIApp(
    sio,
    static_files={
        "/app.css": str(CLIENT / "app.css"),
        "/vila.js": str(CLIENT / "vila.js"),
        "/app.js": str(CLIENT / "app.js"),
        "/": str(CLIENT / "index.html"),
        "/assets": str(CLIENT / "assets"),  # mapa, tileset e sprites da vila
    },
)

estado = {
    "fase": Fase.AGUARDANDO,  # aguardando -> aberta -> encerrada
    "nectar": 150,
    "mel": 0,
    "moeda": 0,
    "apicultores": 0,  # ocupados agora
    "limite": LIMITE_APICULTOR,  # máximo de apicultores
    "limite_colmeia": LIMITE_COLMEIA, # limite baseado no espaço de resolução das colmeias no tilemap
    "producao": 10,  # nectar produzidos a cada INTERVALO
    "producao_mel": 0, # mel produzido a cada INTERVALO, depende da construção de colmeia
    "intervalo": INTERVALO_PRODUCAO, # em segundos
    "tempo_obra": TEMPO_OBRA,
    "custo": CUSTO_COLMEIA,
    "mel_por_venda": MEL_POR_VENDA,
    "moeda_por_venda": MOEDA_POR_VENDA,
    "concluidas": 0,
    "em_obra": 0,
}

jogadores = {}


def fato(causa, **extras):
    """Monta o payload de um FATO: o estado atual, a CAUSA (o evento ou o
     temporizador que gerou o fato) e dados extras."""
    return {"estado": dict(estado), "causa": causa, **extras}


@sio.event
async def connect(sid, environ, auth):
    auth = auth or {}
    jogadores[sid] = {
        "nome": auth.get("nome", "Anônimo"),
        "papel": auth.get("papel", Papel.JOGADOR),
    }
    # FATO só para quem acabou de conectar (to=sid): os outros jogadores já têm o
    # estado, então só o recém-chegado precisa receber a "foto" atual do apiário
    await sio.emit("estado.sincronizado", fato("conexao"), to=sid)


@sio.event
async def disconnect(sid):
    jogadores.pop(sid, None)

async def recusar(sid, motivo, causa):
    """Responde só a quem pediu."""
    # A recusa também é um evento, mas vai só para quem fez o pedido (to=sid):
    # para os outros jogadores nada mudou, então não há o que avisar
    await sio.emit(
        "operacao.recusada",
        { "motivo": motivo, "causa": causa },
        to=sid
    )

# ESCUTA o PEDIDO do Mestre para abrir a temporada. O servidor é quem decide:
# confere o papel e a fase antes de mudar qualquer coisa
@sio.on("apiario.abertura_solicitada")
async def abrir_apiario(sid, dados=None):
    pedido = "apiario.abertura_solicitada"
    if jogadores[sid]["papel"] != Papel.MESTRE:
        await recusar(sid, "Só o Mestre pode abrir a temporada", pedido)
        return
    if estado["fase"] != Fase.AGUARDANDO:
        await recusar(sid, "A temporada já foi aberta", pedido)
        return
    estado["fase"] = Fase.ABERTA
    # a partir daqui o temporizador de coleta passa a ser uma fonte de eventos
    sio.start_background_task(producao)
    # FATO para todos: todos os jogadores precisam ver a temporada aberta ao mesmo tempo
    await sio.emit("apiario.iniciado", fato(pedido))


# ESCUTA o PEDIDO de um Jogador para construir uma colmeia
@sio.on("colmeia.solicitada")
async def construir(sid, dados=None):
    pedido = "colmeia.solicitada"

    # Valide TUDO antes de alterar o estado e sem await no meio:
    # assim, dois pedidos simultâneos são decididos um de cada vez.
    if estado["fase"] != Fase.ABERTA:
        motivo = "A temporada não está aberta"
    elif estado["nectar"] < CUSTO_COLMEIA:
        motivo = "Néctar insuficiente"
    elif estado["apicultores"] >= estado["limite"]:
        motivo = "Sem apicultor livre"
    elif estado["concluidas"] + estado["em_obra"] >= estado["limite_colmeia"]:
        motivo = "Limite máximo de colmeias atingido"
    else:
        motivo = None

    if motivo:
        await recusar(sid, motivo, pedido) # só quem pediu recebe
        return

    estado["nectar"] -= CUSTO_COLMEIA
    estado["apicultores"] += 1
    estado["em_obra"] += 1
    nome = jogadores[sid]["nome"]
    # FATO para todos: o néctar e os apicultores são compartilhados, então todas
    # as abas precisam atualizar o estoque e mostrar a colmeia em montagem
    await sio.emit("colmeia.iniciada", fato(pedido, por=nome))
    # a obra termina sozinha: um temporizador vai emitir colmeia.concluida depois
    sio.start_background_task(obra, nome)

# ESCUTA o PEDIDO de venda de mel no mercado (evento próprio do apiário)
@sio.on("mel.venda_solicitada")
async def venda_solicitada(sid, dados=None):
    pedido = "mel.venda_solicitada"

    if estado["fase"] != Fase.ABERTA:
        motivo = "A temporada não está aberta"
    elif estado["mel"] < MEL_POR_VENDA: # vendemos mel por lote
        motivo = "Não há mel o suficiente para venda"
    else:
        motivo = None

    if motivo:
        await recusar(sid, motivo, pedido) # só quem pediu recebe
        return

    estado["mel"] -= MEL_POR_VENDA
    estado["moeda"] += MOEDA_POR_VENDA

    # FATO para todos: o mel e as moedas são do apiário inteiro, então todos
    # precisam ver o estoque de mel cair e as moedas subirem
    await sio.emit("mel.vendido", fato(pedido, por=jogadores[sid]["nome"]))



# TEMPORIZADOR como fonte de eventos: ninguém clica, o servidor coleta sozinho
# a cada INTERVALO_PRODUCAO e avisa todos. O cliente nunca pergunta "já produziu?"
async def producao():
    while estado["fase"] == Fase.ABERTA:
        await sio.sleep(INTERVALO_PRODUCAO)
        if estado["fase"] != Fase.ABERTA:
            break
        estado["nectar"] += estado["producao"]
        estado["mel"] += estado["producao_mel"]
        # FATO para todos, com causa "temporizador" (não veio de nenhum pedido)
        await sio.emit("recurso.produzido", fato("temporizador"))


# TEMPORIZADOR da obra: começa quando a colmeia é iniciada e termina sozinho
async def obra(nome):
    await sio.sleep(TEMPO_OBRA)
    if estado["fase"] != Fase.ABERTA:
        return
    estado["apicultores"] -= 1
    estado["em_obra"] -= 1
    estado["concluidas"] += 1
    estado["producao"] += 5 # cada obra concluída aumenta a produção
    estado["producao_mel"] += 2 # a partir da primeira colmeia, mel começa a ser produzido (cada colmeia refina 2 mel)
    causa = "colmeia.iniciada (temporizador)"
    # FATO para todos: o apicultor fica livre e a produção sobe para o apiário inteiro
    await sio.emit("colmeia.concluida", fato(causa, por=nome))


# ESCUTA o PEDIDO do Mestre para encerrar a temporada
@sio.on("apiario.encerramento_solicitado")
async def encerrar_vila(sid, dados=None):
    pedido = "apiario.encerramento_solicitado"
    if jogadores[sid]["papel"] != Papel.MESTRE:
        await recusar(sid, "Só o Mestre pode encerrar a temporada", pedido)
        return
    if estado["fase"] != Fase.ABERTA:
        await recusar(sid, "A temporada não está aberta", pedido)
        return
    estado["fase"] = Fase.ENCERRADA  # o laço de producao() para na próxima volta
    # FATO para todos: todos param de produzir e passam a ter os pedidos recusados
    await sio.emit("apiario.encerrado", fato(pedido))