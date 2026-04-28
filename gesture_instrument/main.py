import subprocess
import sys

REQUIRED = [
    "mediapipe==0.10.35",
    "opencv-python==4.9.0.80",
    "numpy>=1.26.4",
    "sounddevice==0.5.5"
]

def install_missing():
    import importlib
    package_map = {
        "mediapipe": "mediapipe==0.10.35",
        "cv2": "opencv-python==4.9.0.80",
        "numpy": "numpy>=1.26.4",
        "sounddevice": "sounddevice==0.5.5"
    }
    for import_name, pip_name in package_map.items():
        try:
            importlib.import_module(import_name)
        except ImportError:
            print(f"Installing {pip_name}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", pip_name])

install_missing()

import time
import cv2

from hand_tracker import HandTracker
from radial_menu import RadialMenu
from music_engine import MusicEngine
from config import LEFT_MENU, RIGHT_MENU, SAMPLE_RATE, DISPLAY_W, DISPLAY_H, DEBOUNCE_S

WINDOW_NAME = "Gesture Instrument"


def build_menu(cfg) -> RadialMenu:
    return RadialMenu(
        center_ratio=cfg["center_ratio"],
        inner_r_ratio=cfg["inner_r_ratio"],
        outer_r_ratio=cfg["outer_r_ratio"],
        segments=cfg["segments"],
        accent_color=cfg["accent_color"],
        center_segment_index=cfg.get("center_segment_index"),
    )


def main():
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
    cv2.resizeWindow(WINDOW_NAME, DISPLAY_W, DISPLAY_H)

    tracker   = HandTracker()
    left_menu = build_menu(LEFT_MENU)
    right_menu = build_menu(RIGHT_MENU)
    engine    = MusicEngine(sample_rate=SAMPLE_RATE)

    # Debounce state — play chord only after selection is stable for DEBOUNCE_S seconds
    pending_chord = None   # (note, chord_type) candidate
    pending_since = 0.0
    active_chord  = None   # currently playing (note, chord_type)

    fps_timer   = time.time()
    fps         = 0
    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
            break

        hands = tracker.get_hands(frame)
        # flip display frame to match mirror view used inside tracker
        frame  = cv2.flip(frame, 1)
        # Resize to display resolution maintaining 4:3 — no horizontal stretch
        canvas = cv2.resize(frame, (DISPLAY_W, DISPLAY_H))

        left_tips  = hands.get("Left")   # list of (x,y) or None
        right_tips = hands.get("Right")

        left_hover  = left_menu.get_hovered(left_tips, canvas.shape)
        right_hover = right_menu.get_hovered(right_tips, canvas.shape)

        left_menu.render(canvas, left_hover)
        # Show active chord name in the right panel's inner circle
        right_center_label = RIGHT_MENU["segments"][right_hover]["label"] if right_hover is not None else (active_chord[1] if active_chord else None)
        right_menu.render(canvas, right_hover, center_label=right_center_label)

        selected_note  = LEFT_MENU["segments"][left_hover]["value"]  if left_hover  is not None else None
        selected_chord = RIGHT_MENU["segments"][right_hover]["value"] if right_hover is not None else None
        both_selected  = selected_note is not None and selected_chord is not None

        now = time.time()
        if both_selected:
            candidate = (selected_note, selected_chord)
            if candidate != pending_chord:
                pending_chord = candidate
                pending_since = now
            # Trigger once the candidate has been stable for DEBOUNCE_S
            if (now - pending_since) >= DEBOUNCE_S and candidate != active_chord:
                engine.play_chord(selected_note, selected_chord)
                active_chord = candidate
        else:
            pending_chord = None
            if active_chord is not None:
                engine.stop()
                active_chord = None

        # Fingertip dots — draw all three tracked tips per hand
        h, w = canvas.shape[:2]
        if left_tips is not None:
            for pt in left_tips:
                cv2.circle(canvas, (int(pt[0] * w), int(pt[1] * h)),
                           7, LEFT_MENU["accent_color"], -1, cv2.LINE_AA)

        if right_tips is not None:
            for pt in right_tips:
                cv2.circle(canvas, (int(pt[0] * w), int(pt[1] * h)),
                           7, RIGHT_MENU["accent_color"], -1, cv2.LINE_AA)

        # Chord name — top centre
        if active_chord is not None:
            note_label  = LEFT_MENU["segments"][left_hover]["label"]  if left_hover  is not None else active_chord[0][:-1]
            chord_label = RIGHT_MENU["segments"][right_hover]["label"] if right_hover is not None else active_chord[1]
            chord_text  = f"{note_label} {chord_label}"
            font = cv2.FONT_HERSHEY_SIMPLEX
            scale, thick = 1.8, 3
            (tw, *_), _ = cv2.getTextSize(chord_text, font, scale, thick)
            tx, ty = (w - tw) // 2, 70
            cv2.putText(canvas, chord_text, (tx + 2, ty + 2), font, scale, (0, 0, 0),     thick + 2, cv2.LINE_AA)
            cv2.putText(canvas, chord_text, (tx,     ty),     font, scale, (255, 255, 255), thick,     cv2.LINE_AA)

        # FPS
        frame_count += 1
        if now - fps_timer >= 1.0:
            fps        = frame_count
            frame_count = 0
            fps_timer  = now
        cv2.putText(canvas, f"FPS: {fps}", (14, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 1, cv2.LINE_AA)

        cv2.imshow(WINDOW_NAME, canvas)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    engine.close()
    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
