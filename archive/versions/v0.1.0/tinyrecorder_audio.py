"""
Tiny Recorder — the audio engine (v0.1.0).

Two sources are captured with WASAPI (PyAudioWPatch): the computer's sound (loopback of an output device: everything
you hear) and a microphone (everything you say). A mixer thread keeps one wall clock, takes what each source has
buffered, brings both to one sample rate, adds them and streams the result to an MP3 file (LAME, no ffmpeg).
A source that is silent (loopback often delivers nothing while no sound plays) simply contributes zeros, so the
two never drift apart. No AI, no transcription: only the recording.

The Recorder takes any objects with the Source interface, so tests run it with fake sources and no sound card.
"""

import queue
import threading
import time

import numpy as np

SAMPLE_RATES = (44100, 48000)       # MP3 rates both devices and players handle everywhere
TICK = 0.1                          # seconds between mixer steps
MAX_LAG = 0.6                       # seconds of buffered audio kept beyond what is needed (then the oldest is dropped)
LOW_DISK = 40 * 1024 * 1024         # stop and save when less than this is free
FRAMES_PER_BUFFER = 2048


# ---------------------------------------------------------------- devices

def list_devices():
    """{'loopbacks': [names], 'mics': [names], 'default_out': name, 'default_in': name}; names only, never indexes
    (indexes change between runs). Raises RuntimeError when WASAPI is not available."""
    import pyaudiowpatch as pa
    p = pa.PyAudio()
    try:
        api = p.get_host_api_info_by_type(pa.paWASAPI)
        d_out = p.get_device_info_by_index(api["defaultOutputDevice"])
        try:
            d_in = p.get_device_info_by_index(api["defaultInputDevice"])
            default_in = d_in["name"]
        except Exception:                                                    # noqa: BLE001
            default_in = ""
        loops = [lb["name"] for lb in p.get_loopback_device_info_generator()]
        mics = []
        for i in range(p.get_device_count()):
            d = p.get_device_info_by_index(i)
            if d["hostApi"] == api["index"] and d["maxInputChannels"] > 0 and not d.get("isLoopbackDevice"):
                mics.append(d["name"])
        return {"loopbacks": loops, "mics": mics, "default_out": d_out["name"], "default_in": default_in}
    except OSError as e:
        raise RuntimeError(str(e))
    finally:
        p.terminate()


def loopback_label(name):
    """'Headphones (Jabra) [Loopback]' -> 'Headphones (Jabra)'."""
    return name[:-len(" [Loopback]")] if name.endswith(" [Loopback]") else name


# ---------------------------------------------------------------- sources

class Source:
    """Interface of a capture source. rate and channels describe what pull() gets from the device."""
    kind = "system"                      # "system" or "mic"
    rate = 48000
    channels = 2
    name = ""
    error = ""

    def start(self):                     # open the device; raise OSError / RuntimeError when it cannot be opened
        pass

    def pull(self, n):                   # n frames at self.rate, shape (n, channels), float32 -1..1; short = zero padded
        return np.zeros((n, self.channels), dtype=np.float32)

    def trim(self, keep):                # drop buffered frames beyond `keep` (the newest are kept)
        pass

    def stop(self):
        pass


class DeviceSource(Source):
    """A real WASAPI device (loopback or microphone) read through a callback into a buffer."""

    def __init__(self, pa_mod, pa_inst, info, kind):
        self._pa_mod, self._pa, self.info, self.kind = pa_mod, pa_inst, info, kind
        self.name = info["name"]
        self.rate = int(info["defaultSampleRate"])
        self.channels = max(1, min(int(info["maxInputChannels"]), 2 if kind == "system" else 2))
        self._lock = threading.Lock()
        self._chunks = []
        self._frames = 0
        self._stream = None

    def _callback(self, in_data, frame_count, time_info, status):
        try:
            a = np.frombuffer(in_data, dtype=np.int16).reshape(-1, self.channels).astype(np.float32) / 32768.0
            with self._lock:
                self._chunks.append(a)
                self._frames += len(a)
        except Exception:                                                    # noqa: BLE001
            pass
        return (None, self._pa_mod.paContinue)

    def start(self):
        self._stream = self._pa.open(format=self._pa_mod.paInt16, channels=self.channels, rate=self.rate,
                                     input=True, input_device_index=int(self.info["index"]),
                                     frames_per_buffer=FRAMES_PER_BUFFER, stream_callback=self._callback)
        self._stream.start_stream()

    def pull(self, n):
        out = np.zeros((n, self.channels), dtype=np.float32)
        if n <= 0:
            return out
        with self._lock:
            got = 0
            while self._chunks and got < n:
                c = self._chunks[0]
                take = min(len(c), n - got)
                out[got:got + take] = c[:take]
                got += take
                if take == len(c):
                    self._chunks.pop(0)
                else:
                    self._chunks[0] = c[take:]
            self._frames -= got
        return out

    def trim(self, keep):
        with self._lock:
            while self._chunks and self._frames - len(self._chunks[0]) >= keep:
                self._frames -= len(self._chunks.pop(0))

    def stop(self):
        st, self._stream = self._stream, None
        if st is not None:
            try:
                st.stop_stream()
                st.close()
            except Exception:                                                # noqa: BLE001
                pass


