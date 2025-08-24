import sys
import time
import platform
import numpy as np
import cv2
from mss import mss
from ultralytics import YOLO
from PyQt5 import QtWidgets, QtCore, QtGui
import keyboard

# Windows 鼠标穿透支持
if platform.system() == "Windows":
    from ctypes import windll

# ===============================
# 全局配置
# ===============================
MODEL_PATH = "yolov8n.pt"
MODEL_CONF = 0.35
MODEL_IMGSZ = 320
MODEL_CLASSES = [0]  # 仅检测人物
FPS = 20  # 推理帧率

HOTKEYS = {
    "overlay": "ctrl+alt+o",
    "pause":   "ctrl+alt+p",
    "quit":    "ctrl+alt+q"
}

# 高 DPI 设置
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)


def get_virtual_geometry():
    """计算多显示器下的虚拟桌面范围"""
    rects = [screen.geometry() for screen in QtWidgets.QApplication.screens()]
    left = min(r.left() for r in rects)
    top = min(r.top() for r in rects)
    right = max(r.right() for r in rects)
    bottom = max(r.bottom() for r in rects)
    return QtCore.QRect(left, top, right - left + 1, bottom - top + 1)


class RegionSelector(QtWidgets.QWidget):
    """矩形选区选择器（半透明覆盖层）"""
    region_selected = QtCore.pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        self.start = None
        self.end = None
        self.vgeo = get_virtual_geometry()

        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
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
            self._confirm_selection()

    def keyPressEvent(self, e):
        if e.key() == QtCore.Qt.Key_Escape:
            self.close()
        elif e.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            if self.start and self.end:
                self._confirm_selection()

    def _confirm_selection(self):
        """确认选区并发出信号"""
        x1, y1 = min(self.start.x(), self.end.x()), min(self.start.y(), self.end.y())
        x2, y2 = max(self.start.x(), self.end.x()), max(self.start.y(), self.end.y())

        if x2 - x1 < 5 or y2 - y1 < 5:
            return

        region = {
            "left": self.vgeo.left() + x1,
            "top": self.vgeo.top() + y1,
            "width": x2 - x1,
            "height": y2 - y1
        }
        self.region_selected.emit(region)
        self.close()

    def paintEvent(self, e):
        """绘制半透明遮罩和选区边框"""
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), QtGui.QColor(0, 0, 0, 120))
        if self.start and self.end:
            rect = QtCore.QRect(self.start, self.end).normalized()
            painter.setCompositionMode(QtGui.QPainter.CompositionMode_Clear)
            painter.fillRect(rect, QtCore.Qt.transparent)
            painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceOver)

            pen = QtGui.QPen(QtGui.QColor(0, 200, 255, 220), 2)
            painter.setPen(pen)
            painter.drawRect(rect)

            label = f"{rect.width()} x {rect.height()}"
            painter.setPen(QtGui.QColor(255, 255, 255, 230))
            painter.drawText(rect.topLeft() + QtCore.QPoint(8, -8), label)


class InferenceThread(QtCore.QThread):
    frame_ready = QtCore.pyqtSignal(np.ndarray)

    def __init__(self, monitor, model):
        super().__init__()
        self.monitor = monitor
        self.model = model
        self.running = True
        self.paused = False
        self.visible = True
        self.last_frame = None  # 存储最后一帧

    def run(self):
        sct = mss()
        while self.running:
            try:
                start_time = time.time()

                if self.paused or not self.visible:
                    # 保留之前的画面
                    if self.last_frame is not None:
                        self.frame_ready.emit(self.last_frame)
                    time.sleep(1/FPS)
                    continue

                # 正常抓屏
                img = np.array(sct.grab(self.monitor))
                frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                overlay = np.zeros_like(frame)

                # 推理
                results = self.model.predict(
                    frame, imgsz=MODEL_IMGSZ, conf=MODEL_CONF, classes=MODEL_CLASSES, verbose=False
                )
                for r in results:
                    if getattr(r, "boxes", None) is None:
                        continue
                    for b in r.boxes.xyxy.cpu().numpy():
                        x1, y1, x2, y2 = b.astype(int)
                        w, h = x2 - x1, y2 - y1
                        head_x = x1 + w // 2
                        head_y = y1 + int(0.15 * h)
                        cv2.rectangle(overlay, (x1, y1), (x2, y2), (0, 180, 255), 2)
                        cv2.circle(overlay, (head_x, head_y), 5, (0, 255, 0), -1)

                self.last_frame = overlay
                self.frame_ready.emit(self.last_frame)

                elapsed = time.time() - start_time
                time.sleep(max(0, 1/FPS - elapsed))

            except Exception as e:
                print(f"[警告] 推理线程异常: {e}")
                time.sleep(0.5)  # 等待片刻后重试



class OverlayWindow(QtWidgets.QWidget):
    """检测结果叠加显示窗口"""
    def __init__(self, monitor, model):
        super().__init__()
        self.frame = np.zeros((monitor["height"], monitor["width"], 3), dtype=np.uint8)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setGeometry(monitor["left"], monitor["top"], monitor["width"], monitor["height"])
        self.show()

        if platform.system() == "Windows":
            hwnd = int(self.winId())
            GWL_EXSTYLE = -20
            WS_EX_LAYERED = 0x00080000
            WS_EX_TRANSPARENT = 0x00000020
            style = windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT)

        # 启动推理线程
        self.thread = InferenceThread(monitor, model)
        self.thread.frame_ready.connect(self.update_frame)
        self.thread.start()

        # 热键绑定
        keyboard.add_hotkey(HOTKEYS["overlay"], self.toggle_overlay)
        keyboard.add_hotkey(HOTKEYS["pause"], self.toggle_pause)
        keyboard.add_hotkey(HOTKEYS["quit"], self.quit_app)

        print(f"热键绑定: {HOTKEYS}")

    def update_frame(self, frame):
        self.frame = frame
        self.update()

    def toggle_overlay(self):
        self.thread.visible = not self.thread.visible
        print("Overlay 显示:", self.thread.visible)

    def toggle_pause(self):
        self.thread.paused = not self.thread.paused
        print("推理暂停:", self.thread.paused)

    def quit_app(self):
        self.thread.running = False
        QtWidgets.QApplication.quit()

    def paintEvent(self, event):
        """绘制叠加层图像"""
        if self.frame is None:
            return
        painter = QtGui.QPainter(self)
        img = QtGui.QImage(
            self.frame.data,
            self.frame.shape[1],
            self.frame.shape[0],
            QtGui.QImage.Format_BGR888
        )
        painter.drawImage(0, 0, img)


def main():
    """程序入口"""
    app = QtWidgets.QApplication(sys.argv)

    # 预加载 YOLO 模型，避免重复加载
    print("正在加载模型，请稍候...")
    model = YOLO(MODEL_PATH)
    print("模型加载完成。")

    selector = RegionSelector()
    windows = {}  # 防止对象被垃圾回收

    def start_overlay(region):
        overlay = OverlayWindow(region, model)
        windows['overlay'] = overlay
        selector.deleteLater()

    selector.region_selected.connect(start_overlay)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
