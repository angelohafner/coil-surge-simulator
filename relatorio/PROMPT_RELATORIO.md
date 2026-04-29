# Prompt executavel para gerar o relatorio LaTeX

Voce e um agente responsavel por criar uma documentacao tecnica em **LaTeX** sobre o projeto Python localizado em `E:\surto-1`.

O resultado deve ser salvo **exclusivamente** em `E:\surto-1\relatorio`.

## Objetivo final

Criar um relatorio tecnico, em portugues do Brasil, que explique com clareza:

- o que faz o projeto Python;
- como o projeto simula surtos em uma bobina por parametros distribuidos;
- o que faz o arquivo `surto_bobina.atp`;
- como o modelo Python se relaciona com o modelo ATP;
- o significado tecnico de todas as figuras e animacoes disponiveis em `E:\surto-1\output`;
- o circuito simulado, desenhado no proprio LaTeX com TikZ ou `circuitikz`.
- os fundamentos de engenharia eletrica envolvidos: transitorios eletromagneticos, parametros distribuidos, ondas viajantes, reflexoes, amortecimento, impedancia de surto, resposta de bobinas a impulso atmosferico e uso de ATP/EMTP em estudos de transitorios.
- referencias bibliograficas reais e verificaveis, citadas ao longo do texto e listadas no final do documento.

O relatorio deve ser facil de ler, facil de manter e organizado em varios arquivos pequenos.

O foco principal deve ser o **conteudo tecnico de engenharia eletrica**. A explicacao do codigo deve servir para apoiar a compreensao do modelo fisico, dos metodos numericos e da interpretacao dos resultados eletricos.

## Regras obrigatorias

- Trabalhe dentro de `E:\surto-1\relatorio`.
- Crie o arquivo principal `E:\surto-1\relatorio\relatorio.tex`.
- Nao altere nenhum arquivo fora de `E:\surto-1\relatorio`.
- Pode ler arquivos de `E:\surto-1`, mas toda geracao nova deve ficar dentro de `E:\surto-1\relatorio`.
- Estruture o LaTeX de forma modular.
- Prefira varios arquivos pequenos em vez de poucos arquivos longos.
- Use `\input`, `\include` ou estrategia equivalente para dividir secoes.
- O documento deve compilar com `pdflatex` ou `latexmk`, se as ferramentas estiverem disponiveis.
- Se alguma etapa nao puder ser concluida por limitacao tecnica, registre isso no proprio relatorio e explique a alternativa adotada.

## Estrutura de arquivos esperada

Crie uma estrutura parecida com esta, podendo adaptar se houver boa justificativa:

```text
E:\surto-1\relatorio\
  relatorio.tex
  preamble.tex
  macros.tex
  sections\
    00_resumo.tex
    01_visao_geral.tex
    02_arquitetura_python.tex
    03_modelo_eletrico.tex
    04_fonte_surto.tex
    05_modelo_atp.tex
    06_correspondencia_python_atp.tex
    07_resultados_figuras.tex
    08_animacoes.tex
    09_conclusao.tex
    10_referencias.tex
  figures\
    circuito_tikz.tex
    output\
      ... copias das figuras estaticas usadas ...
  frames\
    ... frames extraidos dos GIFs, se usados pelo pacote animate ...
  references.bib
  build_notes.tex
```

Use nomes claros. Evite concentrar o relatorio inteiro em `relatorio.tex`.

## Ordem de execucao

Siga este checklist na ordem:

1. Criar ou limpar apenas a estrutura necessaria dentro de `E:\surto-1\relatorio`.
2. Inventariar os arquivos do projeto Python.
3. Inventariar recursivamente todas as imagens e animacoes em `E:\surto-1\output`.
4. Ler os arquivos obrigatorios listados neste prompt.
5. Copiar para `E:\surto-1\relatorio\figures\output` todas as figuras estaticas que serao inseridas no PDF.
6. Para cada GIF, tentar converter em sequencia de frames dentro de `E:\surto-1\relatorio\frames`.
7. Montar as animacoes no PDF com `animate`, `animategraphics`, `animateinline`, `media9` ou tecnica equivalente.
8. Criar o desenho do circuito em TikZ ou `circuitikz`.
9. Escrever as secoes em arquivos `.tex` pequenos e tematicos.
10. Criar referencias bibliograficas reais em `references.bib` ou em secao equivalente.
11. Citar as referencias no corpo do texto com `\cite`, `\parencite` ou comando equivalente.
12. Montar `relatorio.tex` como arquivo principal que inclui os demais arquivos.
13. Compilar o LaTeX, se houver ferramenta disponivel.
14. Corrigir erros de compilacao que estejam sob seu controle.
15. Entregar um resumo final indicando arquivos criados, comando de compilacao usado e eventuais limitacoes.

## Arquivos obrigatorios para analise

