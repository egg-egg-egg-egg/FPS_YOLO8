# region_picker.py
# pip install mss opencv-python numpy

import cv2
import numpy as np
from mss import mss

def pick_region(max_display_w=1600, max_display_h=900):
    """
    在桌面截图上用鼠标拖拽选择区域，按 Enter 确认，返回 mss 兼容的区域字典。
    支持多显示器（虚拟桌面）。Esc 取消返回 None。
    """
    with mss() as sct:
        vmon = sct.monitors[0]  # 虚拟桌面（覆盖所有显示器）
        shot = sct.grab(vmon)
        img = np.array(shot)[:, :, :3]  # BGRA -> BGR 只取前三通道
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        H, W = img.shape[:2]

        # 缩放以适配窗口显示，记录缩放比例
        scale = min(1.0, min(max_display_w / W, max_display_h / H))
        disp = cv2.resize(img, (int(W * scale), int(H * scale))) if scale < 1.0 else img.copy()

        win = "Select region (Drag LMB, Enter=OK, R=Reset, Esc=Cancel)"
        cv2.namedWindow(win, cv2.WINDOW_NORMAL)
        cv2.imshow(win, disp)

        selecting = False
        start_pt, end_pt = None, None
        disp_draw = disp.copy()

        def on_mouse(event, x, y, flags, param):
            nonlocal selecting, start_pt, end_pt, disp_draw
            disp_draw = disp.copy()
            if event == cv2.EVENT_LBUTTONDOWN:
                selecting = True
                start_pt = (x, y)
                end_pt = (x, y)
            elif event == cv2.EVENT_MOUSEMOVE and selecting:
                end_pt = (x, y)
            elif event == cv2.EVENT_LBUTTONUP:
                selecting = False
                end_pt = (x, y)

            # 绘制半透明选区
            if start_pt and end_pt:
                x1, y1 = start_pt
                x2, y2 = end_pt
                x0, y0 = min(x1, x2), min(y1, y2)
                x3, y3 = max(x1, x2), max(y1, y2)
                overlay = disp_draw.copy()
                cv2.rectangle(overlay, (x0, y0), (x3, y3), (0, 200, 255), -1)
                disp_draw = cv2.addWeighted(overlay, 0.25, disp_draw, 0.75, 0)
                cv2.rectangle(disp_draw, (x0, y0), (x3, y3), (0, 200, 255), 2)

        cv2.setMouseCallback(win, on_mouse)

        while True:
            cv2.imshow(win, disp_draw)
            key = cv2.waitKey(10) & 0xFF
            if key == 27:  # Esc
                cv2.destroyWindow(win)
                return None
            if key in (ord('\r'), 10, 13):  # Enter
                if start_pt and end_pt:
                    x1, y1 = start_pt
                    x2, y2 = end_pt
                    x0, y0 = min(x1, x2), min(y1, y2)
                    x3, y3 = max(x1, x2), max(y1, y2)
                    # 防止零大小
                    if x3 - x0 < 5 or y3 - y0 < 5:
                        continue
                    # 映射回原始像素坐标
                    left = int(x0 / scale)
                    top = int(y0 / scale)
                    width = int((x3 - x0) / scale)
                    height = int((y3 - y0) / scale)

                    # 转换到虚拟桌面绝对坐标（可能为负，mss 支持）
                    abs_left = vmon["left"] + left
                    abs_top = vmon["top"] + top
                    region = {"top": abs_top, "left": abs_left, "width": width, "height": height}
                    cv2.destroyWindow(win)
                    return region
            if key in (ord('r'), ord('R')):
                start_pt, end_pt = None, None
                disp_draw = disp.copy()

if __name__ == "__main__":
    box = pick_region()
    print("Selected region:", box)
