from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QPushButton, QTextEdit, QFrame)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap
import cv2

class ROIDetailDialog(QDialog):
    def __init__(self, roi_image, roi_name, results, parent=None):
        super().__init__(parent)
        self.roi_image = roi_image
        self.roi_name = roi_name
        self.results = results if results else {}
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle(f"검사 결과 상세 - {self.roi_name}")
        self.setGeometry(100, 100, 900, 700)
        
        main_layout = QHBoxLayout()
        
        # 왼쪽 프레임 (ROI 이미지)
        left_frame = QFrame()
        left_frame.setFrameShape(QFrame.StyledPanel)
        left_layout = QVBoxLayout(left_frame)
        
        # ROI 이미지 표시
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(580, 580)
        left_layout.addWidget(self.image_label)
        
        # 이미지 정보 표시
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel(f"ROI 이름: {self.roi_name}"))
        info_layout.addWidget(QLabel(f"크기: {self.roi_image.shape[1]}x{self.roi_image.shape[0]}"))
        left_layout.addLayout(info_layout)
        
        # 오른쪽 프레임 (결과 상세)
        right_frame = QFrame()
        right_frame.setFrameShape(QFrame.StyledPanel)
        right_layout = QVBoxLayout(right_frame)
        
        # 결과 텍스트
        result_text = QTextEdit()
        result_text.setReadOnly(True)
        
        # 결과 정보 구성
        text_content = f"ROI 이름: {self.roi_name}\n"
        text_content += "-" * 30 + "\n\n"
        
        # 각 알고리즘 결과 추가
        for algorithm, values in self.results.items():
            text_content += f"[{algorithm.upper()}]\n"
            if algorithm == "hsv":
                ref_rate, target_rate, is_pass = values
                text_content += f"기준값: {ref_rate:.2f}%\n"
                text_content += f"측정값: {target_rate:.2f}%\n"
            else:
                accuracy, is_pass = values
                text_content += f"정확도: {accuracy:.2f}%\n"
            
            text_content += f"결과: {'통과' if is_pass else '불통과'}\n"
            text_content += "-" * 30 + "\n\n"
        
        # 텍스트 설정
        result_text.setText(text_content)
        result_text.setStyleSheet("""
            QTextEdit {
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 14px;
                line-height: 1.5;
            }
        """)
        
        right_layout.addWidget(result_text)
        
        # 닫기 버튼
        close_button = QPushButton("닫기")
        close_button.clicked.connect(self.accept)
        right_layout.addWidget(close_button)
        
        # 메인 레이아웃에 프레임 추가
        main_layout.addWidget(left_frame)
        main_layout.addWidget(right_frame)
        
        self.setLayout(main_layout)
        
        # 이미지 표시
        self.update_image()
        
    def update_image(self):
        if self.roi_image is None:
            return
            
        try:
            # 600x600 크기로 이미지 리사이즈
            resized = cv2.resize(self.roi_image, (580, 580))
            
            # BGR to RGB 변환
            rgb_image = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
            
            # QImage 생성
            h, w, ch = rgb_image.shape
            bytes_per_line = ch * w
            qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            
            # QPixmap으로 변환 및 표시
            pixmap = QPixmap.fromImage(qt_image)
            self.image_label.setPixmap(pixmap)
            
        except Exception as e:
            print(f"이미지 업데이트 중 오류 발생: {str(e)}") 