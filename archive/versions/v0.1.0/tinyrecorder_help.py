"""Tiny Recorder — the Help window text (v0.1.0), English and Portuguese. Lines in **…** are shown bold."""

EN = [
    ("Quick start", """
1. Open Tiny Recorder before the meeting. Leave **Computer audio** and **Microphone** ticked.
2. Press ● Record (or Ctrl+Alt+R from any program). The first start can take a few seconds: Windows opens the headset.
3. Join your Teams, Zoom or Meet call as usual. Everything you hear and everything you say goes into one MP3 file.
4. While recording, fill in **Title**, **People** and the other details (or later, from the list).
5. Press ■ Stop. The file is tagged and renamed to **date - Title.mp3** and appears in the list.

Nothing is sent anywhere: no AI, no transcription, no cloud.
"""),
    ("Tags and file names", """
**What is stored in the MP3 file (ID3 tags)**
- Date → the Date tag (and the first part of the file name)
- Title → the Title tag (and the second part of the file name)
- People → the Artist tag
- Project → the Album tag
- Notes → the Comment tag

**File name**
**YYYY-MM-DD - Title.mp3**, for example 2026-10-20 - Budget review.mp3. Characters Windows does not allow in file names
(: / \\ ? * " < > |) are replaced by spaces in the name; the Title tag keeps your text exactly as typed.
Without a title the name is "date - Untitled.mp3". If the name is taken, (2), (3)… is added.

**Changing a recording later**
Right-click it in the list → **Edit details and rename…**. The tags are rewritten and the file is renamed to match.
"""),
    ("Quality and size", """
Settings → Quality:
- **Voice**: mono, 64 kbps. Clear speech, about 29 MB per hour. The default.
- **Standard**: stereo, 128 kbps, about 58 MB per hour.
- **High**: stereo, 192 kbps, about 86 MB per hour.

The sound of the computer and your microphone are always mixed into the same file. The volume of each can be set in
Settings (0 to 200 %), so a quiet microphone can be raised.
"""),
    ("Devices and headsets", """
**Computer audio** is what the chosen output device plays (loopback). By default Tiny Recorder follows the Windows
default output at the moment you press Record. If you move the call to another device during a recording, stop and
record again, or choose that device in Settings.

**Microphone** follows the Windows default microphone, or the one you choose.

**Bluetooth headsets** switch to a low-quality "hands-free" mode when their microphone is used; the meeting program does
that, not Tiny Recorder. Recording still works; the sound quality is the one the headset gives.

If one of the two cannot be opened (for example a blocked microphone) the other is recorded and a warning is shown.
"""),
    ("Hotkey", """
**Ctrl+Alt+R** starts and stops the recording from any program, so you do not need to switch windows during a call.
The window title shows ● REC and the elapsed time, so the taskbar tells you when it is recording.
If another program already uses Ctrl+Alt+R, Tiny Recorder says so and the hotkey stays off. Turn it off in Settings.
"""),
    ("Recovery", """
While recording, the MP3 file is written continuously (a temporary file ending in .mp3.part). If the program or the PC
stops during a recording, nothing is lost: the next time Tiny Recorder starts it finds the unfinished file and offers to
recover it as "date - Recovered recording.mp3".

The recording also stops by itself, and is saved, when the disk has almost no free space.
"""),
    ("If something goes wrong", """
**The microphone level stays at zero.** Check that the microphone is not muted (headset button, Windows) and that
Windows allows desktop apps to use it: Settings → Privacy & security → Microphone.

**The computer-audio level stays at zero.** Nothing is playing, or the meeting uses another output device than the one
shown in the status line. Choose the right device in Settings → Computer audio device.

**The first Record takes a few seconds.** Bluetooth headsets and some antivirus programs open audio devices slowly.
The window shows "Starting…".

**The file cannot be renamed.** A player or a sync program has it open. Close it and try again.
"""),
    ("Files and privacy", """
Recordings are saved in the folder shown at the bottom of the window (Settings → Output folder). Settings are kept in
%APPDATA%\\TinyRecorder. Nothing else is written, and nothing is sent anywhere.

**Responsible use.** Tell the people in a meeting that you are recording. In many countries, including Switzerland,
recording a conversation without the consent of the other participants can be a criminal offence, even when you take
part in it. Teams and Zoom announce their own recordings; Tiny Recorder does not announce anything to the others.
This text is not legal advice.
"""),
]

