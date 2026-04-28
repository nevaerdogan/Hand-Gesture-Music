import numpy as np
import sounddevice as sd
import threading


CHORD_INTERVALS = {
    "maj":  [0, 4, 7],
    "min":  [0, 3, 7],
    "aug":  [0, 4, 8],
    "dim":  [0, 3, 6],
    "maj7": [0, 4, 7, 11],
    "min7": [0, 3, 7, 10],
    "sus4": [0, 5, 7],
    "dom7": [0, 4, 7, 10],
}

NOTE_MIDI = {
    "C": 60, "D": 62, "E": 64, "F": 65,
    "G": 67, "A": 69, "B": 71,
}


def _midi_to_freq(midi):
    return 440.0 * (2.0 ** ((midi - 69) / 12.0))


def _note_str_to_midi(note_str: str) -> int:
    name = note_str[:-1]
    octave = int(note_str[-1])
    return NOTE_MIDI[name] + (octave - 4) * 12


class MusicEngine:
    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate
        self._lock = threading.Lock()
        self._stream = None

        # Synthesis state — written by main thread, read by audio callback
        self._freqs: list[float] = []
        self._playing = False
        self._sample_pos = 0      # monotonically increasing sample counter
        self._chord_start = 0     # sample counter value when current chord started
        self._stopping = False
        self._stop_start = 0

        # ADSR timing in samples
        self._attack  = int(0.025 * sample_rate)
        self._decay   = int(0.060 * sample_rate)
        self._sustain = 0.7
        self._release = int(0.120 * sample_rate)

    # ---------------------------------------------------------------- callback
    def _callback(self, outdata, frames, time_info, status):
        with self._lock:
            freqs      = list(self._freqs)
            playing    = self._playing
            stopping   = self._stopping
            pos        = self._sample_pos
            chord_start = self._chord_start
            stop_start  = self._stop_start

        if not freqs:
            outdata[:] = 0
            with self._lock:
                self._sample_pos += frames
            return

        idx = np.arange(pos, pos + frames, dtype=np.float64)
        t   = idx / self.sample_rate

        # Sum sine waves
        signal = np.zeros(frames, dtype=np.float64)
        for f in freqs:
            signal += np.sin(2.0 * np.pi * f * t)

        # ADSR envelope — applied from chord_start
        elapsed = (idx - chord_start).clip(min=0)
        env = np.where(
            elapsed < self._attack,
            elapsed / max(self._attack, 1),
            np.where(
                elapsed < self._attack + self._decay,
                1.0 - (1.0 - self._sustain) * (elapsed - self._attack) / max(self._decay, 1),
                self._sustain
            )
        )

        # Release fade-out when stopping
        if stopping:
            rel_elapsed = (idx - stop_start).clip(min=0, max=self._release)
            rel_env = 1.0 - rel_elapsed / self._release
            env *= rel_env
            if pos + frames >= stop_start + self._release:
                with self._lock:
                    self._playing  = False
                    self._stopping = False
                    self._freqs    = []

        signal *= env
        # Normalize by number of notes to keep volume consistent
        signal = (signal / max(len(freqs), 1) * 0.5).astype(np.float32)
        np.clip(signal, -1.0, 1.0, out=signal)

        with self._lock:
            self._sample_pos += frames

        outdata[:, 0] = signal

    # ---------------------------------------------------------- public API
    def _ensure_stream(self):
        if self._stream is None or not self._stream.active:
            self._stream = sd.OutputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                blocksize=2048,
                callback=self._callback,
            )
            self._stream.start()

    def play_chord(self, root_note: str, chord_type: str):
        root_midi = _note_str_to_midi(root_note)
        intervals = CHORD_INTERVALS.get(chord_type, [0, 4, 7])
        freqs = [_midi_to_freq(root_midi + iv) for iv in intervals]
        with self._lock:
            was_playing = self._playing
            self._freqs    = freqs
            self._playing  = True
            self._stopping = False
            # Only restart the ADSR envelope when transitioning from silence
            if not was_playing:
                self._chord_start = self._sample_pos
        self._ensure_stream()

    def stop(self):
        with self._lock:
            if self._playing and not self._stopping:
                self._stopping  = True
                self._stop_start = self._sample_pos

    def close(self):
        """Hard stop — call on program exit."""
        with self._lock:
            self._playing  = False
            self._stopping = False
            self._freqs    = []
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
