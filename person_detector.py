import cv2
import numpy as np
from ultralytics import YOLO

class PersonDetector:
    def __init__(self, model_path="yolov8n.pt", imgsz=416, conf=0.35, iou=0.45):
        self.model = YOLO(model_path)
        self.imgsz = imgsz
        self.conf = conf
        self.iou = iou
        
    def detect(self, frame):
        """
        检测图像中的人物并返回结果
        Args:
            frame: BGR格式的图像
        Returns:
            处理后的图像和检测到的人物坐标列表 [(head_x, head_y, x1, y1, x2, y2), ...]
        """
        results = self.model.predict(
            frame, 
            imgsz=self.imgsz, 
            conf=self.conf, 
            iou=self.iou, 
            classes=[0],  # 只检测人
            verbose=False
        )
        
        detections = []
        for r in results:
            if r.boxes is None:
                continue
            for b in r.boxes.xyxy.cpu().numpy():
                x1, y1, x2, y2 = b.astype(int)
                w, h = x2 - x1, y2 - y1
                head_x = x1 + w // 2
                head_y = y1 + int(0.15 * h)
                
                # # 绘制检测框和头部位置
                # cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 180, 255), 2)
                # cv2.circle(frame, (head_x, head_y), 6, (0, 255, 0), -1)
                
                detections.append((head_x, head_y, x1, y1, x2, y2))
                
        return frame, detections