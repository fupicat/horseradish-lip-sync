import os
import sys
# O MFA tenta executar a CLI do sqlite3, então precisamos adicionar ele ao PATH.
if getattr(sys, "frozen", False):
    bundle_dir = sys._MEIPASS # type: ignore
else:
    bundle_dir = os.path.dirname(
        os.path.abspath(__file__)
    )
os.environ["PATH"] = (
    bundle_dir
    + os.pathsep
    + os.environ.get("PATH", "")
)

from multiprocessing import freeze_support
from contextlib import redirect_stdout, redirect_stderr
from shutil import copy
from tempfile import TemporaryDirectory
from json import load as json_load, dumps as json_dumps
from argparse import ArgumentParser
from pathlib import Path
from traceback import format_exc
from typing import TYPE_CHECKING

if TYPE_CHECKING:
  from faster_whisper import WhisperModel

VERSION = "v0.0.4"

# Fonemas que representam cada formato de boca
PHONEMES = {
  "A": "b bʲ m m̩ mʲ p pʰ pʲ pʷ",
  # qlq fonema não reconhecido é classificado como B, então n precisa colocar uma lista extensa aqui
  "B": "c cʰ cʷ ç d d̪ dʒ dʲ k n s t tʰ tʲ tʷ t̪ tʃ x z ɟ ɟʷ ɡ ɡʷ ɲ ŋ ɾ ʃ ʒ i ĩ ɨ j j̃ ð ɫ ʎ θ",
  "C": "e ẽ ej eː ɛ ɛː ɪ ɝ ɚ ə əw",
  "D": "ɑ ɑː a ɐ ɐ̃ aj aw aː æ ɜ ɜː",
  "E": "o õ ow oː ɔ ɔj ɒ ɒː",
  "F": "u ũ uː ʉ ʉː w w̃ ʊ ʋ ɹ",
  "G": "f v vʲ fʲ",
  "H": "l ʎ",
}

# Pode acontecer de ocorrerem várias vogais e consoantes uma depois da outra que tem o formato de boca B.
# Se uma vogal B estiver rodeada por consoantes Bs, trocamos ela por C.
VOGAIS_B = "i ĩ ɨ j j̃".split(" ")

# Converte para Preston Blair
PRESTON_BLAIR = {
  "A": "MBP",
  "A-trans": "MBP-trans",
  "B": "etc",
  "B-trans": "etc-trans",
  "C": "E",
  "C-trans": "E-trans",
  "D": "AI",
  "D-trans": "AI-trans",
  "E": "O",
  "E-trans": "O-trans",
  "F": "U",
  "F-trans": "U-trans",
  "G": "FV",
  "G-trans": "FV-trans",
  "H": "L",
  "H-trans": "L-trans",
  "X": "rest",
  "X-trans": "rest-trans",
}