def open_sources(want_system, want_mic, system_name="", mic_name=""):
    """Open the wanted devices. Returns (pa_instance, [sources], [problem texts]). A device that cannot be opened
    is reported and skipped, so a blocked microphone never loses the computer audio."""
    import pyaudiowpatch as pa
    p = pa.PyAudio()
    sources, problems = [], []
    try:
        api = p.get_host_api_info_by_type(pa.paWASAPI)
    except OSError as e:
        p.terminate()
        return None, [], ["WASAPI is not available: %s" % e]
    if want_system:
        try:
            target = (system_name + " [Loopback]") if system_name else \
                p.get_device_info_by_index(api["defaultOutputDevice"])["name"] + " [Loopback]"
            info = next((lb for lb in p.get_loopback_device_info_generator() if lb["name"] == target), None)
            if info is None:
                raise OSError("no loopback device named %r" % target)
            s = DeviceSource(pa, p, info, "system")
            s.start()
            sources.append(s)
        except Exception as e:                                               # noqa: BLE001
            problems.append("computer audio: %s" % e)
    if want_mic:
        try:
            info = None
            if mic_name:
                for i in range(p.get_device_count()):
                    d = p.get_device_info_by_index(i)
                    if d["hostApi"] == api["index"] and d["name"] == mic_name and d["maxInputChannels"] > 0:
                        info = d
                        break
            if info is None:
                info = p.get_device_info_by_index(api["defaultInputDevice"])
            s = DeviceSource(pa, p, info, "mic")
            s.start()
            sources.append(s)
        except Exception as e:                                               # noqa: BLE001
            problems.append("microphone: %s" % e)
    return p, sources, problems


# ---------------------------------------------------------------- mixing

def choose_out_rate(sources):
    """The computer audio is never resampled when its rate is an MP3 rate; otherwise 48000."""
    for s in sources:
        if s.kind == "system" and s.rate in SAMPLE_RATES:
            return s.rate
    for s in sources:
        if s.rate in SAMPLE_RATES:
            return s.rate
    return 48000


def to_layout(block, out_channels):
    """(n, ch) -> (n, out_channels): mono = mean of all channels; stereo = first two (a mono source is doubled)."""
    n, ch = block.shape
    if out_channels == 1:
        return block.mean(axis=1, keepdims=True) if ch > 1 else block
    if ch == 1:
        return np.repeat(block, 2, axis=1)
    return block[:, :2]


def resample(block, n_out):
    """Linear interpolation of an (n_in, ch) block to n_out frames. Good for speech; exact when the sizes match."""
    n_in = block.shape[0]
    if n_in == n_out or n_out <= 0:
        return block if n_out > 0 else block[:0]
    if n_in <= 1:
        return np.repeat(block[:1] if n_in else np.zeros((1, block.shape[1]), np.float32), n_out, axis=0)
    xs = np.linspace(0, n_in - 1, n_out)
    xi = np.arange(n_in)
    return np.stack([np.interp(xs, xi, block[:, c]) for c in range(block.shape[1])], axis=1).astype(np.float32)


class Lane:
    """One source on the mixer's clock: converts 'frames of output' into 'frames of input' without drift."""

    def __init__(self, source, out_rate, out_channels, gain):
        self.source, self.out_rate, self.out_channels, self.gain = source, out_rate, out_channels, gain
        self.produced = 0
        self.consumed = 0
        self.peak = 0.0

    def get(self, n_out):
        self.produced += n_out
        target_in = int(self.produced * self.source.rate / self.out_rate)
        n_in = max(0, target_in - self.consumed)
        self.consumed = target_in
        self.source.trim(n_in + int(MAX_LAG * self.source.rate))
        block = self.source.pull(n_in)
        block = to_layout(block, self.out_channels)
        block = resample(block, n_out) * self.gain
        self.peak = float(np.max(np.abs(block))) if block.size else 0.0
        return block


