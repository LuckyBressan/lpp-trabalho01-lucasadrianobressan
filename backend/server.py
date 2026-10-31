import socketio

from constantes import CUSTO_COLMEIA, INTERVALO_PRODUCAO, TEMPO_OBRA

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
    "fase": "aguardando",  # aguardando -> aberta -> encerrada
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
    return {"estado": dict(estado), "causa": causa, **extras}


@sio.event
async def connect(sid, environ, auth):
    auth = auth or {}
    jogadores[sid] = {
        "nome": auth.get("nome", "Anônimo"),
        "papel": auth.get("papel", "jogador"),
    }
    await sio.emit("estado.sincronizado", fato("conexao"), to=sid)


@sio.event
async def disconnect(sid):
    jogadores.pop(sid, None)