# Language code => (acoustic, dictionary, g2p)
# 40 idiomas suportados no total, 21 idiomas com modelos g2p para palavras fora do dicionário
# Modelos g2p não são obrigatórios, mas se não tiver, vai ficar uns gaps vazios no lip sync
# muitos idiomas comuns, como o árabe e hindi, não tem modelos acústicos, então infelizmente não podem ser usados
MFA_MODELS = {
  "ab": ("abkhaz_cv", "abkhaz_cv", None),
  "hy": ("armenian_cv", "armenian_cv", None),
  "ba": ("bashkir_cv", "bashkir_cv", None),
  "eu": ("basque_cv", "basque_cv", None),
  "be": ("belarusian_cv", "belarusian_cv", None),
  "bg": ("bulgarian_mfa", "bulgarian_mfa", "bulgarian_mfa"),
  "cv": ("chuvash_cv", "chuvash_cv", None),
  "hr": ("croatian_mfa", "croatian_mfa", "croatian_mfa"),
  "cs": ("czech_mfa", "czech_mfa", "czech_mfa"),
  "nl": ("dutch_cv", "dutch_cv", None),
  "en": ("english_mfa", "english_mfa", "english_us_mfa"),
  "fr": ("french_mfa", "french_mfa", "french_mfa"),
  "ka": ("georgian_cv", "georgian_cv", None),
  "de": ("german_mfa", "german_mfa", "german_mfa"),
  "el": ("greek_cv", "greek_cv", None),
  "gn": ("guarani_cv", "guarani_cv", None),
  "ha": ("hausa_mfa", "hausa_mfa", "hausa_mfa"),
  "hu": ("hungarian_cv", "hungarian_cv", None),
  "it": ("italian_cv", "italian_cv", None),
  "ja": ("japanese_mfa", "japanese_mfa", "japanese_mfa"),
  "kk": ("kazakh_cv", "kazakh_cv", None),
  "ko": ("korean_mfa", "korean_mfa", "korean_mfa"),
  "ku": ("kurmanji_cv", "kurmanji_cv", None),
  "ky": ("kyrgyz_cv", "kyrgyz_cv", None),
  "zh": ("mandarin_mfa", "mandarin_mfa", "mandarin_china_mfa"),
  "pl": ("polish_mfa", "polish_mfa", "polish_mfa"),
  "pt": ("portuguese_mfa", "portuguese_mfa", "portuguese_brazil_mfa"),
  "ro": ("romanian_cv", "romanian_cv", None),
  "ru": ("russian_mfa", "russian_mfa", "russian_mfa"),
  "es": ("spanish_mfa", "spanish_mfa", "spanish_latin_america_mfa"),
  "sw": ("swahili_mfa", "swahili_mfa", "swahili_mfa"),
  "sv": ("swedish_mfa", "swedish_mfa", "swedish_mfa"),
  "ta": ("tamil_cv", "tamil_mfa", "tamil_mfa"),
  "tt": ("tatar_cv", "tatar_cv", None),
  "th": ("thai_mfa", "thai_mfa", "thai_mfa"),
  "tr": ("turkish_mfa", "turkish_mfa", "turkish_mfa"),
  "uk": ("ukrainian_mfa", "ukrainian_mfa", "ukrainian_mfa"),
  "ug": ("uyghur_cv", "uyghur_cv", None),
  "uz": ("uzbek_cv", "uzbek_cv", None),
  "vi": ("vietnamese_mfa", "vietnamese_mfa", "vietnamese_hanoi_mfa"),
}


def load_whisper(model_size = "turbo") -> "WhisperModel":
  from faster_whisper import WhisperModel

  return WhisperModel(model_size, device="auto")

def detect_language(model: "WhisperModel", audio_path: Path) -> str:
  from faster_whisper import decode_audio

  audio = decode_audio(str(audio_path.resolve()))
  language, _, _ = model.detect_language(audio) # type: ignore
  return language

def transcribe(model: "WhisperModel", audio_path: Path, language: str) -> str:
  segments, _ = model.transcribe(str(audio_path.resolve()), language)

  transcription = ""

  for segment in segments:
    transcription += segment.text

  return transcription.strip()


def get_mfa_model_paths(language: str) -> tuple[Path, Path, Path | None]:
  from montreal_forced_aligner.models import AcousticModel, DictionaryModel, G2PModel, ModelManager

  model_manager = ModelManager()
  
  # Acquire models
  if not language in MFA_MODELS:
    raise Exception(f"Language {language} is not supported.")
  
  acoustic_name, dictionary_name, g2p_name = MFA_MODELS[language]

  with open(os.devnull, 'w') as devnull_var, redirect_stdout(devnull_var), redirect_stderr(devnull_var):
    acoustic_path = AcousticModel.get_pretrained_path(acoustic_name)
    if not acoustic_path:
      model_manager.download_model("acoustic", acoustic_name)
      acoustic_path = AcousticModel.get_pretrained_path(acoustic_name)
      
    dictionary_path = DictionaryModel.get_pretrained_path(dictionary_name)
    if not dictionary_path:
      model_manager.download_model("dictionary", dictionary_name)
      dictionary_path = DictionaryModel.get_pretrained_path(dictionary_name)

    g2p_path = None
    if g2p_name:
      g2p_path = G2PModel.get_pretrained_path(g2p_name)
      if not g2p_path:
        model_manager.download_model("g2p", g2p_name)
        g2p_path = G2PModel.get_pretrained_path(g2p_name)

  if acoustic_path is None:
    raise Exception(f"Failed to load acoustic model {acoustic_name}.")
  if dictionary_path is None:
    raise Exception(f"Failed to load dictionary {dictionary_name}.")
  if g2p_path is None and not g2p_name is None:
    raise Exception(f"Failed to load g2p model {g2p_name}.")

  return (acoustic_path, dictionary_path, g2p_path)

