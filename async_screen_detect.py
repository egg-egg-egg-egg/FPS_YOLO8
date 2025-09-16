import asyncio
import time
import cv2
import numpy as np
from mss import mss
from region_picker import pick_region
from person_detector import PersonDetector
import queue
import threading

class AsyncScreenDetector:
    def __init__(self):
        self.detector = PersonDetector()
        self.frame_queue = asyncio.Queue(maxsize=3)
        self.result_queue = asyncio.Queue(maxsize=3)
        self.running = True
        
    async def capture_frame(self, monitor):
        """异步截图任务"""
        with mss() as sct:
            while self.running:
                shot = sct.grab(monitor)
                frame = np.array(shot)[:, :, :3]
                await self.frame_queue.put(frame)
                await asyncio.sleep(0.001)  # 让出控制权
                
    async def process_frame(self):
        """异步处理任务"""
        while self.running:
            if not self.frame_queue.empty():
                frame = await self.frame_queue.get()
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
                frame, detections = self.detector.detect(frame)
                await self.result_queue.put((frame, detections))
            await asyncio.sleep(0.001)  # 让出控制权
                
    async def display_results(self):
        """异步显示任务"""
        prev = time.time()
        while self.running:
            if not self.result_queue.empty():
                frame, _ = await self.result_queue.get()
                
                # 计算和显示FPS
                now = time.time()
                fps = 1.0 / (now - prev)
                prev = now
                cv2.putText(frame, f"FPS: {fps:.1f}", (10, 24),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (50, 255, 50), 2)
                
                cv2.imshow("Screen detection (selected region)", frame)
                if cv2.waitKey(1) & 0xFF == 27:
                    self.running = False
                    break
            await asyncio.sleep(0.001)  # 让出控制权

    async def run(self):
        # 选择区域
        monitor = pick_region()
        if not monitor:
            print("取消选择，退出。")
            return

        print("选区：", monitor)
        
        # 创建任务
        tasks = [
            asyncio.create_task(self.capture_frame(monitor)),
            asyncio.create_task(self.process_frame()),
            asyncio.create_task(self.display_results())
        ]
        
        # 等待所有任务完成
        await asyncio.gather(*tasks)
        cv2.destroyAllWindows()

async def main():
    detector = AsyncScreenDetector()
    await detector.run()

if __name__ == "__main__":
    asyncio.run(main())