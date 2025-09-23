install ultralytics with no dependencies to reduce size when no GPU is available

opencv-python-headless==4.8.1.78
numpy==1.26.0
matplotlib>=3.3.0
opencv-python>=4.6.0
pillow>=7.1.2
pyyaml>=5.3.1
requests>=2.23.0
scipy>=1.4.1
tqdm>=4.64.0
pandas>=1.1.4
psutil
dill
py-cpuinfo

and this line added in my dockerfile:
#Install torch and torchvision CPU only versions
RUN pip3 install torch==1.8.0+cpu torchvision==0.9.0+cpu -f https://download.pytorch.org/whl/cpu/torch_stable.html

#Explicitly install ultralytics without optional dependencies (like CUDA).
RUN pip3 install ultralytics==8.0.200 --no-deps