def generate_pronunciations(corpus_dir: str, output_dir: str, dictionary_path: Path, g2p_path: Path):
  from montreal_forced_aligner.models import DictionaryModel, G2PModel
  from montreal_forced_aligner.g2p.generator import PyniniDictionaryCorpusGenerator
  from montreal_forced_aligner.dictionary.multispeaker import MultispeakerDictionary
  from montreal_forced_aligner.exceptions import PhoneMismatchError

  with open(os.devnull, 'w') as devnull_var, redirect_stdout(devnull_var), redirect_stderr(devnull_var):
    dictionary_model = DictionaryModel(dictionary_path)
    g2p_model = G2PModel(g2p_path)
    g2p = PyniniDictionaryCorpusGenerator(
      corpus_directory=corpus_dir,
      dictionary=dictionary_model,
      g2p_model=g2p_model,
      **PyniniDictionaryCorpusGenerator.parse_parameters(),
    )
    g2p.setup()
    g2p.export_pronunciations(os.path.join(output_dir, "audio.oov"))
    base_dictionary = MultispeakerDictionary(dictionary=dictionary_model)
    base_dictionary.dictionary_setup()
    new_pronunciations = MultispeakerDictionary(dictionary=DictionaryModel(os.path.join(output_dir, "audio.oov")))
    new_pronunciations.dictionary_setup()
    new_phones = set()
    for phone in new_pronunciations.non_silence_phones:
      if phone not in base_dictionary.non_silence_phones:
        new_phones.add(phone)
    if new_phones:
      raise PhoneMismatchError(new_phones)

    new_words = new_pronunciations.words_for_export(probability=True)
    base_dictionary.add_words(new_words)
    base_dictionary.export_lexicon(
      base_dictionary._default_dictionary_id, # type: ignore
      base_dictionary.dictionary_model.path,
      probability=True,
    )
    new_pronunciations.cleanup_connections()
    base_dictionary.cleanup_connections()
    g2p.cleanup_connections()

def align(corpus_dir: str, output_dir: str, acoustic_path: Path, dictionary_path: Path) -> dict:
  from montreal_forced_aligner.alignment import PretrainedAligner

  with open(os.devnull, 'w') as devnull_var, redirect_stdout(devnull_var), redirect_stderr(devnull_var):
    aligner = PretrainedAligner(
      corpus_directory=corpus_dir,
      dictionary_path=dictionary_path,
      acoustic_model_path=acoustic_path,
    )
    aligner.setup()
    aligner.align()
    aligner.export_files(output_dir, 'json')
    aligner.cleanup_connections()

  analysis = json_load(open(os.path.join(output_dir, 'audio.json'), 'r', encoding='utf-8'))

  return analysis


