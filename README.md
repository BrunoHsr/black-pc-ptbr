# BLACK — Tradução PT-BR para o port de PC

Tradução para português do Brasil do **BLACK** (Criterion, 2006) rodando no
[port não oficial de PC](https://github.com/Spark198rus/black-pc) do Spark198rus:

- **Textos do jogo:** menus, opções, objetivos, dicas ("intel black"), mensagens, resultados e funções dos créditos (1063 textos).
- **Legendas nas cenas da história:** as falas dos 9 vídeos de interrogatório entre as missões, em PT-BR, gravadas na própria imagem dos vídeos.
- **Acentos:** as fontes do jogo ganharam **Ã/ã** (e **Õ/õ** na fonte grande), montados com peças da própria fonte. As outras letras acentuadas já existiam.

> ⚠️ **Tradução feita com inteligência artificial.** Os textos e as legendas foram traduzidos por IA, e as falas
> das cenas foram transcritas com o Whisper (reconhecimento de fala). O resultado foi conferido dentro do jogo
> (telas, tamanho dos textos, sincronia das legendas), mas pode ter erros de tradução ou de interpretação.
> Correções são bem-vindas (veja [Como corrigir](#como-corrigir)).

Este repositório **não contém nenhum arquivo do jogo**. O aplicador gera os arquivos traduzidos a partir da **sua**
cópia do BLACK e guarda os originais para você poder voltar atrás.

## Requisitos

- O port de PC funcionando com o disco **NTSC-U** (o mesmo que o port exige; o aplicador confere o `default.xbe`).
- Windows 10 ou 11.
- [Python 3.10+](https://www.python.org/downloads/) com o Pillow: `python -m pip install pillow`
- **ffmpeg** completo (com o codificador `wmv2` e o filtro `subtitles`): `winget install Gyan.FFmpeg`
  (depois abra um terminal novo).

## Instalação

1. Baixe este repositório (**Code → Download ZIP**) e extraia em qualquer lugar.
2. Dê dois cliques em **`aplicar.bat`** e arraste para a janela a pasta do BLACK (a que tem a pasta `game`
   e a `port`), depois aperte Enter. Pelo terminal: `aplicar.bat "D:\Jogos\BLACK"`.
3. Leva uns 30 segundos. Pronto: abra o jogo normalmente.

Os originais ficam em `traducao-ptbr-backup`, ao lado da pasta `game`.
**Para desfazer:** `aplicar.bat --restaurar "D:\Jogos\BLACK"`.

Rodar o aplicador de novo (por exemplo, depois de uma versão nova da tradução) usa os originais guardados no backup.

## O que fica em inglês

- **Itens do próprio port:** `QUIT` no menu principal e as páginas **PC SETTINGS**. Esses textos vêm do
  executável do port, não dos arquivos do jogo.
- **As vozes.** O jogo não tem dublagem em português; as cenas ganharam legenda, e o rádio durante as missões
  continua sem legenda (o jogo não tem sistema de legendas para isso).
- Nomes próprios, de armas e de lugares (Seventh Wave, Black Ops, Naszran, Tivliz…), e os nomes nos créditos.

## Como corrigir

- **Textos do jogo:** `traducao/pt/*.tsv`, uma linha por texto: `índice<TAB>texto`. `\r\n` é quebra de linha,
  `<F01E>` e parecidos são ícones de botão do controle, e `%s`, `%d`, `%1` são valores que o jogo preenche.
  Esses três precisam continuar no texto, e o aplicador recusa a tradução se faltar algum.
- **Legendas:** `legendas/<vídeo>.tsv`, uma fala por linha: `início<TAB>fim<TAB>texto` (segundos desde o começo
  do vídeo; `\N` quebra a linha). Mantenha no máximo duas linhas de ~50 caracteres.

Depois de editar, rode o `aplicar.bat` de novo. Mande a correção como *pull request* ou abra uma *issue*.

## Como funciona (técnico)

| Parte | Arquivo do jogo | O que o aplicador faz |
|---|---|---|
| Textos | `language/strings/MainUS.bin` | Tabela {chave de 32 bits, texto UTF-8}; troca o texto e mantém chaves e ordem (`patch/strtab.py`, `patch/build_strings.py`). |
| Fontes | `language/fonts/Small.bin`, `Big.bin` | Fonte bitmap (DXT3) com tabela de 129 baldes, `(código & 0x7F) + 1`. Desenha Ã/Õ com o corpo do A/O e o til do Ñ, insere os registros no balde certo e só regrava blocos vazios da textura (`patch/fontpatch.py`). Os menus ("Eurostile LT Std" / "ITC Machine Std") usam essas mesmas duas fontes. |
| Vídeos | `videos/03_n.xmv` … `18_n.xmv` | XMV do Xbox (WMV2). Decodifica com o ffmpeg, repete os quadros "pulados", queima a legenda (libass) e recodifica em WMV2 com os mesmos quadros e tempos. A extradata é convertida para o formato do XMV, e os pacotes são remontados sem passar do maior pacote do vídeo original, para o player não usar mais memória (`patch/xmv.py`, `patch/revideo.py`, `patch/legendas.py`). |

A legenda fica na faixa preta de baixo do vídeo e é comprimida na horizontal (75%), porque o port estica o quadro
4:3 para 16:9.

O áudio das cenas fica separado, em `sound/streams/*.bks`: 7 faixas por arquivo (idiomas), blocos estéreo de
0x4000 com quadros EA-XAS; o jogo NTSC-U toca a faixa 5 (inglês). As ferramentas usadas para extrair, transcrever
e testar estão em `dev/` (não são necessárias para aplicar a tradução).

## Aviso legal

Projeto de fãs, sem fins lucrativos, sem ligação com a Electronic Arts, a Criterion Games ou o autor do port.
BLACK é marca da Electronic Arts. Você precisa da sua própria cópia original do jogo. Nenhum código ou dado do jogo
está neste repositório.

Port de PC: [Spark198rus/black-pc](https://github.com/Spark198rus/black-pc).
