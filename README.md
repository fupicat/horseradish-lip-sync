# Horseradish Lip Sync

Horseradish Lip Sync gera dados de sincronização labial a partir de uma gravação de voz. Ele usa o Whisper (`faster-whisper`) para detectar o idioma e reconhecer a fala, o Montreal Forced Aligner (MFA) para alinhar palavras e fonemas, e converte o alinhamento em formatos de boca.

O projeto foi criado como uma alternativa compatível com a CLI do [Rhubarb Lip Sync](https://github.com/DanielSWolf/rhubarb-lip-sync), com o objetivo de gerar animação labial mais apropriada para o idioma português. Uma instalação do Rhubarb pode, em muitos casos, ser substituída pelo executável do Horseradish renomeado para `rhubarb.exe` e imediatamente obter melhores resultados.

## Requisitos

- Windows 64 bits (versões para Linux e MacOS indisponíveis no momento)
- Um arquivo de áudio em WAVE (`.wav`) ou Ogg Vorbis (`.ogg`)
- Conexão com a internet na primeira execução, caso os modelos de idioma ainda não tenham sido baixados

## Instalação e uso

Baixe e extraia o zip mais recente na página de [releases](https://github.com/fupicat/horseradish-lip-sync/releases). Este programa é projetado para ser executado em segundo plano por integrações com programas de animação, porém a CLI também pode ser usada diretamente.

Exemplo básico:

```powershell
.\horseradish.exe fala.wav
```

Por padrão, o resultado é escrito em TSV no terminal. Para gravar o resultado em um arquivo:

```powershell
.\horseradish.exe -o fala.tsv fala.wav
```

Para ver todas as opções:

```powershell
.\horseradish.exe --help
```

Se quiser utilizá-lo no lugar do Rhubarb em alguma integração existente, você também precisará renomear o executável para `rhubarb.exe` e copiar tanto ele quanto a pasta `horseradish` para dentro da pasta onde o Rhubarb está.

## Opções de linha de comando

| Opção                   | Padrão        | Descrição                                                                                                                                 |
| ----------------------- | ------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `inputFile`             | obrigatório   | Arquivo de áudio analisado. Deve ser o último argumento.                                                                                  |
| `-r`, `--recognizer`    | `mfa`         | Mantida por compatibilidade. Atualmente o MFA é o único reconhecedor suportado.                                                           |
| `-f`, `--exportFormat`  | `tsv`         | Formato de saída: `tsv`, `xml`, `json` ou `dat`.                                                                                          |
| `-d`, `--dialogFile`    | —             | Arquivo de texto com o diálogo do áudio. Pula a etapa de transcrição e pode agilizar o processo.                                          |
| `--extendedShapes`      | `GHX`         | Formatos estendidos habilitados. Use `""` para os seis formatos básicos.                                                                  |
| `-o`, `--output`        | —             | Caminho do arquivo de saída. Sem esta opção, o resultado é enviado para `stdout`.                                                         |
| `--frameRate`           | `24`          | Taxa de quadros usada pelo reenquadramento e pelos formatos baseados em quadros.                                                          |
| `--datFrameRate`        | `--frameRate` | Opção legado usada apenas com `dat`.                                                                                                      |
| `--exposureDuration`    | `1`           | Número mínimo de quadros que uma posição de boca ocupa: `1` para animação _on ones_, `2` _on twos_, etc.                                  |
| `--useTransitionFrames` | desativado    | Adiciona quadros de transição entre quadros-chave. Utiliza-se um formato de boca adicional para cada formato base, com o sufixo `-trans`. |
| `--datUsePrestonBlair`  | desativado    | Usa nomes Preston Blair em vez das letras do formato `dat`.                                                                               |
| `--outputAnalysis`      | —             | Salva o alinhamento fonético produzido pelo MFA em JSON para depuração.                                                                   |
| `--machineReadable`     | desativado    | Escreve mensagens de progresso e resultado no `stderr` como objetos JSON.                                                                 |
| `-q`, `--quiet`         | desativado    | Suprime mensagens de progresso no `stderr`.                                                                                               |
| `--version`             | —             | Exibe a versão e encerra.                                                                                                                 |

Exemplo com diálogo conhecido e saída JSON:

```powershell
.\horseradish.exe -f json -d fala.txt -o fala.json fala.wav
```

Exemplo para animação em 24 fps, com transições:

```powershell
.\horseradish.exe --frameRate 24 --useTransitionFrames -f dat -o fala.dat fala.wav
```

## Formatos de saída

### TSV

Cada linha contém o tempo inicial em segundos e o formato de boca separado por tabulação:

```text
0.00	X
0.25	B
0.50	C
1.20	X
```

### XML

Contém início e fim de cada formato de boca, além de metadados do áudio:

```xml
<rhubarbResult>
  <metadata>
    <soundFile>C:\audio\fala.wav</soundFile>
    <duration>1.20</duration>
  </metadata>
  <mouthCues>
    <mouthCue start="0.00" end="0.25">X</mouthCue>
  </mouthCues>
</rhubarbResult>
```

### JSON

Mesma coisa que o formato anterior, porém como JSON:

```json
{
  "metadata": {
    "soundFile": "C:\\audio\\fala.wav",
    "duration": 1.2
  },
  "mouthCues": [{ "start": 0.0, "end": 0.25, "value": "X" }]
}
```

### DAT

Contém pares de número de quadro e formato de boca, compatíveis com Moho/OpenToonz:

```text
MohoSwitch1
1 rest
7 etc
12 E
```

## Formatos de boca

O programa usa nove posições:

| Figura                  | Figura `-trans`               | Código | Preston Blair | Movimento aproximado                                                                         |
| ----------------------- | ----------------------------- | ------ | ------------- | -------------------------------------------------------------------------------------------- |
| ![](./imagens/MBP.png)  | ![](./imagens/MBP-trans.png)  | `A`    | `MBP`         | Fechada com lábios juntos, como em `M`, `B` e `P`                                            |
| ![](./imagens/etc.png)  | ![](./imagens/etc-trans.png)  | `B`    | `etc`         | Boca estreita mostrando os dentes, usado para a maioria das consoantes e também o som de `I` |
| ![](./imagens/E.png)    | ![](./imagens/E-trans.png)    | `C`    | `E`           | Boca entreaberta, como em `E`                                                                |
| ![](./imagens/AI.png)   | ![](./imagens/AI-trans.png)   | `D`    | `AI`          | Boca aberta, como em `A`                                                                     |
| ![](./imagens/O.png)    | ![](./imagens/O-trans.png)    | `E`    | `O`           | Boca arredondada, como em `O`                                                                |
| ![](./imagens/U.png)    | ![](./imagens/U-trans.png)    | `F`    | `U`           | Boca projetada, como em `U`                                                                  |
| ![](./imagens/FV.png)   | ![](./imagens/FV-trans.png)   | `G`    | `FV`          | (formato estendido) Boca com dentes encostando o lábio inferior, como em `F` e `V`           |
| ![](./imagens/L.png)    | ![](./imagens/L-trans.png)    | `H`    | `L`           | (formato estendido) Boca mostrando a língua, como em `L`                                     |
| ![](./imagens/rest.png) | ![](./imagens/rest-trans.png) | `X`    | `rest`        | (formato estendido) Descanso ou boca fechada                                                 |

As figuras acima são só para fins de demonstração, o programa não vem com nenhuma figura de boca.

Também há a opção de incluir frames de transição com a opção `--useTransitionFrames`. Cada formato acima recebe um formato adicional, cujo código é o mesmo código com o sufixo `-trans`. A figura deste frame de transição deve ser uma versão semi-aberta/semi-fechada da boca.

## Criando integrações

### Substituição do Rhubarb

O Horseradish aceita a maioria das opções de entrada e todos os formatos de saída utilizados por aplicativos que chamam o Rhubarb por linha de comando. Por exemplo, o programa de animação [Tahoma2D](https://tahoma2d.org/) vem com uma instalação do Rhubarb nos seus arquivos que pode ser substituída para obter resultados melhores.

Para testar uma integração existente:

1. Renomeie o executável do Horseradish para `rhubarb.exe`.
2. Copie o executável e a pasta `horseradish` para a mesma pasta onde o Rhubarb é executado pelo programa.
3. Execute a função de lip sync do programa.

A princípio, tudo deve sair funcionando. Se não, por favor abra um issue explicando a incompatibilidade que você encontrou.

### Saídas estruturadas para uma interface

Use `--machineReadable` para receber eventos no `stderr`. Os eventos incluem `start`, `progress`, `success` e `failure`.

Exemplo de progresso:

```json
{
  "type": "progress",
  "value": 0.4,
  "log": { "level": "Trace", "message": "Progress: 40%" }
}
```

Os frames de lip sync são exibidos em `stdout`, ou no arquivo especificado por `-o`.

### Idiomas suportados

A tabela abaixo indica o nível de suporte de cada idioma que o Horseradish consegue manusear.

- **Confirmado:** Contém todos os modelos necessários para utilizar com qualquer fala, e foi testado e aprovado por um falante da língua.
- **Não-confirmado:** Contém todos os modelos necessários, mas pode não ter ainda mapeamento de formatos de boca para todos os fonemas do idioma. Ajuda de falantes da língua é bem-vinda.
- **Incompleto:** Tem um dicionário limitado de palavras conhecidas, sem a possibilidade de sincronizar palavras fora dele.

| Idioma      | Nível de suporte |
| ----------- | ---------------- |
| Português   | **Confirmado**   |
| Inglês      | **Confirmado**   |
| Búlgaro     | Não-confirmado   |
| Croata      | Não-confirmado   |
| Checo       | Não-confirmado   |
| Francês     | Não-confirmado   |
| Alemão      | Não-confirmado   |
| Hauçá       | Não-confirmado   |
| Japonês     | Não-confirmado   |
| Coreano     | Não-confirmado   |
| Mandarim    | Não-confirmado   |
| Polonês     | Não-confirmado   |
| Russo       | Não-confirmado   |
| Espanhol    | Não-confirmado   |
| Suaíli      | Não-confirmado   |
| Sueco       | Não-confirmado   |
| Tâmil       | Não-confirmado   |
| Tailandês   | Não-confirmado   |
| Turco       | Não-confirmado   |
| Ucraniano   | Não-confirmado   |
| Vietnamita  | Não-confirmado   |
| Abcázio     | Incompleto       |
| Armênio     | Incompleto       |
| Bashkir     | Incompleto       |
| Basco       | Incompleto       |
| Bielorrusso | Incompleto       |
| Chuvache    | Incompleto       |
| Holandês    | Incompleto       |
| Georgiano   | Incompleto       |
| Grego       | Incompleto       |
| Guarani     | Incompleto       |
| Húngaro     | Incompleto       |
| Italiano    | Incompleto       |
| Cazaque     | Incompleto       |
| Curmânji    | Incompleto       |
| Quirguiz    | Incompleto       |
| Romeno      | Incompleto       |
| Tártaro     | Incompleto       |
| Uigur       | Incompleto       |
| Usbeque     | Incompleto       |

## Desenvolvimento

### Ambiente

O arquivo `requirements.txt` é um snapshot de um ambiente Conda para Windows. Ele inclui Python, PyInstaller, `faster-whisper`, Montreal Forced Aligner e suas dependências nativas.

Com Miniforge/Conda, crie o ambiente a partir do arquivo:

```powershell
conda create --name horseradish --file requirements.txt
conda activate horseradish
```

Caso o arquivo não seja reconhecido por versões de Conda com nomes de pacote específicos da plataforma, instale os pacotes principais em um novo ambiente:

```powershell
conda create --name horseradish python
conda activate horseradish
conda install -c conda-forge faster-whisper montreal-forced-aligner pyinstaller
```

### Arquivos principais

- `main.py`: CLI, reconhecimento, alinhamento, reenquadramento e exportação.
- `horseradish.spec`: definição do pacote executável do PyInstaller.
- `build.bat`: cria a distribuição Windows em `dist\horseradish\`.
- `demos/assets/`: recursos de demonstração e exemplos de áudio para testes visuais.

### Executar em modo fonte

No diretório do projeto:

```powershell
python main.py fala.wav
python main.py --help
```

Para depurar o resultado fonético:

```powershell
python main.py --outputAnalysis analysis.json fala.wav
```

### Compilar no Windows

1. Prepare o ambiente Conda com as dependências.
2. Baixe a versão mais recente do [SQLite](https://sqlite.org/download.html) e coloque o executável `sqlite3.exe` na pasta raíz do projeto.
3. Execute:

```powershell
.\build.bat
```

A saída fica em `dist\horseradish\`. O script usa:

- `--onedir` para distribuir o executável com suas dependências
- `--add-binary "sqlite3.exe;."` para incluir o SQLite no pacote
- `--name="horseradish"` para definir o nome da aplicação

O arquivo `horseradish.spec` contém a mesma configuração para uso direto pelo PyInstaller:

```powershell
pyinstaller horseradish.spec --noconfirm
```

### Fluxo de implementação

O pipeline principal é:

1. Detectar o idioma do áudio.
2. Transcrever o áudio ou carregar o texto fornecido em `--dialogFile`.
3. Baixar ou localizar os modelos MFA correspondentes ao idioma.
4. Gerar pronúncias para palavras fora do dicionário quando houver modelo G2P.
5. Alinhar fonemas e tempos.
6. Converter fonemas em formatos de boca.
7. Reenquadrar para a taxa de quadros e duração de exposição.
8. Opcionalmente inserir quadros de transição.
9. Exportar em TSV, XML, JSON ou DAT.

Ao adicionar um formato de saída, implemente o caso correspondente em `main()` e mantenha a saída baseada na lista `lip_frames`. Ao ajustar o reconhecimento de um idioma, atualize `PHONEMES`, `VOGAIS_B` ou `alignment_to_lip_shapes()` conforme o comportamento necessário. O código contém comentários para explicar o uso de cada variável.
