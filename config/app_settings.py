import os
import platform

# 시스템별 폰트 경로 설정
if platform.system() == 'Windows':
    FONT_PATHS = [
        "malgun.ttf",
        os.path.join(os.environ.get('SystemRoot', 'C:/Windows'), 'Fonts/malgun.ttf'),
        os.path.join(os.environ.get('SystemRoot', 'C:/Windows'), 'Fonts/gulim.ttc')
    ]
elif platform.system() == 'Linux':
    FONT_PATHS = [
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/usr/share/fonts/truetype/korean/UnGraphic.ttf"
    ]
elif platform.system() == 'Darwin':  # macOS
    FONT_PATHS = [
        "/Library/Fonts/AppleGothic.ttf",
        "/System/Library/Fonts/AppleGothic.ttf"
    ]
else:
    FONT_PATHS = ["malgun.ttf"]

# 폰트 크기 설정
FONT_SIZES = {
    'small': 12,
    'normal': 20,
    'large': 32
} 