def alignment_to_lip_shapes(alignment: dict, extended_shapes = "GHX") -> list[tuple[float, str]]:
  shape_map = {}
  
  for shape, phonemes in PHONEMES.items():
    for phoneme in phonemes.split(" "):
      shape_map[phoneme] = shape
      if shape in "GHX" and not shape in extended_shapes:
        shape_map[phoneme] = "B"

  phone_entries = alignment["tiers"]["phones"]["entries"]
  lip_timeline = []
  last_shape = ""
  last_phoneme_end_timestamp = 0.0
  i = 0
  for entry in phone_entries:
    start_time = entry[0]
    end_time = entry[1]
    phoneme = entry[2]

    # Insert rests where no phoneme is being said
    if start_time - last_phoneme_end_timestamp > 0.2:
      lip_timeline.append((last_phoneme_end_timestamp, "X" if "X" in extended_shapes else "A"))

    shape = shape_map.get(phoneme, "B")  # Default to "B" if phoneme not found.
    if shape == "B" and phoneme in VOGAIS_B:
      next_shape = shape_map.get(phone_entries[i + 1][2], "B") if i < len(phone_entries) - 1 else ""
      if last_shape == "B" or next_shape == "B":
        shape = "C"
    lip_timeline.append((start_time, shape))

    # Por algum motivo o MFA classifica ditongos vocálicos em inglês como um fonema só. Então aqui eu separo entre o primeiro e o segundo som.
    if shape != "w" and shape.endswith("w"):
      lip_timeline.append(((start_time + end_time) / 2, shape_map.get("w", "F")))
    
    last_phoneme_end_timestamp = end_time
    last_shape = shape
    i += 1
  
  lip_timeline.append((last_phoneme_end_timestamp, "X" if "X" in extended_shapes else "A"))

  return lip_timeline

# Transforma uma lista de timings de bocas em uma lista de frames de bocas.
# Formatos de boca entre frames são descartados, e aqui também adiciona variação em frames repetidos.
# O primeiro valor da tuple é o frame, o segundo é o segundo em que o frame começa (para formatos que não são baseados em frames), e o terceiro é o formato da boca.
# Nesse meu sistema, todos os tipos de output passam por esse passo de reframe, para melhorar a animação.
def reframe_lip_shapes(lip_timings: list[tuple[float, str]], framerate: float, exposure: int) -> list[tuple[int, float, str]]:
  output_list = []
  secs_per_frame = (1.0 / framerate)
  current_frame = 1
  last_written_shape = ''
  shapes_in_this_frame = ["X"]
  current_lip_index = 0
  while current_lip_index < len(lip_timings):
    time, lip = lip_timings[current_lip_index]
    if time < current_frame * secs_per_frame:
      shapes_in_this_frame.append(lip)
      current_lip_index += 1
      continue
    output_shape = shapes_in_this_frame[-1]
    # Só adicionar rests se nenhum outro shape estiver presente neste frame.
    if len(shapes_in_this_frame) > 1 and output_shape == "X":
      output_shape = shapes_in_this_frame[-2]
    # Se o frame atual tiver um plosivo MBP, e o frame anterior já não for um plosivo, dá prioridade para ele
    # Eu faço isso porque como plosivos são muito curtinhos, eles quase sempre acabam ficando entre frames e ficam perdidos.
    if "A" in shapes_in_this_frame and last_written_shape != "A":
      output_shape = "A"
    # Mesma coisa para a consoante FV
    if "G" in shapes_in_this_frame and last_written_shape != "G":
      output_shape = "G"
    # Mesma coisa para a consoante L
    if "H" in shapes_in_this_frame and last_written_shape != "H":
      output_shape = "H"
    # Não repete keyframes um depois do outro
    if output_shape == last_written_shape:
      current_frame += 1
      shapes_in_this_frame = [shapes_in_this_frame[-1]]
      continue
    output_list.append((current_frame, (current_frame - 1) * secs_per_frame, output_shape))
    last_written_shape = output_shape
    current_frame += exposure
    shapes_in_this_frame = [shapes_in_this_frame[-1]]
  
  if shapes_in_this_frame[-1] != last_written_shape:
    output_list.append((current_frame, (current_frame - 1) * secs_per_frame, shapes_in_this_frame[-1]))

  # Adianta keyframes A e G por 1 frame, se estiver animando on ones.
  if exposure == 1:
    remove_these = []
    for i in range(len(output_list)):
      if i == 0:
        continue
      frame, time, shape = output_list[i]
      if shape in "AG":
        prev_frame, _, _ = output_list[i-1]
        if prev_frame == frame - 1:
          remove_these.append(output_list[i-1])
        output_list[i] = (frame - 1, time - secs_per_frame, shape)
    for removable in remove_these:
      output_list.remove(removable)
  # Se estiver animando on twos ou mais, o algoritmo de reframe já adianta as keyframes, não precisa de passos adicionais.

  return output_list