PT = [
    ("Primeiros passos", """
1. Abra o Tiny Recorder antes da reunião. Deixe **Áudio do computador** e **Microfone** marcados.
2. Pressione ● Gravar (ou Ctrl+Alt+R em qualquer programa). O primeiro início pode levar alguns segundos: o Windows abre o fone.
3. Entre na chamada do Teams, Zoom ou Meet como sempre. Tudo o que você ouve e tudo o que você fala vai para um único arquivo MP3.
4. Durante a gravação, preencha **Título**, **Pessoas** e os outros detalhes (ou depois, pela lista).
5. Pressione ■ Parar. O arquivo recebe as tags, é renomeado para **data - Título.mp3** e aparece na lista.

Nada é enviado a lugar nenhum: sem IA, sem transcrição, sem nuvem.
"""),
    ("Tags e nomes de arquivo", """
**O que fica gravado no arquivo MP3 (tags ID3)**
- Data → a tag Data (e a primeira parte do nome do arquivo)
- Título → a tag Título (e a segunda parte do nome do arquivo)
- Pessoas → a tag Artista
- Projeto → a tag Álbum
- Notas → a tag Comentário

**Nome do arquivo**
**AAAA-MM-DD - Título.mp3**, por exemplo 2026-10-20 - Revisão do orçamento.mp3. Caracteres que o Windows não aceita em
nomes de arquivo (: / \\ ? * " < > |) viram espaços no nome; a tag Título guarda o seu texto exatamente como digitado.
Sem título o nome é "data - Sem título.mp3". Se o nome já existir, é acrescentado (2), (3)…

**Mudar uma gravação depois**
Clique com o botão direito na lista → **Editar detalhes e renomear…**. As tags são regravadas e o arquivo é renomeado.
"""),
    ("Qualidade e tamanho", """
Configurações → Qualidade:
- **Voz**: mono, 64 kbps. Fala clara, cerca de 29 MB por hora. É o padrão.
- **Padrão**: estéreo, 128 kbps, cerca de 58 MB por hora.
- **Alta**: estéreo, 192 kbps, cerca de 86 MB por hora.

O som do computador e o seu microfone são sempre misturados no mesmo arquivo. O volume de cada um pode ser ajustado em
Configurações (0 a 200 %), para aumentar um microfone baixo.
"""),
    ("Dispositivos e fones", """
**Áudio do computador** é o que o dispositivo de saída escolhido toca (loopback). Por padrão o Tiny Recorder segue a saída
padrão do Windows no momento em que você pressiona Gravar. Se você mover a chamada para outro dispositivo durante a gravação,
pare e grave de novo, ou escolha esse dispositivo em Configurações.

**Microfone** segue o microfone padrão do Windows, ou o que você escolher.

**Fones Bluetooth** passam a um modo "mãos livres" de baixa qualidade quando o microfone é usado; quem faz isso é o programa
da reunião, não o Tiny Recorder. A gravação funciona; a qualidade é a que o fone oferece.

Se um dos dois não puder ser aberto (por exemplo um microfone bloqueado), o outro é gravado e um aviso aparece.
"""),
    ("Atalho global", """
**Ctrl+Alt+R** inicia e para a gravação em qualquer programa, sem trocar de janela durante a chamada.
O título da janela mostra ● GRAV e o tempo, então a barra de tarefas avisa quando está gravando.
Se outro programa já usa Ctrl+Alt+R, o Tiny Recorder avisa e o atalho fica desligado. Desligue-o em Configurações.
"""),
    ("Recuperação", """
Durante a gravação o arquivo MP3 é escrito continuamente (um arquivo temporário terminado em .mp3.part). Se o programa ou
o PC parar durante uma gravação, nada se perde: na próxima vez que o Tiny Recorder iniciar, ele encontra o arquivo
inacabado e oferece recuperá-lo como "data - Gravação recuperada.mp3".

A gravação também para sozinha, e é salva, quando o disco tem quase nenhum espaço livre.
"""),
    ("Se algo der errado", """
**O nível do microfone fica em zero.** Verifique se o microfone não está mudo (botão do fone, Windows) e se o Windows permite
que aplicativos de desktop o usem: Configurações → Privacidade e segurança → Microfone.

**O nível do áudio do computador fica em zero.** Nada está tocando, ou a reunião usa outro dispositivo de saída que não o
mostrado na linha de status. Escolha o dispositivo certo em Configurações → Dispositivo do áudio do computador.

**O primeiro Gravar demora alguns segundos.** Fones Bluetooth e alguns antivírus abrem dispositivos de áudio devagar.
A janela mostra "Iniciando…".

**Não é possível renomear o arquivo.** Um player ou programa de sincronização o mantém aberto. Feche-o e tente de novo.
"""),
    ("Arquivos e privacidade", """
As gravações são salvas na pasta mostrada na parte de baixo da janela (Configurações → Pasta de saída). As configurações
ficam em %APPDATA%\\TinyRecorder. Nada mais é escrito, e nada é enviado a lugar nenhum.

**Uso responsável.** Avise as pessoas de uma reunião que você está gravando. Em muitos países, incluindo a Suíça, gravar uma
conversa sem o consentimento dos outros participantes pode ser crime, mesmo quando você participa dela. O Teams e o Zoom
anunciam as próprias gravações; o Tiny Recorder não anuncia nada aos outros. Este texto não é aconselhamento jurídico.
"""),
]
