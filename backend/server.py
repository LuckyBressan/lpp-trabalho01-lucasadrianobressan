import socketio

from constantes import CUSTO_COLMEIA, INTERVALO_PRODUCAO, TEMPO_OBRA, LIMITE_APICULTORES, MEL_POR_VENDA, MOEDA_POR_VENDA
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

# @todo depois será trocado as chaves para corresponder ao meu tipo de vila
estado = {
    "fase": Fase.AGUARDANDO,  # aguardando -> aberta -> encerrada
    "nectar": 150,
    "mel": 0,
    "moeda": 0,
    "apicultores": 0,  # ocupados agora
    "limite": LIMITE_APICULTORES,  # máximo de apicultores
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
    # servidor -> UM cliente: entrega o estado atual
    await sio.emit("estado.sincronizado", fato("conexao"), to=sid)


@sio.event
async def disconnect(sid):
    jogadores.pop(sid, None)

async def recusar(sid, motivo, causa):
    """Responde só a quem pediu."""
    await sio.emit(
        "operacao.recusada",
        { "motivo": motivo, "causa": causa },
        to=sid
    )

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
    sio.start_background_task(producao)
    await sio.emit("apiario.iniciado", fato(pedido))   # para todos


@sio.on("colmeia.solicitada")
async def construir(sid, dados=None):
    pedido = "colmeia.solicitada"

    # Valide TUDO antes de alterar o estado e sem await no meio:
    # assim, dois pedidos simultâneos são decididos um de cada vez.
    if estado["fase"] != "aberta":
        motivo = "A temporada não está aberta"
    elif estado["nectar"] < CUSTO_COLMEIA:
        motivo = "Nectar insuficiente"
    elif estado["apicultores"] >= estado["limite"]:
        motivo = "Sem apicultor livre"
    else:
        motivo = None

    if motivo:
        await recusar(sid, motivo, pedido) # só quem pediu recebe
        return
    estado["nectar"] -= CUSTO_COLMEIA
    estado["apicultores"] += 1
    estado["em_obra"] += 1
    nome = jogadores[sid]["nome"]
    await sio.emit("colmeia.iniciada", fato(pedido, por=nome))
    sio.start_background_task(obra, nome)

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

    await sio.emit("mel.vendido", fato(pedido, por=jogadores[sid]["nome"]))



async def producao():
    while estado["fase"] == "aberta":
        await sio.sleep(INTERVALO_PRODUCAO)
        if estado["fase"] != "aberta":
            break
        estado["nectar"] += estado["producao"]
        estado["mel"] += estado["producao_mel"]
        await sio.emit("recurso.produzido", fato("temporizador"))


async def obra(nome):
    await sio.sleep(TEMPO_OBRA)
    if estado["fase"] != "aberta":
        return
    estado["apicultores"] -= 1
    estado["em_obra"] -= 1
    estado["concluidas"] += 1
    estado["producao"] += 5 # cada obra concluída aumenta a produção
    estado["producao_mel"] += 2 # a partir da primeira colmeia, mel começa a ser produzido (cada colmeia refina 2 mel)
    causa = "colmeia.iniciada (temporizador)"
    await sio.emit("colmeia.concluida", fato(causa, por=nome))


@sio.on("apiario.encerramento_solicitado")
async def encerrar_vila(sid, dados=None):
    pedido = "apiario.encerramento_solicitado"
    if jogadores[sid]["papel"] != "mestre":
        await recusar(sid, "Só o Mestre pode encerrar a temporada", pedido)
        return
    if estado["fase"] != "aberta":
        await recusar(sid, "A temporada não está aberta", pedido)
        return
    estado["fase"] = "encerrada"
    await sio.emit("apiario.encerrado", fato(pedido))