# Adiciona frames de transição.
# Frames de transição são representados pelo nome do formato de boca, com "-trans" adicionado no final da string.
# Cada formato de boca tem um único frame de transição, utilizado tanto para começar quanto para terminar um estado da boca.
def add_transition_frames(lip_frames: list[tuple[int, float, str]], framerate: float) -> list[tuple[int, float, str]]:
  output_list = []
  secs_per_frame = (1.0 / framerate)

  for i in range(len(lip_frames)):
    current_entry = lip_frames[i]
    (current_frame, current_time, current_lip) = current_entry

    # Trata último frame
    if i >= len(lip_frames) - 1:
      output_list.append((current_frame, current_time, current_lip + "-trans"))
      output_list.append((current_frame + 1, current_time + secs_per_frame, current_lip))
      break

    next_entry = lip_frames[i + 1]
    (next_frame, next_time, next_lip) = next_entry

    frames_in_between = next_frame - current_frame - 1

    if frames_in_between < 1:
      # Nenhum frame vazio entre duas keyframes? Só mantém a keyframe original.
      output_list.append(current_entry)
    elif frames_in_between == 1:
      # Só um frame vazio? Adiciona a transição após o keyframe atual
      output_list.append(current_entry)
      output_list.append((current_frame + 1, current_time + secs_per_frame, current_lip + "-trans"))
    else:
      # Dois ou mais frames vazios?
      # Comportamento padrão: Entra em um estado de "hold", com um frame de transição pra abrir, e um pra fechar.
      # Comportamento especial para A (MBP): Não se coloca transição de entrada, para não parecer que a boca tá tremendo, já que os holds tendem a ser bem curtos.
      # Comportamento especial ao transicionar de um X (rest) para um A (MBP): Não se coloca transição de saída, já que os desenhos para X e A tendem a ser os mesmos, ou muito parecidos, então pode parecer que a boca tá tremendo.
      if current_lip == "A":
        output_list.append(current_entry)
      else:
        # Não se faz transição de entrada se o primeiro frame for um X (rest), porque assume-se que a boca já está fechada.
        if i == 0 and current_lip == "X":
          output_list.append(current_entry)
        else:
          output_list.append((current_frame, current_time, current_lip + "-trans"))
          output_list.append((current_frame + 1, current_time + secs_per_frame, current_lip))
      if not (current_lip == "X" and next_lip == "A"):
        output_list.append((next_frame - 1, next_time - secs_per_frame, current_lip + "-trans"))
      
  return output_list


