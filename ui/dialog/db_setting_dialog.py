from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                           QLabel, QLineEdit, QGroupBox, QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt
import sqlite3
import os
from manager.db_manager import DBManager

class DBSettingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_manager = DBManager()
        self.db_path = self.db_manager.db_path
        self.initUI()

    def initUI(self):
        self.setWindowTitle('DB 설정')
        self.setFixedSize(400, 250)  # 높이 증가

        layout = QVBoxLayout()

        # DB 파일 설정 그룹
        dbGroup = QGroupBox('데이터베이스 설정')
        dbLayout = QVBoxLayout()

        # DB 파일 경로 설정
        pathLayout = QHBoxLayout()
        pathLabel = QLabel('DB 파일 경로:')
        self.pathEdit = QLineEdit()
        self.pathEdit.setReadOnly(True)
        browseButton = QPushButton('찾아보기')
        browseButton.clicked.connect(self.browsePath)
        pathLayout.addWidget(pathLabel)
        pathLayout.addWidget(self.pathEdit)
        pathLayout.addWidget(browseButton)
        dbLayout.addLayout(pathLayout)

        # 파일 생성/초기화 버튼 그룹
        fileButtonLayout = QHBoxLayout()
        createButton = QPushButton('DB 파일 생성')
        initButton = QPushButton('DB 초기화')
        createButton.clicked.connect(self.createDB)
        initButton.clicked.connect(self.initializeDB)
        fileButtonLayout.addWidget(createButton)
        fileButtonLayout.addWidget(initButton)
        dbLayout.addLayout(fileButtonLayout)

        dbGroup.setLayout(dbLayout)
        layout.addWidget(dbGroup)

        # 하단 버튼
        buttonLayout = QHBoxLayout()
        saveButton = QPushButton('저장')
        cancelButton = QPushButton('취소')
        saveButton.clicked.connect(self.accept)
        cancelButton.clicked.connect(self.reject)
        buttonLayout.addWidget(saveButton)
        buttonLayout.addWidget(cancelButton)
        layout.addLayout(buttonLayout)

        self.setLayout(layout)

        # 현재 DB 경로 표시
        self.pathEdit.setText(self.db_path)
        
        if self.db_path == self.db_manager.DEFAULT_DB_PATH:
            self.pathEdit.setPlaceholderText("(기본 DB 사용 중)")

    def browsePath(self):
        """DB 파일 경로 선택"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "DB 파일 선택",
            "",
            "SQLite DB Files (*.db);;All Files (*)"
        )
        if file_path:
            self.db_path = file_path
            self.pathEdit.setText(file_path)

    def createDB(self):
        """새 DB 파일 생성"""
        if not self.db_path:
            QMessageBox.warning(self, "경고", "DB 파일 경로를 선택해주세요.")
            return

        try:
            # 파일이 이미 존재하는지 확인
            if os.path.exists(self.db_path):
                reply = QMessageBox.question(
                    self,
                    "확인",
                    "이미 존재하는 파일입니다. 덮어쓰시겠습니까?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return

            # 빈 DB 파일 생성
            conn = sqlite3.connect(self.db_path)
            conn.close()

            reply = QMessageBox.question(
                self,
                "확인",
                "DB 파일이 생성되었습니다. 테이블을 초기화하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            
            if reply == QMessageBox.Yes:
                self.initializeDB()
            else:
                QMessageBox.information(self, "알림", "빈 DB 파일이 생성되었습니다.")

        except sqlite3.Error as e:
            QMessageBox.critical(self, "오류", f"DB 파일 생성 중 오류가 발생했습니다: {str(e)}")

    def initializeDB(self):
        """DB 초기화 및 테이블 생성"""
        if not self.db_path:
            QMessageBox.warning(self, "경고", "DB 파일 경로를 선택해주세요.")
            return

        if not os.path.exists(self.db_path):
            QMessageBox.warning(self, "경고", "DB 파일이 존재하지 않습니다. 먼저 파일을 생성해주세요.")
            return

        reply = QMessageBox.question(
            self,
            "확인",
            "데이터베이스를 초기화하면 모든 데이터가 삭제됩니다. 계속하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.No:
            return

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 기존 테이블 삭제
            cursor.executescript('''
                DROP TABLE IF EXISTS inspection_result_table;
                DROP TABLE IF EXISTS production_table;
                DROP TABLE IF EXISTS product_table;
                DROP TABLE IF EXISTS equipment_table;
            ''')

            # 테이블 재생성
            cursor.executescript('''
                -- 장비 테이블
                CREATE TABLE IF NOT EXISTS equipment_table (
                    equipment_id TEXT PRIMARY KEY,
                    reg_date DATE,
                    equipment_name TEXT,
                    manager TEXT,
                    last_update TIMESTAMP
                );

                -- 제품 테이블
                CREATE TABLE IF NOT EXISTS product_table (
                    product_id TEXT PRIMARY KEY,
                    reg_date DATE,
                    product_name TEXT,
                    last_update TIMESTAMP,
                    test_items TEXT,
                    roi_settings TEXT DEFAULT '{}'  -- ROI 설정 추가
                );

                -- 생산 기록 테이블
                CREATE TABLE IF NOT EXISTS production_table (
                    production_date DATE,
                    product_id TEXT,
                    equipment_id TEXT,
                    production_count INTEGER DEFAULT 0,
                    defect_count INTEGER DEFAULT 0,
                    PRIMARY KEY (production_date, product_id, equipment_id),
                    FOREIGN KEY (product_id) REFERENCES product_table(product_id),
                    FOREIGN KEY (equipment_id) REFERENCES equipment_table(equipment_id)
                );

                -- 검사 결과 테이블
                CREATE TABLE IF NOT EXISTS inspection_result_table (
                    result_id TEXT PRIMARY KEY,
                    production_date DATE,
                    product_id TEXT,
                    equipment_id TEXT,
                    inspection_datetime TIMESTAMP,
                    roi_results TEXT,
                    image_path TEXT,
                    overall_result TEXT,
                    FOREIGN KEY (production_date, product_id, equipment_id) 
                        REFERENCES production_table(production_date, product_id, equipment_id)
                );
            ''')

            conn.commit()
            conn.close()

            QMessageBox.information(self, "성공", "데이터베이스가 성공적으로 초기화되었습니다.")

        except sqlite3.Error as e:
            QMessageBox.critical(self, "오류", f"데이터베이스 초기화 중 오류가 발생했습니다: {str(e)}")

    def accept(self):
        """설정 저장 및 다이얼로그 종료"""
        if self.db_path and self.db_path != self.db_manager.db_path:
            self.db_manager.change_db(self.db_path)
        super().accept()

    def get_db_path(self):
        """설정된 DB 파일 경로 반환"""
        return self.db_path 