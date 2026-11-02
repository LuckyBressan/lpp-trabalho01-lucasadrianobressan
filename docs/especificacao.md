# Especificação — Vila em Tempo Real

**Integrante:** Lucas Adriano dos Santos Bressan
**Tipo de vila (sorteio):** Apiário e Mercado

## 1. Regras da vila

* Recurso primário e recurso refinado: néctar e mel
* Custo de uma construção: 50 néctar
* Tempo da obra: 8 segundos
* Limite de trabalhadores: 2 apicultores
* Limite de colmeias: 6 no apiário (somando as prontas e as em montagem); acima disso o pedido é recusado
* Intervalo e quantidade da produção automática: + 10 néctar a cada 5 s, com 1 colmeia são +15 néctar e + 2 mel a cada 5s
* O que muda quando uma obra termina: libera o apicultor, + 5 néctar por coleta e cada colmeia gera +2 mel por coleta
* Qual o evento do mercado: O jogador vende 10 mel e a vila ganha 30 moedas; Se não tiver mel o suficiente, é recusado a venda

## 2. Eventos

| Evento                            | Emite    | Recebe         | O que muda no estado                                        |
| --------------------------------- | -------- | -------------- | ----------------------------------------------------------- |
| `estado.sincronizado`             | Servidor | Só quem entrou | nada; entrega o estado atual (sincroniza)                   |
| `apiario.abertura_solicitada`     | Mestre   | Servidor       | é um pedido; nada muda                                      |
| `apiario.iniciado`                | Servidor | Todos          | fase passa para "aberta" e a coleta começa                  |
| `colmeia.solicitada`              | Jogador  | Servidor       | é um pedido; nada muda                                      |
| `colmeia.iniciada`                | Servidor | Todos          | −50 néctar, +1 apicultor ocupado, +1 colmeia em montagem    |
| `operacao.recusada`               | Servidor | Só quem pediu  | nada muda; informa o motivo                                 |
| `recurso.produzido`               | Servidor | Todos          | +néctar e +mel (das colmeias prontas)                       |
| `colmeia.concluida`               | Servidor | Todos          | −1 apicultor ocupado, +1 colmeia pronta, coleta aumenta     |
| `mel.venda_solicitada`            | Jogador  | Servidor       | é um pedido; nada muda                                      |
| `mel.vendido`                     | Servidor | Todos          | −10 mel, +30 moedas                                         |
| `apiario.encerramento_solicitado` | Mestre   | Servidor       | é um pedido; nada muda                                      |
| `apiario.encerrado`               | Servidor | Todos          | fase "encerrada"; coleta para e novos pedidos são recusados |

## 3. Cenários de teste (Dado / Quando / Então, escritos com eventos)

### Recusa

Dado que o apiário tem 5 de mel, quando um Jogador emite `mel.venda_solicitada`, então o servidor emite `operacao.recusada` apenas para ele, com o motivo de que são necessários 10 de mel para a venda; o estoque de mel e as moedas não mudam e o mel continua sendo refinado normalmente

### Passagem do tempo

Dado que a temporada está aberta (`apiario.iniciado`) e há 1 colmeia pronta, quando passam 5 segundos, então é coletado e produzido automaticamente +15 néctar e + 2 mel (`recurso.produzido`) e o servidor avisa todos os jogadores, sem ninguém clicar

### Disputa entre dois jogadores

Dado que há apenas 1 apicultor livre, quando dois jogadores A e B solicitam ao mesmo tempo 1 construção (`colmeia.solicitada`), então o solicitante que chegou primeiro recebe a resposta positiva (`colmeia.iniciada`) e o outro a recusa (`operacao.recusada`) com o motivo "sem apicultor livre"
