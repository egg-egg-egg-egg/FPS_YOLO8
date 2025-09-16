# mouse_simulator.py
from pynput.mouse import Controller
import time

# 创建鼠标控制器
mouse = Controller()

# 等待用户切换到目标窗口
print("请在 3 秒内切换到目标窗口...")
time.sleep(3)

# 获取当前鼠标位置
start_pos = mouse.position
print(f"起始位置: {start_pos}")

# 模拟鼠标移动：向右下方移动
for i in range(20):
    mouse.move(10, 5)  # 每次移动 10 像素横向，5 像素纵向
    time.sleep(0.05)

# 打印结束位置
end_pos = mouse.position
print(f"结束位置: {end_pos}")
