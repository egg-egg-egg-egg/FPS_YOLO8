import sys, time
import numpy as np
import cv2
from mss import mss
from ultralytics import YOLO
from PyQt5 import QtWidgets, QtCore, QtGui

class OverlayWindow(QtWidgets.QWidget):
    def __init__(self, monitor, model):
        super().__init__()
        self.monitor = monitor
        self.model = model
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.Tool
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        # 鼠标穿透
        self.setWindowFlag(QtCore.Qt.WindowTransparentForInput)
        self.setGeometry(
            monitor["left"], monitor["top"],
            monitor["width"], monitor["height"]
        )
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_frame)
        self.sct = mss()
        self.frame = None
        self.timer.start(30)  # 约 ~33 FPS

    def update_frame(self):
        img = np.array(self.sct.grab(self.monitor))
        frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        results = self.model.predict(
            frame, imgsz=320, conf=0.35, classes=[0], verbose=False
        )
        overlay_img = np.zeros((self.monitor["height"], self.monitor["width"], 4), dtype=np.uint8)
        for r in results:
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
        if self.frame is None: return
        painter = QtGui.QPainter(self)
        img = QtGui.QImage(
            self.frame.data, self.frame.shape[1], self.frame.shape[0],
            QtGui.QImage.Format_RGBA8888
        )
        painter.drawImage(0, 0, img)

# 简单鼠标选区
class RegionSelector(QtWidgets.QWidget):
    region_selected = QtCore.pyqtSignal(dict)
    def __init__(self):
        super().__init__()
        self.start, self.end = None, None
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint)
        self.setWindowState(QtCore.Qt.WindowFullScreen)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.show()

    def mousePressEvent(self, e):
        self.start = e.pos()
    def mouseMoveEvent(self, e):
        self.end = e.pos()
        self.update()
    def mouseReleaseEvent(self, e):
        if self.start and self.end:
            x1, y1 = min(self.start.x(), self.end.x()), min(self.start.y(), self.end.y())
            x2, y2 = max(self.start.x(), self.end.x()), max(self.start.y(), self.end.y())
            region = {"top": y1, "left": x1, "width": x2-x1, "height": y2-y1}
            self.region_selected.emit(region)
            self.close()

    def paintEvent(self, e):
        if not self.start or not self.end: return
        painter = QtGui.QPainter(self)
        painter.setPen(QtGui.QPen(QtGui.QColor(0,200,255,200), 2))
        painter.setBrush(QtGui.QBrush(QtGui.QColor(0,200,255,50)))
        rect = QtCore.QRect(self.start, self.end)
        painter.drawRect(rect)

def main():
    app = QtWidgets.QApplication(sys.argv)
    selector = RegionSelector()

    def start_overlay(region):
        model = YOLO("yolov8n.pt")  # 可换成你的头部模型
        overlay = OverlayWindow(region, model)
        overlay.show()
        selector.deleteLater()

    selector.region_selected.connect(start_overlay)
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