def main():
  parser = ArgumentParser(description="Horseradish Lip Sync allows you to quickly create 2D mouth animation from voice recordings. It analyzes your audio files, recognizes what is being said, then automatically generates lip sync information. You can use it for animating speech in computer games, animated cartoons, or any similar project.")
  parser.add_argument("inputFile", type=str, nargs="?", default="", help="The audio file to be analyzed. This must be the last command-line argument. Supported file formats are WAVE (.wav) and Ogg Vorbis (.ogg).")
  parser.add_argument("-r", "--recognizer", type=str, default="mfa", help="Specifies how Horseradish Lip Sync recognizes speech within the recording. Right now, it does nothing. Preserved for compatibility with Rhubarb Lip Sync. The only valid option is \"mfa\" (Montreal Forced Aligner).")
  parser.add_argument("-f", "--exportFormat", type=str, default="tsv", help="The export format. Options: tsv (tab-separated values, see details), xml (see details), json (see details), dat (see Moho and OpenToonz).")
  parser.add_argument("-d", "--dialogFile", type=str, help="With this option, you can provide Horseradish Lip Sync with the dialog text to get more reliable results. Specify the path to a plain-text file (in ASCII or UTF-8 format) containing the dialog contained in the audio file. Horseradish Lip Sync will still perform word recognition internally, but it will prefer words and phrases that occur in the dialog file. This leads to better recognition results and thus more reliable animation.")
  parser.add_argument("--extendedShapes", type=str, default="GHX", help='As described in Mouth shapes, Horseradish Lip Sync uses six basic mouth shapes and up to three extended mouth shapes, which are optional. Use this option to specify which extended mouth shapes should be used. For example, to use only the G and X extended mouth shapes, specify GX; to use only the six basic mouth shapes, specify an empty string: "".')
  parser.add_argument("-o", "--output", type=str, help="The name of the output file to create. If the file already exists, it will be overwritten. If you don't specify an output file, the result will be written to stdout.")
  parser.add_argument("--version", action='store_true', help="Displays version information and exits.")
  parser.add_argument("--datFrameRate", type=int, help="LEGACY. USE --frameRate INSTEAD. Only valid when using the dat export format. Controls the frame rate for the output file.")
  parser.add_argument("--datUsePrestonBlair", action='store_true', help="Uses Preston Blair mouth shapes names instead of the default alphabetical ones.")
  parser.add_argument("--outputAnalysis", type=str, help="Name of the file to save the MFA phoneme breakdown, for debug purposes.")
  parser.add_argument("--frameRate", type=int, default=24, help="Controls the frame rate for the output file.")
  parser.add_argument("--exposureDuration", type=int, default=2, help="Number of frames minimum for the keyframes to be exposed. 1 = Animation on ones, 2 = animation on twos, etc.")
  parser.add_argument("--useTransitionFrames", action='store_true', help="Adds transition frames between keyframes, labeled with '-trans' at the end. Note that transition frames ignore exposure, they are always animated on ones.")
  parser.add_argument("--machineReadable", action='store_true', help="This option is useful if you want to integrate Rhubarb Lip Sync with another (possibly graphical) application. All status messages to stderr will be in structured JSON format, allowing your program to parse them and display a graphical progress bar or something similar.")

  args = parser.parse_args()

  if args.version:
    print("Horseradish Lip Sync version " + VERSION)
    sys.exit(0)

  if not args.inputFile:
    print("Error: No input file specified. Use the --help option for usage information.", file=sys.stderr)
    sys.exit(1)

  machine_readable = args.machineReadable

  if machine_readable:
    print(f'{{ "type": "start", "file": {json_dumps(args.inputFile)}, "log": {{ "level": "Info", "message": "Application startup. Input file: {json_dumps(args.inputFile).replace('"', '\\"')}." }} }}', file=sys.stderr)

  try:
    audio_path = Path(args.inputFile)
    input_text = ""
    if machine_readable:
      print('{ "type": "progress", "value": 0.00, "log": { "level": "Trace", "message": "Progress: 0%" } }', file=sys.stderr)
    
    model = load_whisper()
    language = detect_language(model, audio_path)
    if machine_readable:
      print('{ "type": "progress", "value": 0.02, "log": { "level": "Trace", "message": "Progress: 2%" } }', file=sys.stderr)
    
    if args.dialogFile:
      input_text = open(Path(args.dialogFile), "r").read()
    else:
      input_text = transcribe(model, audio_path, language)
    if machine_readable:
      print('{ "type": "progress", "value": 0.40, "log": { "level": "Trace", "message": "Progress: 40%" } }', file=sys.stderr)

    acoustic_path, dictionary_path, g2p_path = get_mfa_model_paths(language)
    with TemporaryDirectory() as corpus_dir, TemporaryDirectory() as output_dir:
      copy(audio_path, os.path.join(corpus_dir, "audio.wav"))
      open(os.path.join(corpus_dir, "audio.txt"), "w", encoding="utf-8").write(input_text)

      if g2p_path:
        generate_pronunciations(corpus_dir, output_dir, dictionary_path, g2p_path)
      if machine_readable:
        print('{ "type": "progress", "value": 0.70, "log": { "level": "Trace", "message": "Progress: 70%" } }', file=sys.stderr)

      alignment = align(corpus_dir, output_dir, acoustic_path, dictionary_path)
      if machine_readable:
        print('{ "type": "progress", "value": 0.90, "log": { "level": "Trace", "message": "Progress: 90%" } }', file=sys.stderr)
  
    if args.outputAnalysis:
      open(args.outputAnalysis, 'w', encoding="utf-8").write(json_dumps(alignment, ensure_ascii=False))
  
    lip_timings = alignment_to_lip_shapes(alignment, args.extendedShapes)
  
    framerate = abs(args.datFrameRate) if not (args.datFrameRate is None) else abs(args.frameRate)
  
    lip_frames = reframe_lip_shapes(lip_timings, framerate, max(abs(args.exposureDuration), 1))
    if (args.useTransitionFrames):
      lip_frames = add_transition_frames(lip_frames, framerate)
    if machine_readable:
      print('{ "type": "progress", "value": 0.95, "log": { "level": "Trace", "message": "Progress: 95%" } }', file=sys.stderr)
  
    output_string = ""
  
    match args.exportFormat:
      case "tsv":
        for (_, time, lip) in lip_frames:
          output_string += f'{time:.2f}\t{lip}\n'
        # O último item é sempre uma boca fechada no final da gravação.
        output_string += f'{alignment["end"]:.2f}\tX\n'
      case "xml":
        output_string += '<?xml version="1.0" encoding="utf-8"?>\n'
        output_string += '<rhubarbResult>\n'
        output_string += '  <metadata>\n'
        output_string += f'    <soundFile>{audio_path.resolve()}</soundFile>\n'
        output_string += f'    <duration>{alignment["end"]:.2f}</duration>\n'
        output_string += '  </metadata>\n'
        output_string += '  <mouthCues>\n'
        i = 0
        for (_, time, lip) in lip_frames:
          output_string += f'    <mouthCue start="{time:.2f}" end="{(alignment["end"] if (i == len(lip_frames) - 1) else lip_frames[i + 1][1]):.2f}">{lip}</mouthCue>\n'
          i += 1
        output_string += '  </mouthCues>\n'
        output_string += '</rhubarbResult>\n'
      case "json":
        output_string += '{\n'
        output_string += '  "metadata": {\n'
        output_string += f'    "soundFile": "{str(audio_path.resolve()).replace("\\", "\\\\")}",\n'
        output_string += f'    "duration": {alignment["end"]:.2f}\n'
        output_string += '  },\n'
        output_string += '  "mouthCues": [\n'
        i = 0
        for (_, time, lip) in lip_frames:
          output_string += f'    {{ "start": {time:.2f}, "end": {(alignment["end"] if (i == len(lip_frames) - 1) else lip_frames[i + 1][1]):.2f}, "value": "{lip}" }}{"," if (i < len(lip_frames) - 1) else ""}\n'
          i += 1
        output_string += '  ]\n'
        output_string += '}\n'
      case "dat":
        output_string = 'MohoSwitch1\n'
        for (frame, _, lip) in lip_frames:
          output_string += f'{frame} {PRESTON_BLAIR[lip] if args.datUsePrestonBlair else lip}\n'
      case _:
        raise Exception(f"Output format \"{args.exportFormat}\" not supported.")
  
    if machine_readable:
      print('{ "type": "progress", "value": 1.00, "log": { "level": "Trace", "message": "Progress: 100%" } }', file=sys.stderr)

    if args.output:
      with open(args.output, "w", encoding="utf-8") as f:
        f.write(output_string)
    else:
      print(output_string)
    if machine_readable:
      print('{ "type": "success", "log": { "level": "Info", "message": "Application terminating normally." } }', file=sys.stderr)
  except Exception as e:
    if machine_readable:
      print(format_exc())
      print(f'{{ "type": "failure", "reason": "{e}", "log": {{ "level": "Fatal", "message": "Application terminating with error: {e}" }} }}', file=sys.stderr)


if __name__ == '__main__':
  freeze_support()
  main()