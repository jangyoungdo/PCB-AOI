from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                           QLineEdit, QPushButton, QLabel, QMessageBox,
                           QFormLayout, QTableWidget, QTableWidgetItem, QFrame)
from PyQt5.QtCore import Qt
from datetime import datetime
from manager.db_manager import DBManager

class EquipmentRegisterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("장비 등록")
        self.setModal(True)
        self.equipment_data = None
        self.db_manager = DBManager()
        self.db_manager.db_error.connect(self.show_db_error)
        self.db_manager.db_changed.connect(self.load_equipment_list)
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
        self.equipment_id = QLineEdit()
        self.equipment_name = QLineEdit()
        self.manager = QLineEdit()

        form_layout.addRow("장비 ID:", self.equipment_id)
        form_layout.addRow("장비 이름:", self.equipment_name)
        form_layout.addRow("관리자:", self.manager)
        
        register_layout.addLayout(form_layout)
        
        # 저장 버튼
        button_layout = QHBoxLayout()
        save_button = QPushButton("저장")
        save_button.clicked.connect(self.save_equipment)
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
        
        # 장비 목록 테이블
        list_label = QLabel("등록된 장비 목록")
        list_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        list_layout.addWidget(list_label)
        
        self.equipment_table = QTableWidget()
        self.equipment_table.setColumnCount(5)
        self.equipment_table.setHorizontalHeaderLabels(['장비 ID', '장비명', '관리자', '등록일', '최종 수정일'])
        self.equipment_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.equipment_table.setSelectionMode(QTableWidget.SingleSelection)
        self.equipment_table.itemDoubleClicked.connect(self.select_equipment)
        
        # 테이블 스타일 설정
        self.equipment_table.setStyleSheet("""
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
        
        list_layout.addWidget(self.equipment_table)
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
        
        # 장비 목록 로드
        self.load_equipment_list()
        
    def load_equipment_list(self):
        """등록된 장비 목록을 테이블에 로드"""
        equipments = self.db_manager.get_all_equipments()
        self.equipment_table.setRowCount(len(equipments))
        
        for row, equipment in enumerate(equipments):
            self.equipment_table.setItem(row, 0, QTableWidgetItem(equipment['equipment_id']))
            self.equipment_table.setItem(row, 1, QTableWidgetItem(equipment['equipment_name']))
            self.equipment_table.setItem(row, 2, QTableWidgetItem(equipment['manager']))
            self.equipment_table.setItem(row, 3, QTableWidgetItem(str(equipment['reg_date'])))
            self.equipment_table.setItem(row, 4, QTableWidgetItem(str(equipment['last_update'])))
            
        self.equipment_table.resizeColumnsToContents()
        
    def select_equipment(self, item):
        """테이블에서 장비 선택 시 처리"""
        row = item.row()
        self.equipment_data = {
            'equipment_id': self.equipment_table.item(row, 0).text(),
            'equipment_name': self.equipment_table.item(row, 1).text(),
            'manager': self.equipment_table.item(row, 2).text()
        }
        self.accept()

    def save_equipment(self):
        """새 장비 정보 저장"""
        if not self.equipment_id.text().strip() or not self.equipment_name.text().strip():
            QMessageBox.warning(self, "입력 오류", "장비 ID와 장비 이름은 필수 입력 항목입니다.")
            return

        equipment_data = {
            'equipment_id': self.equipment_id.text().strip(),
            'reg_date': datetime.now().date(),
            'equipment_name': self.equipment_name.text().strip(),
            'manager': self.manager.text().strip(),
            'last_update': datetime.now()
        }
        
        if self.db_manager.insert_equipment(equipment_data):
            self.equipment_data = equipment_data
            self.load_equipment_list()  # 목록 갱신
            # 입력 필드 초기화
            self.equipment_id.clear()
            self.equipment_name.clear()
            self.manager.clear()
            QMessageBox.information(self, "저장 완료", "장비 정보가 저장되었습니다.")
        else:
            QMessageBox.critical(self, "저장 오류", "장비 정보를 DB에 저장하는 중 오류가 발생했습니다.") 

    def show_db_error(self, error_msg):
        QMessageBox.critical(self, "DB 오류", error_msg) 