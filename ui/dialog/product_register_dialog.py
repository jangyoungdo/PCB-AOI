from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                           QLineEdit, QPushButton, QLabel, QMessageBox,
                           QFormLayout, QTableWidget, QTableWidgetItem, QFrame)
from PyQt5.QtCore import Qt
from manager.db_manager import DBManager
from datetime import datetime

class ProductRegisterDialog(QDialog):
    def __init__(self, parent=None, equipment_id=None):
        super().__init__(parent)
        self.setWindowTitle("제품 등록")
        self.setModal(True)
        self.product_data = None
        self.equipment_id_value = equipment_id
        self.db_manager = DBManager()
        self.db_manager.db_error.connect(self.show_db_error)
        self.db_manager.db_changed.connect(self.load_product_list)
        self.initUI()
        
    def initUI(self):
        self.setMinimumSize(600, 800)
        main_layout = QVBoxLayout()
        
        # 상단 등록 영역
        top_frame = QFrame()
        top_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        top_frame.setStyleSheet("""
            QFrame {
                background-color: #f5f5f5;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        
        register_layout = QVBoxLayout(top_frame)
        form_layout = QFormLayout()

        # 입력 필드들
        self.product_id = QLineEdit()
        self.equipment_id = QLineEdit()
        self.equipment_id.setReadOnly(True)
        if self.equipment_id_value:
            self.equipment_id.setText(self.equipment_id_value)
        self.product_name = QLineEdit()

        form_layout.addRow("생산품 ID:", self.product_id)
        form_layout.addRow("장비 ID:", self.equipment_id)
        form_layout.addRow("생산품명:", self.product_name)
        
        register_layout.addLayout(form_layout)
        
        # 버튼 영역
        button_layout = QHBoxLayout()
        save_button = QPushButton("저장")
        save_button.clicked.connect(self.save_product)
        save_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border-radius: 3px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        button_layout.addWidget(save_button)
        register_layout.addLayout(button_layout)
        
        main_layout.addWidget(top_frame)
        
        # 하단 목록 영역
        bottom_frame = QFrame()
        bottom_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        bottom_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        
        list_layout = QVBoxLayout(bottom_frame)
        
        # 제품 목록 테이블
        list_label = QLabel("등록된 제품 목록")
        list_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        list_layout.addWidget(list_label)
        
        self.product_table = QTableWidget()
        self.product_table.setColumnCount(4)
        self.product_table.setHorizontalHeaderLabels(['제품 ID', '제품명', '등록일', '최종 수정일'])
        self.product_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.product_table.setSelectionMode(QTableWidget.SingleSelection)
        self.product_table.itemDoubleClicked.connect(self.select_product)
        
        # 테이블 스타일 설정
        self.product_table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #ddd;
                border-radius: 3px;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 5px;
                border: 1px solid #ddd;
            }
        """)
        
        list_layout.addWidget(self.product_table)
        main_layout.addWidget(bottom_frame)
        
        # 닫기 버튼
        close_button = QPushButton("닫기")
        close_button.clicked.connect(self.reject)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border-radius: 3px;
                padding: 5px 15px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        main_layout.addWidget(close_button)
        
        self.setLayout(main_layout)
        
        # 제품 목록 로드
        self.load_product_list()
        
    def load_product_list(self):
        """등록된 제품 목록을 테이블에 로드"""
        products = self.db_manager.get_all_products()  # DB에서 제품 목록 조회
        self.product_table.setRowCount(len(products))
        
        for row, product in enumerate(products):
            self.product_table.setItem(row, 0, QTableWidgetItem(product['product_id']))
            self.product_table.setItem(row, 1, QTableWidgetItem(product['product_name']))
            self.product_table.setItem(row, 2, QTableWidgetItem(str(product['reg_date'])))
            self.product_table.setItem(row, 3, QTableWidgetItem(str(product['last_update'])))
            
        self.product_table.resizeColumnsToContents()
        
    def select_product(self, item):
        """테이블에서 제품 선택 시 처리"""
        row = item.row()
        self.product_data = {
            'product_id': self.product_table.item(row, 0).text(),
            'product_name': self.product_table.item(row, 1).text()
        }
        self.accept()
        
    def save_product(self):
        """새 제품 정보 저장"""
        if not self.product_id.text().strip() or not self.product_name.text().strip():
            QMessageBox.warning(self, "입력 오류", "제품 ID와 제품 이름은 필수 입력 항목입니다.")
            return

        product_data = {
            'product_id': self.product_id.text().strip(),
            'reg_date': datetime.now().date(),
            'product_name': self.product_name.text().strip(),
            'last_update': datetime.now(),
            'test_items': '{}'
        }
        
        if self.db_manager.insert_product(product_data):
            self.product_data = product_data
            self.load_product_list()  # 목록 갱신
            self.product_id.clear()   # 입력 필드 초기화
            self.product_name.clear()
            QMessageBox.information(self, "저장 완료", "제품 정보가 저장되었습니다.")
        else:
            QMessageBox.critical(self, "저장 오류", "제품 정보를 DB에 저장하는 중 오류가 발생했습니다.") 

    def show_db_error(self, error_msg):
        QMessageBox.critical(self, "DB 오류", error_msg) 