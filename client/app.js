const { createApp, ref, reactive, computed, nextTick } = Vue;

createApp({
  setup() {
    const nome = ref("");
    const papel = ref("");
    const conectado = ref(false);
    const estado = reactive({
      fase: "aguardando",
      toras: 0,
      trabalhadores: 0,
      limite: 0,
      producao: 0,
      intervalo: 0,
      tempo_obra: 0,
      custo: 0,
      concluidas: 0,
      em_obra: 0,
    });
    const avisos = ref([]);
    const eventos = ref([]); // linha do tempo do painel de eventos
    const contadores = reactive({}); // quantas vezes cada evento ocorreu
    const ocultarProducao = ref(false);
    const eventosVisiveis = computed(() =>
      eventos.value.filter(
        (e) => !(ocultarProducao.value && e.nome === "recurso.produzido"),
      ),
    );
    const jogo = criarJogo(); // a vila desenhada (Phaser)
    let socket = null;

    const porMinuto = computed(() =>
      estado.intervalo
        ? Math.round((estado.producao * 60) / estado.intervalo)
        : 0,
    );

    function avisar(texto, tipo = "info") {
      avisos.value.unshift({ texto, tipo });
      avisos.value = avisos.value.slice(0, 6);
    }

    function atualizar(d) {
      Object.assign(estado, d.estado); // copia o estado enviado pelo servidor
    }

    // ----- painel de eventos (já pronto) -----
    function resumir(d) {
      // transforma os dados do evento em texto curto
      if (!d) return "";
      const { estado: e, causa, ...resto } = d;
      const partes = Object.entries(resto).map(([k, v]) => k + ": " + v);
      if (e)
        partes.push(
          "toras " +
            e.toras +
            ", trabalhadores " +
            e.trabalhadores +
            "/" +
            e.limite,
        );
      return partes.join(" · ");
    }
    function registrar(sentido, nome, dados, reacao = "") {
      const tipo = /_solicitad[ao]$/.test(nome)
        ? "pedido"
        : nome === "operacao.recusada"
          ? "recusa"
          : "fato";
      contadores[nome] = (contadores[nome] || 0) + 1;
      eventos.value.unshift({
        hora: new Date().toLocaleTimeString(),
        sentido: sentido,
        nome,
        tipo,
        causa: (dados && dados.causa) || "",
        dados: resumir(dados),
        reacao,
      });
      eventos.value = eventos.value.slice(0, 40);
    }

    // OUVIR (on): registra o evento no painel e executa a reação do cliente
    function ouvir(nome, reacao, funcao) {
      socket.on(nome, (d) => {
        registrar("recebido", nome, d, reacao);
        funcao(d);
      });
    }
    // PEDIR (emit): registra o evento no painel e o envia ao servidor
    function pedir(nome, dados) {
      registrar("enviado", nome, dados);
      if (dados === undefined) socket.emit(nome);
      else socket.emit(nome, dados);
    }

    function entrar(p) {
      papel.value = p;
      socket = io({ auth: { nome: nome.value || "Anônimo", papel: p } });
      socket.on("connect", () => {
        conectado.value = true;
        nextTick(() => jogo.iniciar("jogo")); // a vila desenhada começa quando a tela aparece
      });

      ouvir("estado.sincronizado", "guarda o estado e desenha a vila", (d) => {
        atualizar(d);
        jogo.mostrarEstado(d.estado);
      });

      ouvir("vila.iniciada", "muda a faixa para temporada aberta", (d) => {
        atualizar(d);
        avisar("A temporada começou!", "ok");
        jogo.vilaIniciada();
      });



      // ===== ESCUTAS (on): o cliente reage aos FATOS do servidor =====
      // ouvir(evento, "o que o cliente faz ao receber", função)
      // ETAPA 2: ouvir "vila.iniciada"         -> jogo.vilaIniciada()
      // ETAPA 3: ouvir "construcao.iniciada"   -> jogo.obraIniciada(...)
      // ETAPA 4: ouvir "operacao.recusada"     -> jogo.recusado(...)
      // ETAPA 5: ouvir "recurso.produzido"     -> jogo.recursoProduzido(...)
      //          e "construcao.concluida"      -> jogo.obraConcluida(...)
      // ETAPA 6: ouvir "vila.encerrada"        -> jogo.vilaEncerrada()
    }

    // ===== PEDIDOS (emit): o cliente PEDE algo ao servidor =====
    // pedir(evento)
    function abrirVila() {
      pedir("vila.abertura_solicitada");
    }
    function construir() {
      // ETAPA 3: pedir "construcao.solicitada"
    }
    function encerrarVila() {
      // ETAPA 6: pedir "vila.encerramento_solicitado"
    }

    return {
      nome,
      papel,
      conectado,
      estado,
      avisos,
      eventosVisiveis,
      contadores,
      ocultarProducao,
      porMinuto,
      entrar,
      abrirVila,
      construir,
      encerrarVila,
    };
  },
}).mount("#app");