Leia e use informacoes reais destes arquivos:

- `E:\surto-1\README.md`
- `E:\surto-1\main.py`
- `E:\surto-1\config\default_case.json`
- `E:\surto-1\src`
- `E:\surto-1\run_atp.py`
- `E:\surto-1\simulate_direct.py`
- `E:\surto-1\save_images.py`
- `E:\surto-1\surto_bobina.atp`
- `E:\surto-1\output` e todas as subpastas

Nao invente comportamento. Quando explicar algo, fundamente no codigo, no README, no ATP, na configuracao ou nos artefatos gerados.

## Informacoes tecnicas que devem aparecer

Inclua obrigatoriamente estes pontos:

- O projeto Python simula a propagacao de surtos em uma bobina modelada por parametros distribuidos.
- O caso padrao usa `N = 20` secoes.
- `L_total = 0.01 H`.
- `R_total = 5.0 ohm`.
- `C_total = 1e-9 F`.
- `model_type = "pi"`.
- `source_type = "double_exp"`.
- `V_amplitude = 1000 V`.
- `t_front = 1.2e-6 s`.
- `t_tail = 50e-6 s`.
- `t_total = 5e-5 s`.
- `dt = 1e-8 s`.
- A terminacao padrao e circuito aberto.
- O arquivo `surto_bobina.atp` representa uma escada Pi com 20 secoes, ramos serie `R-L`, capacitores para terra, fonte dupla exponencial no no `N0` e saida aberta em `N20`.

## Enfase obrigatoria em engenharia eletrica

O relatorio nao deve ser apenas uma descricao de software. Ele deve explicar o significado eletrico do modelo e dos resultados.

Inclua, com profundidade adequada, os seguintes topicos:

- transitorios eletromagneticos em enrolamentos e bobinas;
- aproximacao de uma bobina por parametros distribuidos;
- diferenca entre modelos concentrados e distribuidos;
- interpretacao fisica de `R`, `L` e `C` distribuidos ao longo do enrolamento;
- escadas Pi e T como aproximacoes discretas de uma linha ou enrolamento distribuido;
- propagacao de ondas de tensao e corrente;
- reflexoes causadas por terminacao em circuito aberto;
- amortecimento devido a resistencia serie;
- efeito da capacitancia total e da capacitancia por secao na distribuicao de tensao;
- gradiente de tensao entre secoes e sua relevancia para solicitacao dieletrica;
- tensao de entrada, tensao de saida e relacao de transferencia;
- significado fisico da impedancia de surto;
- relacao entre impulso atmosferico 1.2/50 us e ensaios de alta tensao;
- uso de ATP/EMTP para estudos de transitorios eletromagneticos;
- limitacoes do modelo, incluindo discretizacao em 20 secoes, ausencia de acoplamentos adicionais se nao estiverem implementados, simplificacoes de perdas e condicoes de contorno.

Ao interpretar figuras e GIFs, priorize a leitura eletrica dos resultados: onde a onda se propaga, onde ha reflexao, onde ha maior gradiente, como a energia e dissipada e como a topologia Pi/T ou a capacitancia afeta a resposta.

## Referencias e citacoes obrigatorias

Inclua referencias bibliograficas reais e verificaveis sobre engenharia eletrica, transitorios eletromagneticos, ATP/EMTP, ensaios de impulso e parametros distribuidos.

Regras:

- Criar `E:\surto-1\relatorio\references.bib` ou uma secao de referencias equivalente.
- Citar as referencias no corpo do texto, nao apenas listar no final.
- Usar um estilo bibliografico consistente, como IEEE, ABNT, `plain`, `ieeetr`, `biblatex` ou equivalente.
- Preferir referencias tecnicas reconhecidas: livros, normas, manuais tecnicos, artigos ou documentacao oficial.
- Verificar que cada referencia citada no texto aparece na bibliografia.
- Verificar que cada item da bibliografia e citado pelo menos uma vez no texto.

Referencias recomendadas para buscar, verificar e citar quando forem pertinentes:

- literatura classica de transitorios eletromagneticos em sistemas de potencia;
- livros ou manuais sobre EMTP/ATP;
- documentacao oficial do ATP/EMTP;
- normas ou guias sobre ensaios de impulso de alta tensao, como IEC 60060 ou norma equivalente;
- referencias sobre linhas de transmissao, ondas viajantes e parametros distribuidos;
- materiais tecnicos sobre resposta de enrolamentos de transformadores ou bobinas a surtos, se disponiveis.

Nao invente autores, titulos, normas, anos ou edicoes. Se nao conseguir verificar uma referencia, nao a use como citacao formal.

## Conteudo minimo por secao

### Resumo

- Explique o problema estudado.
- Explique que o relatorio documenta o simulador Python, o caso ATP e os resultados visuais.
- Mencione a bobina distribuida, o impulso 1.2/50 us e a comparacao de modelos.

