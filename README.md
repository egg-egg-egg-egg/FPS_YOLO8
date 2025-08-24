# **纯 CPU 环境安装指南**
---

## **1️⃣ 安装 mamba（conda 加速版）**
```bash
# 先确保已装 Anaconda / Miniconda
conda install -n base -c conda-forge mamba
```

---

## **2️⃣ 创建 CPU 深度学习环境**
> 这里的 `pytorch` 会自动装成 CPU 版本，无需 CUDA
```bash
mamba create -n screen_ai_cpu python=3.10 pytorch torchvision torchaudio cpuonly -c pytorch
```

---

## **3️⃣ 激活环境**
```bash
conda activate screen_ai_cpu
```

---

## **4️⃣ 安装屏幕采集 & 检测依赖**
```bash
pip install ultralytics mss opencv-python pyautogui
```

---

## **5️⃣ 运行检测 Demo**
- 直接用我之前给你的 `screen_detect.py`  
- 如果推理很慢，可以：
  - 调低 `imgsz=640` → `imgsz=320` 或 `imgsz=256`  
  - 选择更小的模型（`yolov8n.pt` 是最小的）  
  - 限制截屏区域尺寸

---

💡 **小优化建议（CPU 模式）：**  
1. **限制检测区域** → 只截取你需要的位置  
2. **批量推理** → 多帧合并做检测（适合低刷新场景）  
3. **模型量化** → 后续可用 `export` 导出 ONNX + INT8 量化，加速不少  

---