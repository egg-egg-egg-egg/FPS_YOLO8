# screen_detect_select.py
# pip install ultralytics mss opencv-python

import time
import cv2
import numpy as np
from mss import mss
from ultralytics import YOLO
from region_picker import pick_region

def main():
    # 1) 点选区域
    monitor = pick_region()
    if not monitor:
        print("取消选择，退出。")
        return
    print("选区：", monitor)

    # 2) 加载模型（CPU 也可跑）
    model = YOLO("yolov8n.pt")

    # 3) 截屏 + 推理
    prev = time.time()
    with mss() as sct:
        while True:
            shot = sct.grab(monitor)
            frame = np.array(shot)[:, :, :3]
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

            # 可调 imgsz 以加速：320/416/512
            results = model.predict(
                frame, imgsz=416, conf=0.35, iou=0.45, classes=[0], verbose=False
            )

            for r in results:
                if r.boxes is None: 
                    continue
                for b in r.boxes.xyxy.cpu().numpy():
                    x1, y1, x2, y2 = b.astype(int) # x1,y1 左上角坐标，x2,y2 右下角坐标 坐标系是easyx那种
                    w, h = x2 - x1, y2 - y1
                    # 计算头部坐标
                    head_x = x1 + w // 2  
                    head_y = y1 + int(0.15 * h)
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 180, 255), 2) # 绘制矩形
                    cv2.circle(frame, (head_x, head_y), 6, (0, 255, 0), -1)    # 绘制圆

            now = time.time()
            fps = 1.0 / (now - prev)
            prev = now
            cv2.putText(frame, f"FPS: {fps:.1f}", (10, 24),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 255, 50), 2)

            cv2.imshow("Screen detection (selected region)", frame)
            if cv2.waitKey(1) & 0xFF == 27:
                break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