### Visao geral do projeto

- Explique o objetivo do projeto.
- Explique quais resultados sao gerados: CSV, PNG e GIF.
- Explique o papel geral das pastas `config`, `src` e `output`.

### Arquitetura Python

Explique o papel dos arquivos e modulos:

- `main.py`
- `run_atp.py`
- `simulate_direct.py`
- `save_images.py`
- `src\models`
- `src\solvers`
- `src\sources`
- `src\utils`
- `src\visualization`

### Fluxo de execucao

Descreva o fluxo:

- leitura de `config\default_case.json`;
- criacao da fonte de impulso;
- montagem do modelo da bobina;
- solucao numerica no dominio do tempo;
- pos-processamento;
- exportacao de CSV;
- geracao de figuras;
- geracao de GIFs;
- cenarios Pi, T, baixa capacitancia e alta capacitancia, se confirmados no codigo.

### Modelo eletrico

Explique:

- modelo de bobina distribuida;
- modelo Pi;
- modelo T;
- diferenca entre Pi e T;
- divisao dos parametros totais por secao;
- papel de `R_sec`, `L_sec`, `C_sec` e `C_sec/2`;
- terminacao em circuito aberto;
- propagacao, reflexoes e amortecimento do surto.
- impedancia de surto e sua interpretacao fisica.
- gradiente de tensao entre secoes e consequencias para isolacao.
- limites da aproximacao por secoes discretas.

Inclua equacoes em LaTeX quando forem uteis.

Use citacoes bibliograficas nesta secao para sustentar os conceitos de parametros distribuidos, ondas viajantes, transitorios e modelos Pi/T.

### Fonte de surto

Inclua e explique a forma de onda dupla exponencial:

```latex
V(t) = A\left(e^{-\alpha t} - e^{-\beta t}\right)
```

Explique:

- amplitude;
- tempo de frente;
- tempo de cauda;
- normalizacao para pico;
- relacao com impulso atmosferico 1.2/50 us, se sustentado pelos arquivos.

Use referencias sobre ensaios de impulso e formas de onda padronizadas, citando normas ou literatura tecnica quando possivel.

### Arquivo ATP

Explique detalhadamente `surto_bobina.atp`:

- cabecalho;
- parametros globais de simulacao;
- significado de `XOPT` e `COPT`, se aplicavel;
- ramos serie `R-L`;
- capacitores shunt para terra;
- fonte tipo 14 dupla exponencial;
- nos `N0`, `N5`, `N10`, `N15` e `N20`;
- saida aberta;
- correspondencia dos valores ATP com o caso padrao Python.

Use referencias sobre ATP/EMTP ou simulacao de transitorios eletromagneticos para contextualizar por que esse tipo de arquivo e usado em engenharia eletrica.

### Correspondencia Python versus ATP

Crie uma tabela comparando:

- numero de secoes;
- resistencia total e por secao;
- indutancia total e por secao;
- capacitancia total e por secao;
- fonte de impulso;
- tempo de simulacao;
- passo de amostragem;
- nos observados;
- tipo de terminacao.

### Figuras estaticas

Crie uma secao especifica para todas as figuras estaticas encontradas em `E:\surto-1\output` e subpastas.

Para cada figura:

- insira a imagem no PDF;
- crie legenda tecnica;
- referencie a figura no texto;
- explique a grandeza mostrada;
- explique eixos e unidades;
- diga se a figura vem do modelo Pi, modelo T, ATP ou comparacao;
- explique o comportamento fisico observado;
- explique por que a figura ajuda a entender a propagacao do surto.
- relacione a interpretacao com conceitos de engenharia eletrica, como onda viajante, reflexao, amortecimento, impedancia de surto, distribuicao de tensao e solicitacao dieletrica.

### Animacoes

Crie uma secao especifica para os GIFs em `E:\surto-1\output\gifs`.

Para cada GIF:

- tente inserir a animacao real no PDF;
- explique o que varia ao longo do tempo;
- explique que fenomeno fica mais claro na animacao;
- explique se a animacao mostra propagacao, reflexao, amortecimento, comparacao de capacitancia ou comparacao de modelo;
- se a animacao nao puder ser preservada no PDF, insira uma imagem estatica representativa e documente a limitacao.
- interprete o comportamento animado com foco no fenomeno eletrico, nao apenas na visualizacao.

## Figuras e animacoes atualmente conhecidas

Ao iniciar, faca uma busca recursiva. Use a lista abaixo como minimo esperado, mas inclua tambem qualquer arquivo adicional encontrado.

Figuras estaticas:

