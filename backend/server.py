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
