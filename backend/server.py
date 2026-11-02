import socketio

from constantes import CUSTO_COLMEIA, INTERVALO_PRODUCAO, TEMPO_OBRA, Fase, Papel

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
    "toras": 150,
    "trabalhadores": 0,  # ocupados agora
    "limite": 2,  # máximo de apicultores
    "producao": 10,  # nectar produzidos a cada INTERVALO
    "intervalo": INTERVALO_PRODUCAO,
    "tempo_obra": TEMPO_OBRA,
    "custo": CUSTO_COLMEIA,
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

@sio.on("vila.abertura_solicitada")
async def abrir_vila(sid, dados=None):
    pedido = "vila.abertura_solicitada"
    if jogadores[sid]["papel"] != Papel.MESTRE:
        await recusar(sid, "Só o Mestre pode abrir a temporada", pedido)
        return
    if estado["fase"] != Fase.AGUARDANDO:
        await recusar(sid, "A temporada já foi aberta", pedido)
        return
    estado["fase"] = Fase.ABERTA
    await sio.emit("vila.iniciada", fato(pedido))   # para todos


@sio.on("construcao.solicitada")
async def construir(sid, dados=None):
    pedido = "construcao.solicitada"
    # Valide TUDO antes de alterar o estado e sem await no meio:
    # assim, dois pedidos simultâneos são decididos um de cada vez.
    if estado["fase"] != "aberta":
        motivo = "A temporada não está aberta"
    elif estado["toras"] < CUSTO_COLMEIA:
        motivo = "Toras insuficientes"
    elif estado["trabalhadores"] >= estado["limite"]:
        motivo = "Sem trabalhador livre"
    else:
        motivo = None
    if motivo:
        await recusar(sid, motivo, pedido) # só quem pediu recebe
        return
    estado["toras"] -= CUSTO_COLMEIA
    estado["trabalhadores"] += 1
    estado["em_obra"] += 1
    nome = jogadores[sid]["nome"]
    await sio.emit("construcao.iniciada", fato(pedido, por=nome))



