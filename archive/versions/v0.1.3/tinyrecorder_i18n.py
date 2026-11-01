"""
Tiny Recorder — English / Portuguese text (v0.1.3). English is written in the code; this file holds the Portuguese
for every _("…") string. tests/test_i18n.py checks that no string is missing and that the {names} match.
"""

LANG = "en"


def set_lang(lang):
    global LANG
    LANG = lang if lang in ("en", "pt") else "en"


def _(text):
    if LANG == "pt":
        return PT.get(text, text)
    return text


PT = {
    "About": "Sobre",
    "About Tiny Recorder": "Sobre o Tiny Recorder",
    "Tiny Recorder records everything the computer plays and everything you say into one MP3 file. No AI, no cloud, no transcription.":
        "O Tiny Recorder grava tudo o que o computador toca e tudo o que você fala em um único arquivo MP3. Sem IA, sem nuvem, sem transcrição.",
    "Version": "Versão",
    "Authors": "Autores",
    "Contact": "Contato",
    "Settings folder": "Pasta de configurações",
    "Recordings folder": "Pasta das gravações",
    "Open": "Abrir",
    "Close": "Fechar",
    "Responsible use": "Uso responsável",
    "Be nice and tell the people in a meeting that you are recording. In many countries, recording a conversation without the consent of the other participants can be a criminal offence. Don't distribute the recording, it should stay on your PC.":
        "Seja gentil e avise as pessoas de uma reunião que você está gravando. Em muitos países, gravar uma conversa sem o consentimento dos outros participantes pode ser crime. Não distribua a gravação: ela deve ficar no seu PC.",
    "Record": "Gravar",
    "Pause": "Pausar",
    "Resume": "Continuar",
    "Stop": "Parar",
    "Ready": "Pronto",
    "Starting…": "Iniciando…",
    "Recording": "Gravando",
    "Paused": "Pausado",
    "Saving…": "Salvando…",
    "REC": "GRAV",
    "PAUSED": "PAUSADO",
    "Computer audio": "Áudio do computador",
    "Microphone": "Microfone",
    "What you hear": "O que você ouve",
    "What you say": "O que você fala",
    "About this recording": "Sobre esta gravação",
    "Date": "Data",
    "Today": "Hoje",
    "Title": "Título",
    "People": "Pessoas",
    "Project": "Projeto",
    "Notes": "Notas",
    "Will be saved as": "Será salvo como",
    "Recordings": "Gravações",
    "Time": "Duração",
    "Size": "Tamanho",
    "Play": "Ouvir",
    "Delete…": "Excluir…",
    "Move this recording to the Recycle Bin?": "Mover esta gravação para a Lixeira?",
    "Moved to the Recycle Bin: {name}": "Movido para a Lixeira: {name}",
    "Could not move the file to the Recycle Bin.": "Não foi possível mover o arquivo para a Lixeira.",
    "Bugs & ideas": "Erros e ideias",
    "GitHub issues": "Issues no GitHub",
    "Licence": "Licença",
    "Third-party notices": "Avisos de terceiros",
    "Off: {what}": "Desligado: {what}",
    "Both sources are off: only silence is being recorded.": "As duas fontes estão desligadas: só silêncio está sendo gravado.",
    "Open with the default player": "Abrir no player padrão",
    "Playing: {title}": "Tocando: {title}",
    "Could not play this file: {err}": "Não foi possível tocar este arquivo: {err}",
    "Show in folder": "Mostrar na pasta",
    "Edit details and rename…": "Editar detalhes e renomear…",
    "Copy file path": "Copiar caminho do arquivo",
    "Open folder": "Abrir pasta",
    "Settings…": "Configurações…",
    "Help": "Ajuda",
    "Settings": "Configurações",
    "Output folder": "Pasta de saída",
    "Browse…": "Procurar…",
    "Quality": "Qualidade",
    "Voice: mono, 64 kbps (about 29 MB per hour)": "Voz: mono, 64 kbps (cerca de 29 MB por hora)",
    "Standard: stereo, 128 kbps (about 58 MB per hour)": "Padrão: estéreo, 128 kbps (cerca de 58 MB por hora)",
    "High: stereo, 192 kbps (about 86 MB per hour)": "Alta: estéreo, 192 kbps (cerca de 86 MB por hora)",
    "Computer audio device": "Dispositivo do áudio do computador",
    "Microphone device": "Dispositivo do microfone",
    "Follow the Windows default": "Seguir o padrão do Windows",
    "Volume of the computer audio": "Volume do áudio do computador",
    "Volume of the microphone": "Volume do microfone",
    "Start and stop from any program with Ctrl+Alt+R": "Iniciar e parar de qualquer programa com Ctrl+Alt+R",
    "Language": "Idioma",
    "English": "English",
    "Português": "Português",
    "Save": "Salvar",
    "Cancel": "Cancelar",
    "Edit details": "Editar detalhes",
    "Choose the recordings folder": "Escolha a pasta das gravações",
    "Date must look like 2026-10-20 (or 20.10.2026).": "A data deve ser como 2026-10-20 (ou 20.10.2026).",
    "Tick Computer audio, Microphone or both before you record.":
        "Marque Áudio do computador, Microfone ou os dois antes de gravar.",
    "Could not start the recording": "Não foi possível iniciar a gravação",
    "Recording stopped because of an error": "A gravação parou por causa de um erro",
    "The disk is almost full. The recording was stopped and saved.":
        "O disco está quase cheio. A gravação foi parada e salva.",
    "Not enough free space in the recordings folder.": "Pouco espaço livre na pasta das gravações.",
    "Could not read the audio devices.": "Não foi possível ler os dispositivos de áudio.",
    "Not available: {what}": "Indisponível: {what}",
    "Recording from {sources} at {rate} Hz": "Gravando de {sources} a {rate} Hz",
    "Saved: {name}": "Salvo: {name}",
    "Saved: {name} (tags not written: {err})": "Salvo: {name} (tags não gravadas: {err})",
    "A recording is in progress. Stop and save it before closing?":
        "Há uma gravação em andamento. Parar e salvar antes de fechar?",
    "Unfinished recordings": "Gravações não concluídas",
    "Found {n} unfinished recording(s) in the recordings folder (the program or the PC stopped during a recording). Recover them now?":
        "Encontrei {n} gravação(ões) não concluída(s) na pasta das gravações (o programa ou o PC parou durante uma gravação). Recuperar agora?",
    "Recovered recording": "Gravação recuperada",
    "Recovered {n} recording(s).": "{n} gravação(ões) recuperada(s).",
    "Could not rename the file (is it open in a player?): {err}":
        "Não foi possível renomear o arquivo (está aberto em um player?): {err}",
    "Copied to the clipboard.": "Copiado para a área de transferência.",
    "Ctrl+Alt+R is used by another program, so the global hotkey is off.":
        "Ctrl+Alt+R é usado por outro programa; o atalho global está desligado.",
    "Help — Tiny Recorder": "Ajuda — Tiny Recorder",
    "Tiny Recorder": "Tiny Recorder",
}
