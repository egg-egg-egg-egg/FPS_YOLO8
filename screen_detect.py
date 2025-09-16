import time
import cv2
import numpy as np
from mss import mss
from region_picker import pick_region
from person_detector import PersonDetector
from mouse_control import move_mouse_absolute,move_mouse_relative

def main():
    # 1) 点选区域
    monitor = pick_region()
    if not monitor:
        print("取消选择，退出。")
        return
    print("选区：", monitor)

    # 2) 初始化检测器
    detector = PersonDetector()

    # 3) 截屏 + 推理
    prev = time.time()
    with mss() as sct:
        while True:
            # 获取并处理截图
            shot = sct.grab(monitor)
            frame = np.array(shot)[:, :, :3]
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

            # 检测人物
            frame, detections = detector.detect(frame)
            # 绘制检测框和头部位置
            for head_x, head_y, x1, y1, x2, y2 in detections:
                move_mouse_absolute(head_x, head_y, duration=0.2)
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 180, 255), 2)
                cv2.circle(frame, (head_x, head_y), 6, (0, 255, 0), -1)
            # 显示FPS
            now = time.time()
            fps = 1.0 / (now - prev)
            prev = now
            cv2.putText(frame, f"FPS: {fps:.1f}", (10, 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 255, 50), 2)

            # 显示结果
            cv2.imshow("Screen detection (selected region)", frame)
            if cv2.waitKey(1) & 0xFF == 27:
                break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()