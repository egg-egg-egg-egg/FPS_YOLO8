import sys
import ctypes
from PyQt5 import QtWidgets, QtCore, QtGui

# 高 DPI（可选）
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)
QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

class Overlay(QtWidgets.QWidget):
    def __init__(self, rect=None):
        super().__init__()
        # 无边框、置顶、工具窗（不占任务栏）
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint |
            QtCore.Qt.WindowStaysOnTopHint |
            QtCore.Qt.Tool
        )
        # 背景全透明
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        # 可选：Qt 层忽略鼠标（不是必须，真正点穿靠 Win32 样式）
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)

        # 覆盖范围：主屏全屏或自定义区域
        if rect is None:
            geo = QtWidgets.QApplication.primaryScreen().geometry()
            self.setGeometry(geo)
        else:
            self.setGeometry(rect[0], rect[1], rect[2], rect[3])

        # 小动画帮助确认确实在重绘
        self._t = 0
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(30)

        self.show()
        # 关键：Win32 层真正开启“输入透明”
        self._make_click_through()

    def _make_click_through(self):
        hwnd = int(self.winId())
        GWL_EXSTYLE = -20
        WS_EX_LAYERED = 0x00080000
        WS_EX_TRANSPARENT = 0x00000020
        user32 = ctypes.windll.user32
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED | WS_EX_TRANSPARENT)
        # 如需整体调整不透明度，可用 SetLayeredWindowAttributes，但这里我们只画半透明线条即可

    def _tick(self):
        self._t = (self._t + 1) % 400
        self.update()

    def paintEvent(self, e):
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing, True)
        w, h = self.width(), self.height()

        # 画四条线（十字准星）
        pen_cross = QtGui.QPen(QtGui.QColor(0, 255, 0, 180), 2)
        p.setPen(pen_cross)
        p.drawLine(0, h // 2, w, h // 2)
        p.drawLine(w // 2, 0, w // 2, h)

        # 画一个半透明圆圈（随时间小幅移动）
        r = 60
        cx = (w // 2) + (self._t - 200) // 4
        cy = (h // 2) + (self._t - 200) // 6
        pen_circle = QtGui.QPen(QtGui.QColor(255, 200, 0, 220), 3)
        p.setPen(pen_circle)
        p.setBrush(QtCore.Qt.NoBrush)
        p.drawEllipse(QtCore.QPoint(cx, cy), r, r)

def main():
    app = QtWidgets.QApplication(sys.argv)

    # A：全屏叠加
    overlay = Overlay()

    # B：指定区域叠加（解开用这个）
    # overlay = Overlay(rect=(100, 100, 800, 600))

    print("已显示透明叠加（十字 + 圆）。试着在其上点击/拖动下层窗口验证能否点穿。")
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
