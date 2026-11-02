function criarJogo() {
  let cena = null; // a cena, quando já estiver pronta
  let partida = null; // o jogo Phaser
  const fila = []; // chamadas feitas antes da cena existir
  const chamar = (nome, ...args) =>
    cena ? cena[nome](...args) : fila.push([nome, args]);

  class VilaScene extends Phaser.Scene {
    constructor() {
      super("vila");
    }

    preload() {
      this.load.image("tiles", "assets/tileset-vila.png"); // peças do cenário
      this.load.spritesheet(
        "sprites",
        "assets/sprites-vila.png", // casa e canteiro
        { frameWidth: 32, frameHeight: 32 },
      );
      this.load.tilemapTiledJSON("mapa", "assets/vila.json"); // o mapa
    }

    create() {
      // 1) o mapa: duas camadas de peças (chão e decoração)
      const mapa = this.make.tilemap({ key: "mapa" });
      const tileset = mapa.addTilesetImage("tileset-vila", "tiles"); // nome no Tiled, chave da imagem
      mapa.createLayer("chao", tileset);
      mapa.createLayer("decoracao", tileset);

      // 2) pontos marcados no mapa: onde ficam as obras e o acampamento de lenha
      const pontos = mapa.getObjectLayer("pontos").objects;
      this.lotes = pontos
        .filter((p) => p.name.startsWith("lote"))
        .sort((a, b) => a.name.localeCompare(b.name, "pt", { numeric: true }));
      this.acampamento = pontos.find((p) => p.name === "acampamento");

      // 3) câmera: o mapa é pequeno (pixel art), então damos zoom 2x
      this.cameras.main
        .setZoom(2)
        .centerOn(mapa.widthInPixels / 2, mapa.heightInPixels / 2);
      this.larg = mapa.widthInPixels;
      this.alt = mapa.heightInPixels;

      this.obras = []; // obras em andamento (a primeira a começar é a primeira a terminar)
      this.usados = 0; // quantos lotes já foram usados
      this.faixa = this.add
        .text(this.larg / 2, 9, "⏳ Aguardando o Mestre", {
          fontSize: "8px",
          color: "#ffffff",
          backgroundColor: "#00000099",
          padding: { x: 5, y: 2 },
          resolution: 2,
        })
        .setOrigin(0.5)
        .setDepth(10);

      cena = this;
      fila.splice(0).forEach(([nome, args]) => this[nome](...args));
    }

    // ----- apoio -----
    lote(i) {
      return this.lotes[i % this.lotes.length];
    }
    criarCasa(x, y) {
      const casa = this.add.sprite(x, y, "sprites", 0);
      this.tweens.add({
        targets: casa,
        scale: { from: 0.3, to: 1 },
        duration: 400,
        ease: "Back.Out",
      });
    }
    criarObra(duracao) {
      const { x, y } = this.lote(this.usados++);
      const canteiro = this.add.sprite(x, y, "sprites", 1);
      const fundo = this.add
        .rectangle(x - 10, y + 16, 20, 3, 0x333333)
        .setOrigin(0, 0.5);
      const barra = this.add
        .rectangle(x - 10, y + 16, 20, 3, 0xffd54a)
        .setOrigin(0, 0.5);
      barra.scaleX = 0;
      this.tweens.add({ targets: barra, scaleX: 1, duration: duracao });
      this.obras.push({ canteiro, fundo, barra, x, y });
    }
    flutuar(texto, x, y, cor) {
      const t = this.add
        .text(x, y, texto, {
          fontSize: "8px",
          color: cor,
          fontStyle: "bold",
          stroke: "#ffffff",
          strokeThickness: 2,
          resolution: 2,
        })
        .setOrigin(0.5)
        .setDepth(8);
      this.tweens.add({
        targets: t,
        y: y - 16,
        alpha: 0,
        duration: 1400,
        onComplete: () => t.destroy(),
      });
    }

    // ----- um método para cada evento do servidor -----
    mostrarEstado(estado) {
      // estado.sincronizado
      for (let i = 0; i < estado.concluidas; i++) {
        const p = this.lote(this.usados++);
        this.criarCasa(p.x, p.y);
      }
      for (let i = 0; i < estado.em_obra; i++)
        this.criarObra(estado.tempo_obra * 1000);
      if (estado.fase === "aberta") this.vilaIniciada();
      if (estado.fase === "encerrada") this.vilaEncerrada();
    }
    vilaIniciada() {
      // apiario.iniciado
      this.faixa.setText("☀️ Temporada aberta");
    }
    obraIniciada(estado) {
      // colmeia.iniciada
      this.criarObra(estado.tempo_obra * 1000);
      this.flutuar(
        "-" + estado.custo + " 🐝",
        this.acampamento.x,
        this.acampamento.y,
        "#b00020",
      );
    }
    obraConcluida(estado) {
      // colmeia.concluida
      const obra = this.obras.shift();
      if (!obra) return;
      obra.canteiro.destroy();
      obra.fundo.destroy();
      obra.barra.destroy();
      this.criarCasa(obra.x, obra.y);
      this.flutuar("🏠 Obra concluída!", obra.x, obra.y - 18, "#1b5e20");
    }
    recursoProduzido(estado) {
      // recurso.produzido
      this.flutuar(
        "+" + estado.producao + " 🐝",
        this.acampamento.x,
        this.acampamento.y,
        "#1b5e20",
      );

      if(!estado.producao_mel) return

      this.flutuar(
        "+" + estado.producao_mel + " 🍯",
        this.acampamento.x,
        this.acampamento.y + 10,
        "#1b5e20",
      );
    }
    recusado(motivo) {
      // operacao.recusada (só quem pediu)
      this.cameras.main.shake(180, 0.006);
      this.flutuar("✋ " + motivo, this.larg / 2, this.alt - 28, "#b00020");
    }
    vilaEncerrada() {
      // apiario.encerrado
      this.faixa.setText("🌙 Temporada encerrada");
      this.add
        .rectangle(
          this.larg / 2,
          this.alt / 2,
          this.larg,
          this.alt,
          0x000033,
          0.35,
        )
        .setDepth(5);
    }
  }

  return {
    iniciar(idContainer) {
      if (partida) return;
      partida = new Phaser.Game({
        type: Phaser.AUTO,
        parent: idContainer,
        width: 576,
        height: 288,
        pixelArt: true,
        backgroundColor: "#7bb661",
        scene: VilaScene,
        audio: { noAudio: true },
      });
    },
    mostrarEstado: (...a) => chamar("mostrarEstado", ...a),
    vilaIniciada: (...a) => chamar("vilaIniciada", ...a),
    obraIniciada: (...a) => chamar("obraIniciada", ...a),
    obraConcluida: (...a) => chamar("obraConcluida", ...a),
    recursoProduzido: (...a) => chamar("recursoProduzido", ...a),
    recusado: (...a) => chamar("recusado", ...a),
    vilaEncerrada: (...a) => chamar("vilaEncerrada", ...a),
  };
}
