import cv2
import numpy as np
import math


class RadialMenu:
    def __init__(self, center_ratio, inner_r_ratio, outer_r_ratio, segments, accent_color, center_segment_index=None):
        self.center_ratio = center_ratio
        self.inner_r_ratio = inner_r_ratio
        self.outer_r_ratio = outer_r_ratio
        self.segments = segments
        self.accent_color = accent_color
        self.center_segment_index = center_segment_index  # segment selected when hand is in inner circle
        self._n = len(segments)
        self._seg_angle = 360.0 / self._n

    def _center_px(self, frame_shape):
        h, w = frame_shape[:2]
        return int(self.center_ratio[0] * w), int(self.center_ratio[1] * h)

    def _radii(self, frame_shape):
        h = frame_shape[0]
        return int(self.inner_r_ratio * h), int(self.outer_r_ratio * h)

    def _check_point(self, norm_point, frame_shape) -> int | None:
        h, w = frame_shape[:2]
        px = norm_point[0] * w
        py = norm_point[1] * h
        cx, cy = self._center_px(frame_shape)
        inner_r, outer_r = self._radii(frame_shape)
        dist = math.hypot(px - cx, py - cy)
        if dist > outer_r:
            return None
        if dist < inner_r:
            return self.center_segment_index  # None or a fixed segment index
        angle = math.degrees(math.atan2(px - cx, -(py - cy))) % 360
        return int(angle / self._seg_angle) % self._n

    def get_hovered(self, tip_points, frame_shape) -> int | None:
        """Accept a list of (norm_x, norm_y) fingertip positions.
        Returns the segment index hit by the first tip that lands in the annulus."""
        if tip_points is None:
            return None
        for pt in tip_points:
            idx = self._check_point(pt, frame_shape)
            if idx is not None:
                return idx
        return None

    def render(self, frame, hovered_index, center_label: str | None = None):
        cx, cy = self._center_px(frame.shape)
        inner_r, outer_r = self._radii(frame.shape)
        overlay = frame.copy()

        for i in range(self._n):
            start_angle = i * self._seg_angle - 90
            end_angle = start_angle + self._seg_angle
            color = tuple(int(c * 0.8) for c in self.accent_color) if i == hovered_index else (45, 45, 45)
            pts = self._wedge_polygon(cx, cy, inner_r, outer_r, start_angle, end_angle)
            cv2.fillPoly(overlay, [pts], color)

        cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

        for i in range(self._n):
            angle_rad = math.radians(i * self._seg_angle - 90)
            ix = int(cx + inner_r * math.cos(angle_rad))
            iy = int(cy + inner_r * math.sin(angle_rad))
            ox = int(cx + outer_r * math.cos(angle_rad))
            oy = int(cy + outer_r * math.sin(angle_rad))
            cv2.line(frame, (ix, iy), (ox, oy), (255, 255, 255), 1, cv2.LINE_AA)

        cv2.circle(frame, (cx, cy), inner_r, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy), outer_r, (255, 255, 255), 1, cv2.LINE_AA)

        font_scale = max(0.45, outer_r / 480)
        for i, seg in enumerate(self.segments):
            mid_angle = math.radians((i + 0.5) * self._seg_angle - 90)
            mid_r = (inner_r + outer_r) / 2
            tx = int(cx + mid_r * math.cos(mid_angle))
            ty = int(cy + mid_r * math.sin(mid_angle))
            text = seg["label"]
            font = cv2.FONT_HERSHEY_SIMPLEX
            (tw, th), _ = cv2.getTextSize(text, font, font_scale, 1)
            cv2.putText(frame, text, (tx - tw // 2, ty + th // 2),
                        font, font_scale, (255, 255, 255), 1, cv2.LINE_AA)

        # Draw active label in the inner circle
        if center_label:
            font = cv2.FONT_HERSHEY_SIMPLEX
            cl_scale = max(0.5, inner_r / 80)
            cl_thick = max(1, int(cl_scale * 1.8))
            (lw, lh), _ = cv2.getTextSize(center_label, font, cl_scale, cl_thick)
            cv2.putText(frame, center_label,
                        (cx - lw // 2, cy + lh // 2),
                        font, cl_scale, (255, 255, 255), cl_thick, cv2.LINE_AA)

    def _wedge_polygon(self, cx, cy, r_in, r_out, start_deg, end_deg, steps=24):
        pts = []
        for a in np.linspace(start_deg, end_deg, steps):
            rad = math.radians(a)
            pts.append([int(cx + r_out * math.cos(rad)), int(cy + r_out * math.sin(rad))])
        for a in np.linspace(end_deg, start_deg, steps):
            rad = math.radians(a)
            pts.append([int(cx + r_in * math.cos(rad)), int(cy + r_in * math.sin(rad))])
        return np.array(pts, dtype=np.int32)
