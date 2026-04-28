# Left hand menu — Root Notes
LEFT_MENU = {
    "center_ratio": (0.25, 0.55),
    "inner_r_ratio": 0.125,
    "outer_r_ratio": 0.30,
    "accent_color": (200, 50, 255),  # Hot pink
    "segments": [
        {"label": "C", "value": "C4"},
        {"label": "D", "value": "D4"},
        {"label": "E", "value": "E4"},
        {"label": "F", "value": "F4"},
        {"label": "G", "value": "G4"},
        {"label": "A", "value": "A4"},
        {"label": "B", "value": "B4"},
    ]
}

# Right hand menu — Chord Types
RIGHT_MENU = {
    "center_ratio": (0.75, 0.55),
    "inner_r_ratio": 0.125,
    "outer_r_ratio": 0.30,
    "accent_color": (210, 40, 160),  # Purple
    "center_segment_index": 0,       # inner circle maps to "maj" (index 0)
    "segments": [
        {"label": "maj",  "value": "maj"},
        {"label": "min",  "value": "min"},
        {"label": "aug",  "value": "aug"},
        {"label": "dim",  "value": "dim"},
        {"label": "maj7", "value": "maj7"},
        {"label": "min7", "value": "min7"},
        {"label": "sus4", "value": "sus4"},
        {"label": "dom7", "value": "dom7"},
    ]
}

SAMPLE_RATE = 44100
FPS_TARGET = 30
DISPLAY_W = 960   # 4:3 ratio — no horizontal stretch
DISPLAY_H = 720
DEBOUNCE_S = 0.08  # seconds a selection must be stable before triggering audio
