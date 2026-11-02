const { createApp, ref, reactive, computed, nextTick } = Vue;

createApp({
  setup() {
    const nome = ref("");
    const papel = ref("");
    const conectado = ref(false);
    const estado = reactive({
      fase: "aguardando",
      nectar: 0,
      mel: 0,
      moeda: 0,
      apicultores: 0,
      limite: 0,
      limite_colmeia: 0,
      producao: 0,
      producao_mel: 0,
      intervalo: 0,
      tempo_obra: 0,
      custo: 0,
      mel_por_venda: 0,
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

    const nectarPorMinuto = computed(() =>
      estado.intervalo
        ? Math.round((estado.producao * 60) / estado.intervalo)
        : 0,
    );

    const melPorMinuto = computed(() =>
      estado.intervalo
        ? Math.round((estado.producao_mel * 60) / estado.intervalo)
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
          "néctar " +
            e.nectar +
            ", mel " +
            e.mel +
            ", apicultores " +
            e.apicultores +
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

      // ===== ESCUTAS (on): o cliente reage  aos FATOS do servidor =====

      ouvir("estado.sincronizado", "guarda o estado e desenha o apiário e mercado", (d) => {
        atualizar(d);
        jogo.mostrarEstado(d.estado);
      });

      ouvir("apiario.iniciado", "muda a faixa para temporada aberta", (d) => {
        atualizar(d);
        avisar("A temporada começou!", "ok");
        jogo.vilaIniciada();
      });

      ouvir("colmeia.iniciada", "mostra a colmeia sendo construída", (d) => {
        atualizar(d);
        avisar(d.por + " iniciou uma obra");
        jogo.obraIniciada(d.estado);
      });

      ouvir("operacao.recusada", "avisa o motivo e a tela treme", (d) => {
        avisar(d.motivo, "erro");
        jogo.recusado(d.motivo);
      });

      ouvir(
        "recurso.produzido",
        "atualiza o nectar e mel, mostra o +N",
        (d) => {
          atualizar(d);
          jogo.recursoProduzido(d.estado);
        },
      );

      ouvir("colmeia.concluida", "exibe a colmeia pronta", (d) => {
        atualizar(d);
        avisar("Obra de " + d.por + " concluída! A produção aumentou.", "ok");
        jogo.obraConcluida(d.estado);
      });

      ouvir(
        "apiario.encerrado",
        "escurece o apiário e bloqueia novas ações",
        (d) => {
          atualizar(d);
          avisar("Temporada encerrada.");
          jogo.vilaEncerrada();
        },
      );

      ouvir(
        "mel.vendido",
        "vende o mel produzido e ganha moedas em troca",
        (d) => {
          atualizar(d);
          avisar(d.por + " vendeu o mel estocado", "ok");
          jogo.melVendido(d.estado)
        },
      );
    }

    // ===== PEDIDOS (emit): o cliente PEDE algo ao servidor =====
    function abrirVila() {
      pedir("apiario.abertura_solicitada");
    }

    function construir() {
      pedir("colmeia.solicitada");
    }

    function vender() {
      pedir("mel.venda_solicitada");
    }

    function encerrarVila() {
      pedir("apiario.encerramento_solicitado");
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
      nectarPorMinuto,
      melPorMinuto,
      entrar,
      abrirVila,
      construir,
      vender,
      encerrarVila,
    };
  },
}).mount("#app");