def make_encoder(rate, channels, kbps, quality=5):
    import lameenc
    enc = lameenc.Encoder()
    enc.set_bit_rate(kbps)
    enc.set_in_sample_rate(rate)
    enc.set_out_sample_rate(rate)
    enc.set_channels(channels)
    enc.set_quality(quality)                                 # 2 = best and slowest, 5 = good and light, 7 = fast
    return enc


class Recorder:
    """Runs one recording on its own thread. Events go to `events` (a queue the Tk thread drains):
        ("started", out_rate, [source names], [problems])   ("levels", system_peak, mic_peak, seconds, size_bytes)
        ("error", text)    ("lowdisk",)    ("stopped", seconds, part_path)
    The file at part_path is a valid MP3 stream while recording (and after a crash)."""

    def __init__(self, part_path, preset, events, opener, system_gain=1.0, mic_gain=1.0, free_check=None):
        self.part_path, self.events = part_path, events
        self.channels, self.kbps = preset["channels"], preset["kbps"]
        self.quality = preset.get("quality", 5)
        self.opener = opener                               # callable() -> (pa_instance, [sources], [problems])
        self.gains = {"system": system_gain, "mic": mic_gain}
        self.free_check = free_check                       # callable() -> free bytes or None
        self._stop = threading.Event()
        self._paused = threading.Event()
        self._thread = None
        self.seconds = 0.0

    def start(self):
        self._thread = threading.Thread(target=self._run, name="recorder", daemon=True)
        self._thread.start()

    def pause(self):
        self._paused.set()

    def resume(self):
        self._paused.clear()

    @property
    def paused(self):
        return self._paused.is_set()

    def request_stop(self):
        """Ask the recorder to finish; returns at once. The "stopped" event arrives when the file is closed."""
        self._stop.set()

    def stop(self, wait=15.0):
        self._stop.set()
        if self._thread:
            self._thread.join(wait)

    def _put(self, *ev):
        try:
            self.events.put_nowait(ev)
        except queue.Full:
            pass

    def _run(self):
        pa_inst, sources, problems = None, [], []
        f = None
        try:
            pa_inst, sources, problems = self.opener()
            if not sources:
                self._put("error", "; ".join(problems) or "no audio source could be opened")
                return
            out_rate = choose_out_rate(sources)
            lanes = [Lane(s, out_rate, self.channels, self.gains.get(s.kind, 1.0)) for s in sources]
            enc = make_encoder(out_rate, self.channels, self.kbps, self.quality)
            f = open(self.part_path, "wb")
            self._put("started", out_rate, [s.name for s in sources], problems)
            t0 = time.monotonic()
            total_out = 0                                   # frames of wall-clock time, paused or not
            written = 0                                     # frames that went into the file
            last_ev = last_disk = t0
            while not self._stop.wait(TICK):
                now = time.monotonic()
                n_out = int((now - t0) * out_rate) - total_out
                if n_out <= 0:
                    continue
                total_out += n_out
                blocks = [lane.get(n_out) for lane in lanes]
                if not self._paused.is_set():
                    mix = np.clip(sum(blocks), -1.0, 1.0)
                    pcm = (mix * 32767.0).astype(np.int16)
                    data = enc.encode(pcm.tobytes())
                    if data:
                        f.write(data)
                    written += n_out
                    self.seconds = written / float(out_rate)
                if now - last_ev >= TICK:
                    last_ev = now
                    sp = max([ln.peak for ln, s in zip(lanes, sources) if s.kind == "system"] or [0.0])
                    mp = max([ln.peak for ln, s in zip(lanes, sources) if s.kind == "mic"] or [0.0])
                    if self._paused.is_set():
                        sp = mp = 0.0
                    self._put("levels", sp, mp, self.seconds, f.tell())
                if self.free_check and now - last_disk >= 20:
                    last_disk = now
                    free = self.free_check()
                    if free is not None and free < LOW_DISK:
                        self._put("lowdisk")
                        break
            if written:                                     # LAME refuses to flush before it has encoded anything
                tail = enc.flush()
                if tail:
                    f.write(tail)
        except Exception as e:                                               # noqa: BLE001
            self._put("error", "%s: %s" % (type(e).__name__, e))
        finally:
            if f is not None:
                try:
                    f.flush()
                    f.close()
                except OSError:
                    pass
            for s in sources:
                s.stop()
            if pa_inst is not None:
                try:
                    pa_inst.terminate()
                except Exception:                                            # noqa: BLE001
                    pass
            self._put("stopped", self.seconds, self.part_path)
