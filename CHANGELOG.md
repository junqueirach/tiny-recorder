# Changelog

## 0.1.4 — 2026-11-01

- **Interface in English, Portuguese (Brazil) and Spanish**: the Windows display language by default (any other
  language gives English), Settings → Interface language changes it at once. Settings saved as `ui_language`; the old
  `lang` setting is read once (`pt` becomes Portuguese, `en` follows Windows). Recordings, tags and file names are the
  same in every language
- **Transcribe with TranscriptLab**: a Transcribe button next to Play and a right-click entry hand the selected recording
  to TranscriptLab 0.16.9 or newer (found through its `install.json`, or chosen in Settings → TranscriptLab). If it is
  not found or too old, a window offers Locate… and Get TranscriptLab
- **Record Now** (the old Record) and **Start on Sound**: waits with the devices open and starts writing when a ticked
  source has sound, with the second before it
- **Auto stop**: after N silent minutes (on by default, 5) and / or at a set length (shows the time it will stop)
- **Ctrl+Alt+P** pauses and resumes from any program
- **Warnings while recording**: Windows moved the sound to another device; the computer audio has been silent for
  3 minutes
- **Check for updates** in About and Settings (as RadioSave)
- The Pause button shows the usual pause sign
- **Fixed** (a review of 0.1.3):
  - a second start could bring an Explorer window on the "Tiny Recorder" folder to the front instead of the app
  - Delete on a network or removable drive deleted for good without saying so; it now asks
  - changing only the capitals of a title did not rename the file
  - Edit details moved an old recording to the top of the list
  - after Stop or an edit, the new or renamed file is selected
  - the Date box kept the day the app was opened
  - Ctrl+Alt+R with Settings open started a recording behind it; Settings now closes without saving
  - a saved computer-audio device that is gone recorded only the microphone; both now fall back to the Windows default
  - a wrong date on the main window was silently replaced by today; the preview says so
  - the "hotkey used by another program" warning disappeared or stayed at the wrong times
  - F1 opened one more Help window each time
  - a window saved on a removed monitor opened off-screen
  - a file vanishing while the list loaded stopped the list refreshing
  - the window did not fit a 1366 × 768 screen (now a compact layout there); the minimum size now always shows some
    rows of the list
  - the "Not available: …" warning of a recording disappeared after 0.1 s
  - the Portuguese Help said untitled recordings are named "Sem título" (the file name is "Untitled")
- 193 tests (122 new; 8 of the 71 from 0.1.3 rewritten because they tested the old language setting)

## 0.1.3 — 2026-10-20

- **Third-party notices** (`THIRD_PARTY_LICENSES.md`, also in the release zip): the exe contains mutagen (GPL-2.0-or-later)
  and lameenc / LAME (LGPL-3.0-or-later), so the exe as a whole is distributed under the GNU GPL version 3 or later, while
  the app's own source stays MIT. The file lists every bundled component with its licence and source, says where the source
  is, and carries the full licence texts. The README has a section on it and About names the file
- **Fixed:** the level meters kept their last bars after a recording ended (they only fell a little per update); they are
  now emptied at once, with the peak-hold tick
- **Fixed:** the Help text kept the source's hard line breaks and showed ragged lines in the word-wrapped box (mainly the
  Portuguese "Arquivos e privacidade"); lines of one paragraph are now joined
- 71 tests (6 new)

## 0.1.2 — 2026-10-20

- **Copyright tag on every recording**: the ID3 Copyright field always holds "not for distribution, personal use only".
  It is written when a recording is saved or recovered and kept when its details are edited later (a recording made
  before 0.1.2 gets it the first time it is edited)
- **Computer audio and Microphone can be switched off and on during a recording**: the boxes stay usable while recording.
  An unticked channel is not in the MP3 (the file gets silence for it, so the timeline stays right); ticking it again is
  instant. A channel that was unticked at Record is opened in the background when it is ticked. The line under the timer
  says which channel is off; both off shows a warning. The change is for that recording only; the boxes return to your
  usual choice when it ends. A channel that cannot be opened is unticked with a message
- **Delete…** in the right-click menu (and the Delete key): asks, stops the playback if that file is playing, and moves the
  recording to the Recycle Bin
- **About**: GitHub (github.com/junqueirach/tiny-recorder), Bugs & ideas (GitHub issues) and Licence (MIT), as in the other
  apps; the "Responsible use" text is the new wording
- Help: Copyright tag, Delete, switching a channel off; Portuguese text for every new string
- Fixed: a source opened while another stream is running failed with "Unanticipated host error" (-9999) on a Bluetooth
  headset; the helper thread now initialises COM and uses its own PyAudio instance
- Tidy: removed a dead branch when a recording ends; the status line is built in one place
- 65 tests (14 new)

## 0.1.1 — 2026-10-20

- **Play and Stop** for saved recordings, built in: select a recording and press ▶ Play (or double-click, or Enter);
  ■ Stop ends it. The line next to the button shows the title and the time (`00:12 / 05:00`); the button returns to Play
  when the file ends. Uses the Windows MCI player: no extra package, nothing left running
- Play is off while recording, and starting a recording stops the playback (the playing file would be recorded as part
  of the computer audio); editing a recording that is playing stops it first, so the file can be renamed
- Right-click menu: **Play** and **Open with the default player** (the old behaviour of Play)
- The newest recording is selected for you, and the selection is kept when the list reloads
- Help: new section "Playing recordings"; Portuguese text for every new string
- 51 tests (10 new: the player with a fake MCI, and the window's Play / Stop flows)

## 0.1.0 — 2026-10-20

First version.

- Records the computer's sound (WASAPI loopback) and the microphone into one MP3 (LAME), mixed on a wall clock so a silent
  source never stalls or drifts; sources at different sample rates are brought to one rate
- Record / Pause / Resume / Stop, timer, two level meters, Ctrl+Alt+R from any program, ● REC in the window title
- Tags (date, title, people, project, notes) written to the MP3 as ID3v2.4; the file is named `YYYY-MM-DD - Title.mp3`
  (illegal characters replaced, `(2)` added when the name is taken)
- Recordings list read from the output folder; right-click: Play, Show in folder, Edit details and rename…, Copy path
- Quality presets: Voice (mono 64 kbps), Standard (stereo 128 kbps), High (stereo 192 kbps)
- The MP3 is written while recording (`.mp3.part`); an unfinished file is offered for recovery at the next start;
  automatic stop and save when the disk is almost full
- A source that cannot be opened (blocked microphone) is skipped with a warning; the other one is recorded
- Settings: output folder, quality, devices, volume of each source, hotkey, language
- About, Help (F1), English and Portuguese, Catppuccin Mocha dark theme, icon
- 41 tests (core, audio engine with fake sources, i18n, window driven in-process)
