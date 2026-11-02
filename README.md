# Vila em Tempo Real — Apiário e Mercado 🐝🍯

Jogo cooperativo em tempo real: o Mestre abre a temporada, os Jogadores constroem colmeias, o apiário coleta néctar sozinho, as colmeias prontas refinam mel e o mel é vendido no mercado em troca de moedas. Tudo acontece por **eventos**: o cliente só pede, o servidor decide e avisa todo mundo.

## Integrantes

* Lucas Adriano dos Santos Bressan — @LuckyBressan

## Tecnologias

* **Servidor:** Python 3.11+ (usa `enum.StrEnum`), python-socketio e uvicorn
* **Comunicação:** Socket.IO
* **Tela:** Vue 3 e Phaser 3, carregados por CDN (nada para instalar)

## Estrutura

```
backend/
  server.py         # estado do apiário, handlers dos pedidos e temporizadores
  constantes.py     # regras (custos, tempos, limites) e enums de fase e papel
  requirements.txt
client/
  index.html        # tela (template do Vue)
  app.js            # aplicação: ESCUTAS (ouvir) e PEDIDOS (pedir)
  vila.js           # cena do Phaser (o apiário desenhado)
  app.css
  assets/           # mapa, tileset e sprites (ver assets/LEIA-ME.txt)
docs/
  especificacao.md  # regras, eventos e cenários (escrita antes do código)
```

## Como instalar e executar

Na pasta raiz do repositório:

```
python -m venv .venv
.venv\Scripts\activate            # Windows
source .venv/bin/activate         # Linux ou macOS
pip install -r backend/requirements.txt
cd backend
uvicorn server:app --reload
```

Abra **<http://localhost:8000>** no navegador (não abra o arquivo direto com `file://`).

> O estado fica na memória do servidor. Ao reiniciar o uvicorn, o apiário volta ao começo: recarregue as abas e entre de novo.

## Como testar com duas abas

1. **Aba 1:** digite um nome e clique em **Entrar como Mestre**. **Aba 2:** entre como **Jogador**. As duas mostram 150 de néctar e a faixa "Aguardando o Mestre".
2. **Recusa antes de abrir:** na aba do Jogador, clique em **Construir**. Só essa aba recebe o aviso vermelho "A temporada não está aberta" e a tela treme.
3. **Abrir:** no Mestre, clique em **Abrir temporada**. As duas abas mudam para "aberta" sem recarregar. O painel do Mestre mostra `⬆ emit apiario.abertura_solicitada` e depois `⬇ on apiario.iniciado`. O do Jogador mostra só o `⬇ on`.
4. **Construir:** o Jogador clica em **Construir**. O néctar cai 50, os apicultores vão para 1/2 e aparece a colmeia em montagem, nas duas abas.
5. **Passagem do tempo:** sem ninguém clicar, o néctar sobe a cada 5 s (`recurso.produzido`, causa: temporizador). Depois de 8 s a colmeia fica pronta (`colmeia.concluida`), e a partir daí o mel também sobe +2 por colmeia a cada coleta.
6. **Mercado:** com menos de 10 de mel, **Vender mel** é recusado só para quem pediu. Com 10 ou mais, `mel.vendido` chega para todos: −10 mel e +30 moedas.
7. **Disputa (3 abas):** Mestre, Jogador A e Jogador B. Com 1/2 apicultores ocupados, A e B clicam em **Construir** quase juntos. Só um recebe `colmeia.iniciada`. O outro recebe "Sem apicultor livre", e o limite nunca passa de 2/2.
8. **Limite de colmeias:** o apiário comporta 6 colmeias (prontas + em montagem). Ao pedir a sétima, só quem pediu recebe "Limite máximo de colmeias atingido".
9. **Encerrar:** o Mestre clica em **Encerrar temporada**. O apiário escurece, a produção para e qualquer pedido novo é recusado.

## Perguntas

> Respostas escritas a partir do código. Revise com suas palavras antes de entregar.

**1. Quais eventos o seu sistema emite e escuta?**

