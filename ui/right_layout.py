from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, 
                           QFrame, QScrollArea, QGridLayout)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont

class ROIDetailWidget(QFrame):
    def __init__(self, name, results):
        super().__init__()
        self.name = name
        self.results = results
        self.is_expanded = False
        self.initUI()
        
    def initUI(self):
        layout = QVBoxLayout()
        
        # ROI 헤더 (클릭 가능한 버튼)
        self.header_btn = QPushButton(self.name)
        self.header_btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 10px;
                background-color: #f5f5f5;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        self.header_btn.clicked.connect(self.toggle_content)
        layout.addWidget(self.header_btn)
        
        # 상세 내용을 담을 컨테이너
        self.content = QFrame()
        self.content.setVisible(False)
        content_layout = QGridLayout()
        
        # 알고리즘별 결과 표시
        row = 0
        for algorithm, values in self.results.items():
            # 알고리즘 이름
            algo_label = QLabel(algorithm.upper())
            algo_label.setStyleSheet("font-weight: bold; padding: 5px;")
            content_layout.addWidget(algo_label, row, 0)
            
            # HSV 알고리즘인 경우
            if algorithm == "hsv":
                ref_rate, target_rate, is_pass = values
                accuracy = target_rate  # target_rate를 정확도로 사용
                threshold = ref_rate    # ref_rate를 임계값으로 사용
            else:
                # 다른 알고리즘들
                accuracy, is_pass = values
                threshold = 50.0  # 임계값 표시용
            
            # 정확도
            accuracy_label = QLabel(f"{accuracy:.1f}%")
            content_layout.addWidget(accuracy_label, row, 1)
            
            # 임계값
            threshold_label = QLabel(f"임계값: {threshold:.1f}%")
            content_layout.addWidget(threshold_label, row, 2)
            
            # 결과 (알고리즘에서 반환된 is_pass 값 사용)
            result_label = QLabel("통과" if is_pass else "불통과")
            result_label.setStyleSheet(f"""
                color: {'#4CAF50' if is_pass else '#f44336'};
                font-weight: bold;
            """)
            content_layout.addWidget(result_label, row, 3)
            row += 1
            
        self.content.setLayout(content_layout)
        self.content.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                margin-left: 20px;
            }
        """)
        layout.addWidget(self.content)
        self.setLayout(layout)
        
    def toggle_content(self):
        self.is_expanded = not self.is_expanded
        self.content.setVisible(self.is_expanded)

class RightLayout(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()
        
        # ROI 상세 정보를 담을 스크롤 영역
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
            }
        """)
        
        self.roi_container = QWidget()
        self.roi_layout = QVBoxLayout()
        self.roi_container.setLayout(self.roi_layout)
        scroll.setWidget(self.roi_container)
        layout.addWidget(scroll)
        
        self.setLayout(layout)

    def update_inspection_results(self, results):
        # 기존 ROI 위젯들 제거
        for i in reversed(range(self.roi_layout.count())): 
            self.roi_layout.itemAt(i).widget().setParent(None)
        
        # ROI별 상세 정보 위젯 추가
        for result in results:
            roi_widget = ROIDetailWidget(result['name'], result['results'])
            self.roi_layout.addWidget(roi_widget) 