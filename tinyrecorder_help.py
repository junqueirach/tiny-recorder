"""Tiny Recorder — the Help window text (v0.1.4) in English, Portuguese (Brazil) and Spanish: the same sections in the
same order. Lines in **…** are shown bold."""

EN = [
    ("Quick start", """
1. Open Tiny Recorder before the meeting. Leave **Computer audio** and **Microphone** ticked.
2. Press ● Record Now (or Ctrl+Alt+R from any program). The first start can take a few seconds: Windows opens the
   headset. In a waiting room, press ◌ Start on Sound instead (see "Start on Sound and auto stop").
3. Join your Teams, Zoom or Meet call as usual. Everything you hear and everything you say goes into one MP3 file.
4. While recording, fill in **Title**, **People** and the other details (or later, from the list).
5. Press ■ Stop. The file is tagged and renamed to **date - Title.mp3** and appears in the list.

Nothing is sent anywhere: no AI, no transcription, no cloud.
"""),
    ("Start on Sound and auto stop", """
**Start on Sound** is for a call that has not started yet (a waiting room, a meeting that starts late). Press
◌ Start on Sound: the devices open and the meters move, but nothing is recorded until a ticked source (Computer audio
or Microphone) has sound. Then the recording starts by itself, with the second before the sound included. Meanwhile
the window shows "Waiting for sound…". **● Record Now** starts at once; **■ Stop** (or Ctrl+Alt+R) stops waiting and
leaves no file.

**Auto stop** (the row under the meters):
- **Stop after 5 silent minutes** (on by default): when every ticked source has been silent that long, the recording
  stops and is saved. Silent means below -40 dB; pauses do not count. Type the number you want (1.5 and 1,5 both work).
- **Stop after 60 minutes**: the recording stops when it reaches that length; the row shows the time it will stop.

Both can be changed during a recording. The line after saving says why a recording stopped.
"""),
    ("Playing recordings", """
Select a recording in the list and press **▶ Play** (or double-click it, or press Enter). **■ Stop** ends it. The line
next to the button shows what is playing and the time. When the recording ends, the button returns to Play.

- Playing uses the Windows player components: nothing else is installed or left running.
- Play is off while you record, and starting a recording stops the playback: the computer audio is what Tiny Recorder
  records, so a playing file would end up in the new recording.
- Editing the details of a recording that is playing stops it first (a playing file cannot be renamed).
- Right-click → **Open with the default player** opens the file in the program Windows uses for MP3 files instead.
- Right-click → **Delete…** (or the Delete key) moves the recording to the Recycle Bin after asking; you can restore it
  from there. A recording that is playing is stopped first. In a folder without a Recycle Bin (a network or removable
  drive) it asks before deleting the file for good.
"""),
    ("Transcribe with TranscriptLab", """
Tiny Recorder does not transcribe. **TranscriptLab**, a separate free app, does it on this PC with Whisper. Select a
recording and press **Transcribe** (or right-click → **Transcribe with TranscriptLab**): Tiny Recorder finds
TranscriptLab and hands it the file. TranscriptLab opens (or comes to the front, if it is already open) and starts the
transcription, or queues the file when it is busy.

- Nothing is sent anywhere by Tiny Recorder; TranscriptLab works on this PC too.
- Transcribe is off while you record (the file is not finished yet). A recording that is playing is stopped first.
- Tiny Recorder finds TranscriptLab by itself once TranscriptLab 0.16.9 or newer has been started once. If it is not
  found, a window offers **Locate…** (choose TranscriptLab's program) and **Get TranscriptLab** (opens its download
  page). Settings → **TranscriptLab** shows which one is used; **Clear** goes back to finding it by itself.
"""),
    ("Tags and file names", """
**What is stored in the MP3 file (ID3 tags)**
- Date → the Date tag (and the first part of the file name)
- Title → the Title tag (and the second part of the file name)
- People → the Artist tag
- Project → the Album tag
- Notes → the Comment tag
- Copyright → always "not for distribution, personal use only" (added to every recording; it cannot be changed in the
  window, and it is kept when you edit the details later)

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

**Switching a channel off during a recording.** The boxes in front of **Computer audio** and **Microphone** stay usable
while you record. Untick one and it is no longer in the MP3 (the file gets silence for it, so the timeline stays right);
tick it again and it is back at once. The line under the timer says which channel is off. A channel that was unticked when
you pressed Record is opened when you tick it, which can take a few seconds with a Bluetooth headset. The change is for
this recording only: the boxes go back to your usual choice when you stop. Untick a channel before pressing Record to
make that the usual choice.

**Warnings during a recording.** If Windows moves the sound to another device (a headset plugged in, Bluetooth
connecting) while Computer audio follows the Windows default, the line under the timer says so: stop and record again
to capture the new device. If Computer audio gives no sound at all for 3 minutes, a quiet warning asks you to check the
device; the recording goes on. A device chosen in Settings that is not there (a headset unplugged) is replaced by the
Windows default, and the line says so.
"""),
    ("Hotkey", """
**Ctrl+Alt+R** starts and stops the recording from any program, so you do not need to switch windows during a call.
**Ctrl+Alt+P** pauses and resumes it.
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
    ("Updates", """
About → **Check for updates** (or Settings → Updates) asks GitHub whether a newer Tiny Recorder exists. Nothing about
you is sent, and Tiny Recorder never checks by itself. If there is one, a window shows what is new:
- **Download and install** (the exe version): the new exe is saved next to the current one, checked against the
  release's SHA-256 checksum and started when you agree; the old exe stays in its folder.
- **Open the release page** opens it in the browser.
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
2. Pressione ● Gravar agora (ou Ctrl+Alt+R em qualquer programa). O primeiro início pode levar alguns segundos: o
   Windows abre o fone. Numa sala de espera, pressione ◌ Gravar ao ouvir som (veja "Gravar ao ouvir som e parada
   automática").
3. Entre na chamada do Teams, Zoom ou Meet como sempre. Tudo o que você ouve e tudo o que você fala vai para um único arquivo MP3.
4. Durante a gravação, preencha **Título**, **Pessoas** e os outros detalhes (ou depois, pela lista).
5. Pressione ■ Parar. O arquivo recebe as tags, é renomeado para **data - Título.mp3** e aparece na lista.

Nada é enviado a lugar nenhum: sem IA, sem transcrição, sem nuvem.
"""),
    ("Gravar ao ouvir som e parada automática", """
**Gravar ao ouvir som** é para uma chamada que ainda não começou (uma sala de espera, uma reunião que atrasa).
Pressione ◌ Gravar ao ouvir som: os dispositivos abrem e os medidores se mexem, mas nada é gravado até uma fonte
marcada (Áudio do computador ou Microfone) ter som. Então a gravação começa sozinha, incluindo o segundo antes do som.
Enquanto isso a janela mostra "Aguardando som…". **● Gravar agora** começa na hora; **■ Parar** (ou Ctrl+Alt+R) deixa
de aguardar e não deixa arquivo.

**Parada automática** (a linha sob os medidores):
- **Parar após 5 minutos em silêncio** (ligado por padrão): quando todas as fontes marcadas ficam em silêncio esse
  tempo, a gravação para e é salva. Silêncio é abaixo de -40 dB; pausas não contam. Digite o número que quiser (1.5 e
  1,5 funcionam).
- **Parar após 60 minutos**: a gravação para quando chega a essa duração; a linha mostra a hora em que vai parar.

As duas podem ser mudadas durante a gravação. A linha depois de salvar diz por que a gravação parou.
"""),
    ("Ouvir as gravações", """
Selecione uma gravação na lista e pressione **▶ Ouvir** (ou dê duplo clique, ou pressione Enter). **■ Parar** encerra. A linha
ao lado do botão mostra o que está tocando e o tempo. Quando a gravação termina, o botão volta a Ouvir.

- Ouvir usa os componentes de áudio do Windows: nada mais é instalado nem fica rodando.
- Ouvir fica desligado enquanto você grava, e iniciar uma gravação para a reprodução: o áudio do computador é o que o Tiny
  Recorder grava, então um arquivo tocando entraria na nova gravação.
- Editar os detalhes de uma gravação que está tocando a interrompe antes (um arquivo tocando não pode ser renomeado).
- Botão direito → **Abrir no player padrão** abre o arquivo no programa que o Windows usa para MP3.
- Botão direito → **Excluir…** (ou a tecla Delete) move a gravação para a Lixeira depois de perguntar; você pode restaurá-la
  de lá. Uma gravação que está tocando é parada antes. Numa pasta sem Lixeira (uma unidade de rede ou removível), ele
  pergunta antes de excluir o arquivo definitivamente.
"""),
    ("Transcrever com o TranscriptLab", """
O Tiny Recorder não transcreve. O **TranscriptLab**, um aplicativo gratuito separado, faz isso neste PC com o Whisper.
Selecione uma gravação e pressione **Transcrever** (ou botão direito → **Transcrever com o TranscriptLab**): o Tiny
Recorder encontra o TranscriptLab e entrega o arquivo a ele. O TranscriptLab abre (ou vem para a frente, se já estiver
aberto) e inicia a transcrição, ou coloca o arquivo na fila quando está ocupado.

- O Tiny Recorder não envia nada a lugar nenhum; o TranscriptLab também trabalha neste PC.
- Transcrever fica desligado enquanto você grava (o arquivo ainda não está pronto). Uma gravação que está tocando é
  parada antes.
- O Tiny Recorder encontra o TranscriptLab sozinho depois que o TranscriptLab 0.16.9 ou mais novo foi aberto uma vez.
  Se ele não for encontrado, uma janela oferece **Localizar…** (escolha o programa do TranscriptLab) e **Baixar o
  TranscriptLab** (abre a página de download). Configurações → **TranscriptLab** mostra qual é usado; **Limpar** volta a
  encontrá-lo sozinho.
"""),
    ("Tags e nomes de arquivo", """
**O que fica gravado no arquivo MP3 (tags ID3)**
- Data → a tag Data (e a primeira parte do nome do arquivo)
- Título → a tag Título (e a segunda parte do nome do arquivo)
- Pessoas → a tag Artista
- Projeto → a tag Álbum
- Notas → a tag Comentário
- Copyright → sempre "not for distribution, personal use only" (acrescentada a toda gravação; não pode ser mudada na
  janela e é mantida quando você edita os detalhes depois)

**Nome do arquivo**
**AAAA-MM-DD - Título.mp3**, por exemplo 2026-10-20 - Revisão do orçamento.mp3. Caracteres que o Windows não aceita em
nomes de arquivo (: / \\ ? * " < > |) viram espaços no nome; a tag Título guarda o seu texto exatamente como digitado.
Sem título o nome é "data - Untitled.mp3". Se o nome já existir, é acrescentado (2), (3)…

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

**Desligar um canal durante a gravação.** As caixas na frente de **Áudio do computador** e **Microfone** continuam
usáveis enquanto você grava. Desmarque uma e ela deixa de entrar no MP3 (o arquivo recebe silêncio no lugar, então a linha
do tempo continua certa); marque de novo e ela volta na hora. A linha sob o cronômetro diz qual canal está desligado. Um
canal que estava desmarcado quando você pressionou Gravar é aberto quando você o marca, o que pode levar alguns segundos
com um fone Bluetooth. A mudança vale só para esta gravação: as caixas voltam à sua escolha de sempre quando você para.
Desmarque um canal antes de pressionar Gravar para fazer disso a escolha de sempre.

**Avisos durante a gravação.** Se o Windows passar o som para outro dispositivo (um fone conectado, o Bluetooth
ligando) enquanto o Áudio do computador segue o padrão do Windows, a linha sob o cronômetro avisa: pare e grave de novo
para capturar o novo dispositivo. Se o Áudio do computador não der som nenhum por 3 minutos, um aviso discreto pede para
verificar o dispositivo; a gravação continua. Um dispositivo escolhido em Configurações que não está presente (um fone
desconectado) é trocado pelo padrão do Windows, e a linha avisa.
"""),
    ("Atalho global", """
**Ctrl+Alt+R** inicia e para a gravação em qualquer programa, sem trocar de janela durante a chamada.
**Ctrl+Alt+P** pausa e continua.
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
    ("Atualizações", """
Sobre → **Verificar atualizações** (ou Configurações → Atualizações) pergunta ao GitHub se existe um Tiny Recorder mais
novo. Nada sobre você é enviado, e o Tiny Recorder nunca verifica sozinho. Se houver, uma janela mostra o que há de novo:
- **Baixar e instalar** (a versão exe): o exe novo é salvo ao lado do atual, conferido com a soma SHA-256 da versão e
  iniciado quando você concordar; o exe antigo fica na pasta dele.
- **Abrir a página da versão** abre a página no navegador.
"""),
    ("Arquivos e privacidade", """
As gravações são salvas na pasta mostrada na parte de baixo da janela (Configurações → Pasta de saída). As configurações
ficam em %APPDATA%\\TinyRecorder. Nada mais é escrito, e nada é enviado a lugar nenhum.

**Uso responsável.** Avise as pessoas de uma reunião que você está gravando. Em muitos países, incluindo a Suíça, gravar uma
conversa sem o consentimento dos outros participantes pode ser crime, mesmo quando você participa dela. O Teams e o Zoom
anunciam as próprias gravações; o Tiny Recorder não anuncia nada aos outros. Este texto não é aconselhamento jurídico.
"""),
]

ES = [
    ("Primeros pasos", """
1. Abra Tiny Recorder antes de la reunión. Deje marcados **Audio de la computadora** y **Micrófono**.
2. Presione ● Grabar ahora (o Ctrl+Alt+R desde cualquier programa). El primer inicio puede tardar unos segundos:
   Windows abre los auriculares. En una sala de espera, presione ◌ Grabar al oír sonido (vea "Grabar al oír sonido y
   detención automática").
3. Entre en su llamada de Teams, Zoom o Meet como siempre. Todo lo que usted oye y todo lo que dice va a un solo
   archivo MP3.
4. Mientras graba, complete **Título**, **Personas** y los demás detalles (o más tarde, desde la lista).
5. Presione ■ Detener. El archivo recibe las etiquetas, se renombra como **fecha - Título.mp3** y aparece en la lista.

No se envía nada a ningún lugar: sin IA, sin transcripción, sin nube.
"""),
    ("Grabar al oír sonido y detención automática", """
**Grabar al oír sonido** es para una llamada que todavía no empezó (una sala de espera, una reunión que se atrasa).
Presione ◌ Grabar al oír sonido: los dispositivos se abren y los medidores se mueven, pero no se graba nada hasta que
una fuente marcada (Audio de la computadora o Micrófono) tenga sonido. Entonces la grabación empieza sola, con el
segundo anterior al sonido incluido. Mientras tanto la ventana muestra "Esperando sonido…". **● Grabar ahora** empieza
al instante; **■ Detener** (o Ctrl+Alt+R) deja de esperar y no deja ningún archivo.

**Detención automática** (la línea bajo los medidores):
- **Detener tras 5 minutos en silencio** (activado de forma predeterminada): cuando todas las fuentes marcadas están en
  silencio ese tiempo, la grabación se detiene y se guarda. Silencio es por debajo de -40 dB; las pausas no cuentan.
  Escriba el número que quiera (1.5 y 1,5 funcionan).
- **Detener tras 60 minutos**: la grabación se detiene cuando llega a esa duración; la línea muestra la hora en que se
  detendrá.

Las dos se pueden cambiar durante una grabación. La línea después de guardar dice por qué se detuvo la grabación.
"""),
    ("Reproducir grabaciones", """
Seleccione una grabación en la lista y presione **▶ Reproducir** (o haga doble clic, o presione Enter). **■ Detener** la
termina. La línea junto al botón muestra qué se está reproduciendo y el tiempo. Cuando la grabación termina, el botón
vuelve a Reproducir.

- La reproducción usa los componentes de Windows: no se instala nada más ni queda nada en ejecución.
- Reproducir está apagado mientras usted graba, y al iniciar una grabación se detiene la reproducción: el audio de la
  computadora es lo que Tiny Recorder graba, así que un archivo en reproducción terminaría en la nueva grabación.
- Editar los detalles de una grabación que se está reproduciendo la detiene antes (un archivo en reproducción no se
  puede renombrar).
- Clic derecho → **Abrir con el reproductor predeterminado** abre el archivo en el programa que Windows usa para MP3.
- Clic derecho → **Eliminar…** (o la tecla Supr) mueve la grabación a la Papelera de reciclaje después de preguntar;
  puede restaurarla desde allí. Una grabación que se está reproduciendo se detiene antes. En una carpeta sin Papelera de
  reciclaje (una unidad de red o extraíble) pregunta antes de eliminar el archivo definitivamente.
"""),
    ("Transcribir con TranscriptLab", """
Tiny Recorder no transcribe. **TranscriptLab**, una aplicación gratuita aparte, lo hace en esta PC con Whisper.
Seleccione una grabación y presione **Transcribir** (o clic derecho → **Transcribir con TranscriptLab**): Tiny Recorder
encuentra TranscriptLab y le entrega el archivo. TranscriptLab se abre (o pasa al frente, si ya está abierto) e inicia
la transcripción, o pone el archivo en la cola cuando está ocupado.

- Tiny Recorder no envía nada a ningún lugar; TranscriptLab también trabaja en esta PC.
- Transcribir está apagado mientras usted graba (el archivo aún no está terminado). Una grabación que se está
  reproduciendo se detiene antes.
- Tiny Recorder encuentra TranscriptLab solo después de que TranscriptLab 0.16.9 o posterior se abrió una vez. Si no lo
  encuentra, una ventana ofrece **Localizar…** (elija el programa de TranscriptLab) y **Obtener TranscriptLab** (abre su
  página de descarga). Configuración → **TranscriptLab** muestra cuál se usa; **Borrar** vuelve a buscarlo solo.
"""),
    ("Etiquetas y nombres de archivo", """
**Lo que se guarda en el archivo MP3 (etiquetas ID3)**
- Fecha → la etiqueta Fecha (y la primera parte del nombre del archivo)
- Título → la etiqueta Título (y la segunda parte del nombre del archivo)
- Personas → la etiqueta Artista
- Proyecto → la etiqueta Álbum
- Notas → la etiqueta Comentario
- Copyright → siempre "not for distribution, personal use only" (se agrega a cada grabación; no se puede cambiar en la
  ventana y se conserva cuando usted edita los detalles más tarde)

**Nombre del archivo**
**AAAA-MM-DD - Título.mp3**, por ejemplo 2026-10-20 - Revisión del presupuesto.mp3. Los caracteres que Windows no acepta
en nombres de archivo (: / \\ ? * " < > |) se cambian por espacios en el nombre; la etiqueta Título guarda su texto
exactamente como lo escribió. Sin título el nombre es "fecha - Untitled.mp3". Si el nombre ya existe, se agrega (2),
(3)…

**Cambiar una grabación más tarde**
Clic derecho en la lista → **Editar detalles y renombrar…**. Las etiquetas se vuelven a escribir y el archivo se
renombra.
"""),
    ("Calidad y tamaño", """
Configuración → Calidad:
- **Voz**: mono, 64 kbps. Voz clara, unos 29 MB por hora. Es la opción predeterminada.
- **Estándar**: estéreo, 128 kbps, unos 58 MB por hora.
- **Alta**: estéreo, 192 kbps, unos 86 MB por hora.

El sonido de la computadora y su micrófono siempre se mezclan en el mismo archivo. El volumen de cada uno se puede
ajustar en Configuración (de 0 a 200 %), para subir un micrófono bajo.
"""),
    ("Dispositivos y auriculares", """
**Audio de la computadora** es lo que reproduce el dispositivo de salida elegido (loopback). De forma predeterminada,
Tiny Recorder sigue la salida predeterminada de Windows en el momento en que usted presiona Grabar. Si pasa la llamada a
otro dispositivo durante una grabación, detenga y grabe de nuevo, o elija ese dispositivo en Configuración.

**Micrófono** sigue el micrófono predeterminado de Windows, o el que usted elija.

**Los auriculares Bluetooth** pasan a un modo "manos libres" de baja calidad cuando se usa su micrófono; eso lo hace el
programa de la reunión, no Tiny Recorder. La grabación funciona; la calidad es la que dan los auriculares.

Si uno de los dos no se puede abrir (por ejemplo, un micrófono bloqueado), se graba el otro y aparece un aviso.

**Apagar un canal durante una grabación.** Las casillas delante de **Audio de la computadora** y **Micrófono** siguen
disponibles mientras usted graba. Desmarque una y deja de estar en el MP3 (el archivo recibe silencio en su lugar, así
que la línea de tiempo sigue correcta); márquela de nuevo y vuelve al instante. La línea bajo el cronómetro indica qué
canal está apagado. Un canal que estaba desmarcado cuando usted presionó Grabar se abre cuando lo marca, lo que puede
tardar unos segundos con auriculares Bluetooth. El cambio vale solo para esta grabación: las casillas vuelven a su
elección habitual cuando usted detiene. Desmarque un canal antes de presionar Grabar para que esa sea la elección
habitual.

**Avisos durante una grabación.** Si Windows pasa el sonido a otro dispositivo (unos auriculares conectados, el
Bluetooth que se enciende) mientras el Audio de la computadora sigue el predeterminado de Windows, la línea bajo el
cronómetro lo indica: detenga y grabe de nuevo para capturar el nuevo dispositivo. Si el Audio de la computadora no da
ningún sonido durante 3 minutos, un aviso discreto le pide revisar el dispositivo; la grabación continúa. Un
dispositivo elegido en Configuración que no está (unos auriculares desconectados) se cambia por el predeterminado de
Windows, y la línea lo indica.
"""),
    ("Atajo global", """
**Ctrl+Alt+R** inicia y detiene la grabación desde cualquier programa, sin cambiar de ventana durante una llamada.
**Ctrl+Alt+P** la pausa y la reanuda.
El título de la ventana muestra ● GRAB y el tiempo, así la barra de tareas indica cuándo está grabando.
Si otro programa ya usa Ctrl+Alt+R, Tiny Recorder lo indica y el atajo queda apagado. Apáguelo en Configuración.
"""),
    ("Recuperación", """
Mientras graba, el archivo MP3 se escribe de forma continua (un archivo temporal que termina en .mp3.part). Si el
programa o la PC se detienen durante una grabación, no se pierde nada: la próxima vez que Tiny Recorder inicie,
encuentra el archivo sin terminar y ofrece recuperarlo como "fecha - Grabación recuperada.mp3".

La grabación también se detiene sola, y se guarda, cuando el disco casi no tiene espacio libre.
"""),
    ("Si algo sale mal", """
**El nivel del micrófono se queda en cero.** Revise que el micrófono no esté silenciado (botón de los auriculares,
Windows) y que Windows permita que las aplicaciones de escritorio lo usen: Configuración → Privacidad y seguridad →
Micrófono.

**El nivel del audio de la computadora se queda en cero.** No se está reproduciendo nada, o la reunión usa otro
dispositivo de salida que el que muestra la línea de estado. Elija el dispositivo correcto en Configuración →
Dispositivo de audio de la computadora.

**El primer Grabar tarda unos segundos.** Los auriculares Bluetooth y algunos antivirus abren los dispositivos de audio
lentamente. La ventana muestra "Iniciando…".

**No se puede renombrar el archivo.** Un reproductor o un programa de sincronización lo tiene abierto. Ciérrelo e
intente de nuevo.
"""),
    ("Actualizaciones", """
Acerca de → **Buscar actualizaciones** (o Configuración → Actualizaciones) pregunta a GitHub si existe un Tiny Recorder
más nuevo. No se envía nada sobre usted, y Tiny Recorder nunca busca por sí solo. Si hay uno, una ventana muestra las
novedades:
- **Descargar e instalar** (la versión exe): el exe nuevo se guarda junto al actual, se verifica con la suma SHA-256 de
  la versión y se inicia cuando usted lo acepte; el exe anterior queda en su carpeta.
- **Abrir la página de la versión** la abre en el navegador.
"""),
    ("Archivos y privacidad", """
Las grabaciones se guardan en la carpeta que se muestra en la parte inferior de la ventana (Configuración → Carpeta de
salida). La configuración se guarda en %APPDATA%\\TinyRecorder. No se escribe nada más y no se envía nada a ningún
lugar.

**Uso responsable.** Avise a las personas de una reunión que está grabando. En muchos países, incluida Suiza, grabar
una conversación sin el consentimiento de los demás participantes puede ser un delito, incluso cuando usted participa
en ella. Teams y Zoom anuncian sus propias grabaciones; Tiny Recorder no anuncia nada a los demás. Este texto no es
asesoramiento legal.
"""),
]