| Evento                            | Emite                              | Escuta   | Tipo          |
| --------------------------------- | ---------------------------------- | -------- | ------------- |
| `estado.sincronizado`             | servidor (só para quem conectou)   | cliente  | fato          |
| `apiario.abertura_solicitada`     | cliente (Mestre)                   | servidor | pedido        |
| `apiario.iniciado`                | servidor (todos)                   | cliente  | fato          |
| `colmeia.solicitada`              | cliente (Jogador)                  | servidor | pedido        |
| `colmeia.iniciada`                | servidor (todos)                   | cliente  | fato          |
| `operacao.recusada`               | servidor (só quem pediu)           | cliente  | fato (recusa) |
| `recurso.produzido`               | servidor (todos), por temporizador | cliente  | fato          |
| `colmeia.concluida`               | servidor (todos), por temporizador | cliente  | fato          |
| `mel.venda_solicitada`            | cliente (Jogador)                  | servidor | pedido        |
| `mel.vendido`                     | servidor (todos)                   | cliente  | fato          |
| `apiario.encerramento_solicitado` | cliente (Mestre)                   | servidor | pedido        |
| `apiario.encerrado`               | servidor (todos)                   | cliente  | fato          |

O servidor também escuta os eventos de sistema `connect` e `disconnect` do Socket.IO.

Essas mesmas descrições você pode acompanhar no arquivo de `especificacoes.md` que redigi e fiz commit na "etapa 0"

**2. Como o sistema sabe quando deve atualizar os outros jogadores?**

O cliente nunca muda o estado por conta própria e nunca pergunta ao servidor se algo mudou. Toda mudança acontece no servidor, dentro de um handler de pedido ou de um temporizador. Logo depois de alterar o estado, o servidor emite um fato com `sio.emit(...)` **sem** **`to=`**, e esse fato chega a todos os clientes conectados. Cada cliente escuta esse fato com `ouvir(...)` e redesenha a tela com o estado que veio junto. Quando só uma pessoa precisa saber, o servidor usa `to=sid`: é o caso da recusa (`operacao.recusada`) e do estado inicial (`estado.sincronizado`).

Como a ideia era simular um jogo e num jogo tudo é "atualizado para todos", optei em todos os eventos atualizar para todos os jogadores, menos esse de `operacao.recusada` e `estado.sincronizado` (em um jogo real isto seria chamado de evento client-side, ou outro nome)

**3. Que parte do código mostra claramente o uso do paradigma orientado a eventos?**

* `backend/server.py`, nos handlers `@sio.on("colmeia.solicitada")` e `@sio.on("mel.venda_solicitada")`: eles **escutam o pedido**, **validam tudo sem** **`await`** **no meio** (por isso a disputa tem um vencedor só), **alteram o estado** e **emitem o fato** para todos, ou a recusa só para quem pediu.
* `backend/server.py`, nas funções `producao()` e `obra()`: temporizadores como **fonte de eventos**, que emitem `recurso.produzido` e `colmeia.concluida` sem nenhum clique.
* `client/app.js`, nas funções `ouvir(...)` e `pedir(...)` e na região ESCUTAS: o cliente registra reações aos fatos e só pede. O Painel de eventos mostra cada emit e on com causa e reação.

## Uso de IA

Usei o Claude (Anthropic) como apoio:

* para revisar a especificação e o código ao fim de cada etapa (por exemplo, corrigir ortograficamente algo ou falta de informação);
* para gerar a arte do apiário: as novas peças do tileset, os sprites da colmeia e o mapa com o mercado (ver `client/assets/LEIA-ME.txt`), como achei meu tema relativamente específico, achei mais fácil solicitar geração, evitando inclusive problemas com direitos autorais;
* para redigir partes deste README a partir do código;
* para os ajustes finais da revisão: comentários nos pontos de emissão e escuta, uso dos enums `Fase`/`Papel` em todo o servidor (busy work).

O código do servidor e do cliente foi escrito por mim, seguindo o Guia de Implementação e adaptando ao apiário, afinal o código era muito simples... pretendo melhorar outras coisas conforme a seção "melhorias futuras".

## Extras

* **Mercado:** evento próprio `mel.venda_solicitada` → `mel.vendido` (−10 mel, +30 moedas), com recusa quando falta mel.
* **Recurso refinado:** cada colmeia pronta passa a gerar +2 de mel por coleta.
* **Limite de colmeias:** no máximo 6 colmeias no apiário, com recusa própria. Fiz isso, pois na tela do jogo só cabem 6 colmeias mesmo
* **Contadores por evento** no Painel de eventos, era obrigatório só para duplas, mas o guia já tinha a estrutura pré-pronta, só tive o trabalho de listar em tela.
* **Mapa e sprites personalizados:** campo de flores, lagoa, colmeias e mercado com duas bancas.
* **Organização:** servidor em `backend/`, regras em `constantes.py` com enums (`Fase`, `Papel`) e cliente separado em `index.html`, `app.js`, `vila.js` e `app.css`.

## Melhorias futuras

* Reescrever o cliente com TypeScript + Vue + Vite (componentes `.vue`, tipagem dos eventos e build), no lugar dos scripts carregados por CDN.

