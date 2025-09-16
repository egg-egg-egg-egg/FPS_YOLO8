"""
多线程加速
"""
import threading
import queue
import time
import cv2
import numpy as np
from mss import mss
from region_picker import pick_region
from person_detector import PersonDetector

class ScreenDetector:
    def __init__(self):
        self.frame_queue = queue.Queue(maxsize=2)
        self.result_queue = queue.Queue(maxsize=2)
        self.detector = PersonDetector()
        self.monitor = pick_region()
        if not self.monitor:
            print("取消选择，退出。")
            return
        print("选区：", self.monitor)
        
    def process_thread(self):
        while True:
            frame = self.frame_queue.get()
            if frame is None:
                break
            result = self.detector.detect(frame)
            self.result_queue.put(result)
            
    def run(self):
        # 启动处理线程
        thread = threading.Thread(target=self.process_thread)
        thread.start()
        
        with mss() as sct:
            while True:
                shot = sct.grab(self.monitor)
                frame = np.array(shot)[:, :, :3]
                
                # 非阻塞方式提交帧
                if not self.frame_queue.full():
                    self.frame_queue.put(frame)
                
                # 非阻塞方式获取结果
                try:
                    result = self.result_queue.get_nowait()
                    # 显示结果
                    cv2.imshow("result", result)
                except queue.Empty:
                    pass
                    
                if cv2.waitKey(1) & 0xFF == 27:
                    break

def main():
    detector = ScreenDetector()
    detector.run()

if __name__ == "__main__":
    main()