- `E:\surto-1\output\atp\grafico_overlay.png`
- `E:\surto-1\output\atp\grafico_subplots.png`
- `E:\surto-1\output\atp\screenshot.png`
- `E:\surto-1\output\figures\gradient.png`
- `E:\surto-1\output\figures\heatmap.png`
- `E:\surto-1\output\figures\io_voltage.png`
- `E:\surto-1\output\figures\max_voltage.png`
- `E:\surto-1\output\figures\section_voltages.png`
- `E:\surto-1\output\t_model\figures\gradient.png`
- `E:\surto-1\output\t_model\figures\heatmap.png`
- `E:\surto-1\output\t_model\figures\io_voltage.png`
- `E:\surto-1\output\t_model\figures\max_voltage.png`
- `E:\surto-1\output\t_model\figures\section_voltages.png`

Animacoes:

- `E:\surto-1\output\gifs\comparison_capacitance.gif`
- `E:\surto-1\output\gifs\comparison_model.gif`
- `E:\surto-1\output\gifs\heatmap_anim.gif`
- `E:\surto-1\output\gifs\voltage_wave_pi.gif`
- `E:\surto-1\output\gifs\voltage_wave_t.gif`

## Requisitos para GIFs no PDF

Prioridade tecnica:

1. Converter cada GIF em frames dentro de `E:\surto-1\relatorio\frames\<nome_do_gif>\`.
2. Usar o pacote LaTeX `animate` com `\animategraphics`.
3. Ativar controles, loop e autoplay quando fizer sentido.
4. Inserir uma legenda explicando que a animacao depende de visualizador PDF compativel.
5. Se `animate` nao funcionar no ambiente de compilacao, testar alternativa com `media9` ou abordagem equivalente.
6. Se nenhuma alternativa funcionar, incluir frame representativo e registrar a limitacao no relatorio.

Nao trate os GIFs apenas como links. Tente de fato incorpora-los como animacoes no PDF.

## Requisitos para o circuito em TikZ

Crie uma figura em LaTeX TikZ ou `circuitikz` que represente o circuito simulado.

A figura deve mostrar:

- fonte aplicada ao no `N0`;
- escada Pi;
- ramos serie com `R_sec` e `L_sec`;
- capacitores para terra;
- capacitores dos extremos como `C_sec/2`;
- capacitores internos como `C_sec`;
- reticencias indicando as secoes intermediarias;
- total `N = 20`;
- saida aberta em `N20`.

O codigo da figura deve ficar em arquivo separado, por exemplo:

```text
E:\surto-1\relatorio\figures\circuito_tikz.tex
```

## Requisitos de escrita

- Escreva em portugues do Brasil.
- Use tom academico e tecnico.
- Seja claro para alguem que nunca viu o projeto.
- Cite nomes reais de arquivos, classes, funcoes, parametros e saidas.
- Evite explicacoes genericas.
- Explique hipoteses quando houver ambiguidade.
- Use equacoes LaTeX quando ajudarem.
- Use tabelas quando facilitarem comparacoes.
- Toda figura deve ter legenda e ser mencionada no texto.
- Todo GIF deve ter legenda, explicacao e observacao sobre compatibilidade de animacao no PDF.
- Inclua citacoes bibliograficas nos trechos que explicam conceitos de engenharia eletrica, normas, ATP/EMTP, formas de onda de impulso e parametros distribuidos.
- Inclua uma bibliografia final consistente.

## Criterios de aceite

O trabalho so esta completo quando todos estes itens forem verdadeiros:

- Existe `E:\surto-1\relatorio\relatorio.tex`.
- O LaTeX esta organizado em varios arquivos pequenos.
- `relatorio.tex` inclui as secoes auxiliares.
- O relatorio explica o projeto Python.
- O relatorio explica `surto_bobina.atp`.
- O relatorio compara Python e ATP.
- O relatorio inclui uma figura TikZ do circuito.
- Todas as figuras estaticas de `E:\surto-1\output` e subpastas foram usadas ou uma justificativa clara foi registrada.
- Todos os GIFs de `E:\surto-1\output\gifs` foram tentados como animacoes reais no PDF.
- Cada figura e cada GIF tem explicacao tecnica.
- O relatorio tem foco substancial em engenharia eletrica, nao apenas em programacao.
- O relatorio contem referencias bibliograficas reais.
- As referencias sao citadas no texto.
- A bibliografia final contem apenas itens citados.
- Ha uma nota clara sobre eventuais limitacoes dos GIFs animados no PDF.
- O relatorio compila, ou a falha de compilacao restante esta documentada com causa objetiva.

## Entrega final esperada

Ao terminar, informe:

- caminho do arquivo principal `relatorio.tex`;
- estrutura criada dentro de `E:\surto-1\relatorio`;
- comando usado para compilar;
- se o PDF foi gerado;
- quais GIFs ficaram animados no PDF;
- quais GIFs, se houver, ficaram apenas como representacao estatica e por qual motivo.
- se as referencias foram incluidas e qual sistema bibliografico foi usado.
