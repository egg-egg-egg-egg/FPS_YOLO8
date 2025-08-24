import sys, time
import numpy as np
import cv2
from mss import mss
from ultralytics import YOLO
from PyQt5 import QtWidgets, QtCore, QtGui
import keyboard
from ctypes import windll

# 高 DPI 适配（建议放在 QApplication 之前）
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

def virtual_geometry():
    # 计算所有屏幕的联合矩形（支持多显示器、负坐标）
    rects = [s.geometry() for s in QtWidgets.QApplication.screens()]
    left = min(r.left() for r in rects)
    top = min(r.top() for r in rects)
    right = max(r.right() for r in rects)
    bottom = max(r.bottom() for r in rects)
    return QtCore.QRect(left, top, right - left + 1, bottom - top + 1)

class RegionSelector(QtWidgets.QWidget):
    region_selected = QtCore.pyqtSignal(dict)
    def __init__(self):
        super().__init__()
        self.start = None
        self.end = None
        self.vgeo = virtual_geometry()
        
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        # 覆盖到虚拟桌面范围（跨屏）
        self.setGeometry(self.vgeo)
        self.show()

    def mousePressEvent(self, e):
        self.start = e.pos()
        self.end = e.pos()
        self.update()

    def mouseMoveEvent(self, e):
        if self.start:
            self.end = e.pos()
            self.update()

    def mouseReleaseEvent(self, e):
        if self.start and self.end:
            self.confirm_and_emit()

    def keyPressEvent(self, e):
        if e.key() == QtCore.Qt.Key_Escape:
            self.close()
        elif e.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            if self.start and self.end:
                self.confirm_and_emit()

    def confirm_and_emit(self):
        x1 = min(self.start.x(), self.end.x())
        y1 = min(self.start.y(), self.end.y())
        x2 = max(self.start.x(), self.end.x())
        y2 = max(self.start.y(), self.end.y())
        if x2 - x1 < 5 or y2 - y1 < 5:
            return
        # 转为全局坐标（加上虚拟桌面偏移）
        region = {
            "left": self.vgeo.left() + x1,
            "top": self.vgeo.top() + y1,
            "width": x2 - x1,
            "height": y2 - y1
        }
        
        self.region_selected.emit(region)
        self.close()

    def paintEvent(self, e):
        painter = QtGui.QPainter(self)
        # 全屏半透明遮罩（让屏幕变暗）
        painter.fillRect(self.rect(), QtGui.QColor(0, 0, 0, 120))
        if self.start and self.end:
            rect = QtCore.QRect(self.start, self.end).normalized()
            # 清除选区内的遮罩（让选区变亮）
            painter.setCompositionMode(QtGui.QPainter.CompositionMode_Clear)
            painter.fillRect(rect, QtCore.Qt.transparent)
            painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceOver)
            # 画边框与尺寸
            pen = QtGui.QPen(QtGui.QColor(0, 200, 255, 220), 2)
            painter.setPen(pen)
            painter.drawRect(rect)
            label = f"{rect.width()} x {rect.height()}"
            painter.setPen(QtGui.QColor(255, 255, 255, 230))
            painter.drawText(rect.topLeft() + QtCore.QPoint(8, -8), label)

class OverlayWindow(QtWidgets.QWidget):
    def __init__(self, monitor, model):
        super().__init__()
        self.monitor = monitor
        self.model = model
        self.visible_overlay = True   # 控制叠加层显示
        self.paused = False           # 控制是否暂停推理
        self.sct = mss()
        self.frame = np.zeros((monitor["height"], monitor["width"], 4), dtype=np.uint8)

        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.Tool
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setGeometry(monitor["left"], monitor["top"], monitor["width"], monitor["height"])
        self.show()

        # 让窗口鼠标穿透（Win32 扩展样式）
        self.make_click_through()

        # 定时器：定期抓屏+推理+重绘
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(50)  # 20 FPS，CPU 机器更稳

        # 全局热键
        keyboard.add_hotkey('ctrl+alt+o', self.toggle_overlay)  # 显示/隐藏叠加
        keyboard.add_hotkey('ctrl+alt+p', self.toggle_pause)    # 开/关推理
        keyboard.add_hotkey('ctrl+alt+q', self.quit_app)        # 退出程序

        print("热键: Ctrl+Alt+O 显示/隐藏 | Ctrl+Alt+P 暂停/恢复 | Ctrl+Alt+Q 退出")

    def make_click_through(self):
        # 将 Qt 窗口设置为 OS 层面的透明可点穿
        hwnd = int(self.winId())
        GWL_EXSTYLE = -20
        WS_EX_LAYERED = 0x00080000
        WS_EX_TRANSPARENT = 0x00000020
        style = windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT)
        
    def toggle_overlay(self):
        self.visible_overlay = not self.visible_overlay
        if not self.visible_overlay:
            self.frame[:] = 0  # 清空画面
            self.update()
        print("Overlay 显示:", self.visible_overlay)

    def toggle_pause(self):
        self.paused = not self.paused
        print("推理暂停:", self.paused)

    def quit_app(self):
        QtWidgets.QApplication.quit()

    def update_frame(self):
        if not self.visible_overlay and self.paused:
            return  # 完全静止，省 CPU

        # 抓屏
        img = np.array(self.sct.grab(self.monitor))
        frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        # 推理
        overlay_img = np.zeros_like(self.frame)
        if self.visible_overlay and not self.paused:
            results = self.model.predict(frame, imgsz=320, conf=0.35, classes=[0], verbose=False)
            for r in results:
                if getattr(r, "boxes", None) is None:
                    continue
                for b in r.boxes.xyxy.cpu().numpy():
                    x1, y1, x2, y2 = b.astype(int)
                    w, h = x2 - x1, y2 - y1
                    head_x = x1 + w // 2
                    head_y = y1 + int(0.15 * h)
                    cv2.rectangle(overlay_img, (x1, y1), (x2, y2), (0, 180, 255, 255), 2)
                    cv2.circle(overlay_img, (head_x, head_y), 5, (0, 255, 0, 255), -1)

        self.frame = overlay_img
        self.update()

    def paintEvent(self, event):
        if self.frame is None:
            return
        painter = QtGui.QPainter(self)
        img = QtGui.QImage(self.frame.data, self.frame.shape[1], self.frame.shape[0],
                           QtGui.QImage.Format.Format_BGR888)
        
        painter.drawImage(0, 0, img)

def main():
    app = QtWidgets.QApplication(sys.argv)

    selector = RegionSelector()
    # 用一个容器保存引用，防止被回收
    windows = {}

    def start_overlay(region):
        model = YOLO("yolov8n.pt")
        overlay = OverlayWindow(region, model)
        # 保存引用
        overlay.show()
        windows['overlay'] = overlay
        selector.deleteLater()

    selector.region_selected.connect(start_overlay)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
