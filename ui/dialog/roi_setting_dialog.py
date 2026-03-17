from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton,
    QLabel, QMessageBox, QWidget, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt5.QtCore import Qt
from config.model_setting import ALGORITHM_PARAMETER  # 사용 가능한 알고리즘 목록
import json
import os
from utils.roi_utils import save_roi_settings, load_roi_settings
import numpy as np
from models.target import InspectionTarget  # 모듈 임포트 추가
from utils.json_utils import parse_json_safely

class ROISettingDialog(QDialog):
    def __init__(self, parent=None, target_manager=None, product_id=None, db_manager=None):
        super().__init__(parent)
        self.target_manager = target_manager
        self.product_id = product_id
        self.db_manager = db_manager
        self.selected_targets = []  # 현재 선택된 ROI들
        self.frame = None  # frame 속성 추가
        self.row_to_target_map = {}  # 초기화 추가
        
        # 부모 다이얼로그에서 frame 가져오기
        if parent and hasattr(parent, 'frame'):
            self.frame = parent.frame
        
        # MainWindow에서 카메라 프레임 가져오기 시도
        if self.frame is None:
            try:
                main_window = self
                while main_window.parent():
                    main_window = main_window.parent()
                    
                if hasattr(main_window, 'camera_manager'):
                    self.frame = main_window.camera_manager.get_current_frame()
                    print(f"카메라에서 프레임 가져옴: {self.frame.shape if self.frame is not None else 'None'}")
            except:
                print("카메라에서 프레임을 가져올 수 없습니다.")
        
        # 그래도 프레임이 없으면 기본 이미지 생성
        if self.frame is None:
            print("기본 이미지 생성 중...")
            # 검은색 빈 이미지 생성 (640x480)
            self.frame = np.zeros((480, 640, 3), dtype=np.uint8)
            print(f"기본 이미지 생성 완료: {self.frame.shape}")
        
        self.initUI()
        
        # 제품의 ROI 설정 로드
        if product_id:
            self.load_product_roi_settings()
        
        # 테이블 업데이트 - 설정 로드 후 실행
        self.update_roi_table()

        print(f"\n=== ROI 설정 다이얼로그 초기화 ===")
        print(f"제품 ID: {self.product_id}")
        if self.product_id:
            product = self.db_manager.get_product_by_id(self.product_id)
            print(f"제품 정보: {product}")
        print("===========================\n")

    def initUI(self):
        self.setWindowTitle('ROI 설정')
        self.setGeometry(100, 100, 1000, 600)

        main_layout = QHBoxLayout(self)
        
        # 좌측: ROI 목록 테이블
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        roi_label = QLabel("등록된 ROI 목록:")
        self.roi_table = QTableWidget()
        self.roi_table.setColumnCount(2)  # 체크박스와 이름만 표시
        self.roi_table.setHorizontalHeaderLabels(['선택', '이름'])
        self.roi_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.roi_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.roi_table.itemChanged.connect(self.on_checkbox_changed)
        self.roi_table.itemClicked.connect(self.on_row_clicked)
        
        left_layout.addWidget(roi_label)
        left_layout.addWidget(self.roi_table)
        
        # 우측: 알고리즘 선택 영역
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 사용 가능한 알고리즘 목록
        available_label = QLabel("사용 가능한 알고리즘:")
        self.available_list = QListWidget()
        self.available_list.setSelectionMode(QListWidget.SingleSelection)
        self.available_list.itemDoubleClicked.connect(self.add_algorithm_by_double_click)
        
        # 선택된 알고리즘 목록
        selected_label = QLabel("선택된 알고리즘:")
        self.selected_list = QListWidget()
        self.selected_list.setSelectionMode(QListWidget.SingleSelection)
        self.selected_list.itemDoubleClicked.connect(self.remove_algorithm_by_double_click)
        
        # 버튼들
        button_layout = QVBoxLayout()
        add_button = QPushButton("추가 >")
        remove_button = QPushButton("< 제거")
        add_button.clicked.connect(self.add_algorithm)
        remove_button.clicked.connect(self.remove_algorithm)
        button_layout.addStretch()
        button_layout.addWidget(add_button)
        button_layout.addWidget(remove_button)
        button_layout.addStretch()
        
        # 알고리즘 선택 영역 레이아웃
        algorithm_layout = QHBoxLayout()
        algorithm_left = QVBoxLayout()
        algorithm_right = QVBoxLayout()
        
        algorithm_left.addWidget(available_label)
        algorithm_left.addWidget(self.available_list)
        algorithm_right.addWidget(selected_label)
        algorithm_right.addWidget(self.selected_list)
        
        algorithm_layout.addLayout(algorithm_left)
        algorithm_layout.addLayout(button_layout)
        algorithm_layout.addLayout(algorithm_right)
        
        right_layout.addLayout(algorithm_layout)
        
        # 하단 버튼
        bottom_layout = QHBoxLayout()
        save_button = QPushButton("저장")
        close_button = QPushButton("닫기")
        
        save_button.clicked.connect(self.save_settings)
        close_button.clicked.connect(self.close)
        
        bottom_layout.addStretch()
        bottom_layout.addWidget(save_button)
        bottom_layout.addWidget(close_button)
        right_layout.addLayout(bottom_layout)
        
        # 제품 정보 표시 추가
        if self.product_id:
            product = self.db_manager.get_product_by_id(self.product_id)
            if product:
                product_info = QLabel(f"제품: {product['product_name']} ({product['product_id']})")
                left_layout.insertWidget(0, product_info)

        # 메인 레이아웃에 추가
        main_layout.addWidget(left_widget)
        main_layout.addWidget(right_widget)

        # 알고리즘 리스트 초기화
        self.available_list.clear()
        self.selected_list.clear()
        
        # 사용 가능한 알고리즘 추가 (ALGORITHM_PARAMETER에서 가져오기)
        for algo in ALGORITHM_PARAMETER.keys():
            self.available_list.addItem(algo)

    def update_roi_table(self):
        """ROI 테이블 업데이트"""
        try:
            self.roi_table.setRowCount(0)  # 테이블 초기화
            self.roi_table.blockSignals(True)  # 시그널 일시 중지
            
            # ROI 목록이 없는 경우
            if not self.target_manager:
                print("타겟 매니저가 없습니다.")
                return
            
            if not self.target_manager.target_list:
                print("표시할 ROI가 없습니다.")
                return
            
            # 매핑 초기화
            self.row_to_target_map = {}
            
            print(f"타겟 목록: {list(self.target_manager.target_list.keys())}")
            
            # 테이블에 ROI 정보 추가
            row = 0
            for target_id, target in self.target_manager.target_list.items():
                self.roi_table.insertRow(row)
                
                # 선택 체크박스 (0번 열)
                select_item = QTableWidgetItem("")
                select_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                select_item.setCheckState(Qt.Unchecked)
                self.roi_table.setItem(row, 0, select_item)
                
                # ROI 이름 (1번 열)
                name_item = QTableWidgetItem(target.name)
                self.roi_table.setItem(row, 1, name_item)
                
                # 행과 타겟 ID 매핑 저장
                self.row_to_target_map[row] = target_id
                
                row += 1
            
            self.roi_table.blockSignals(False)  # 시그널 다시 활성화
            
            # 디버그 정보
            print(f"ROI 테이블 업데이트 완료: {row}개")
            print(f"행-타겟 매핑: {self.row_to_target_map}")
            
        except Exception as e:
            print(f"테이블 업데이트 중 오류: {str(e)}")
            import traceback
            traceback.print_exc()

    def on_row_clicked(self, item):
        """테이블 행 클릭 시 이벤트 처리"""
        if not item:
            return
        
        try:
            # 클릭한 행 번호 가져오기
            current_row = item.row()
            print(f"선택된 행: {current_row}")
            
            # 매핑이 없으면 다시 생성
            if not hasattr(self, 'row_to_target_map') or not self.row_to_target_map:
                print("매핑이 없습니다. 테이블을 다시 업데이트합니다.")
                self.update_roi_table()
                return
            
            # 행 번호를 통해 타겟 ID 가져오기
            if current_row not in self.row_to_target_map:
                print(f"행 {current_row}에 대한 매핑이 없습니다.")
                return
            
            target_id = self.row_to_target_map[current_row]
            
            # 타겟 ID가 타겟 목록에 없는 경우 처리
            if target_id not in self.target_manager.target_list:
                print(f"타겟 ID {target_id}를 찾을 수 없습니다.")
                return
            
            # 타겟 가져오기
            target = self.target_manager.target_list[target_id]
            
            # 알고리즘 목록 초기화
            self.selected_list.clear()
            self.available_list.clear()
            
            # 이미 선택된 알고리즘 추가
            if hasattr(target, 'matching_algorithm'):
                for algorithm in target.matching_algorithm:
                    self.selected_list.addItem(algorithm)
            
            # 사용 가능한 알고리즘 추가 (이미 선택된 알고리즘 제외)
            all_algorithms = list(ALGORITHM_PARAMETER.keys())
            for algorithm in all_algorithms:
                if not hasattr(target, 'matching_algorithm') or algorithm not in target.matching_algorithm:
                    self.available_list.addItem(algorithm)
            
            # 현재 선택된 ROI 저장
            self.selected_target_id = target_id
            print(f"ROI 선택 완료: {target.name} (ID: {target_id})")
            
        except Exception as e:
            print(f"행 클릭 처리 중 오류: {str(e)}")
            import traceback
            traceback.print_exc()
        
    def on_checkbox_changed(self, item):
        """체크박스 상태 변경 시 처리 - 알고리즘 수정용"""
        if item.column() != 0:
            return
            
        row = item.row()
        if row not in self.row_to_target_map:
            print(f"행 {row}에 대한 매핑이 없습니다.")
            return
            
        target_id = self.row_to_target_map[row]
        if target_id not in self.target_manager.target_list:
            print(f"타겟 ID {target_id}를 찾을 수 없습니다.")
            return
            
        target = self.target_manager.target_list[target_id]
        
        # 체크박스 상태에 따라 선택된 ROI 목록 업데이트
        if item.checkState() == Qt.Checked:
            if target not in self.selected_targets:
                self.selected_targets.append(target)
                print(f"ROI '{target.name}' 선택됨")
        else:
            if target in self.selected_targets:
                self.selected_targets.remove(target)
                print(f"ROI '{target.name}' 선택 해제됨")
        
        # 알고리즘 수정 버튼들 활성화/비활성화
        enable_edit = len(self.selected_targets) > 0
        self.available_list.setEnabled(enable_edit)
        self.selected_list.setEnabled(enable_edit)

    def update_algorithm_list(self):
        """선택된 ROI의 알고리즘 목록 업데이트"""
        current_row = self.roi_table.currentRow()
        if current_row < 0:
            return
            
        target_id = self.row_to_target_map.get(current_row)
        if not target_id or target_id not in self.target_manager.target_list:
            return
            
        target = self.target_manager.target_list[target_id]
        self.selected_list.clear()
        self.available_list.clear()
        
        # 이미 선택된 알고리즘 추가
        if hasattr(target, 'matching_algorithm'):
            for algorithm in target.matching_algorithm:
                self.selected_list.addItem(algorithm)
        
        # 사용 가능한 알고리즘 추가 (이미 선택된 알고리즘 제외)
        all_algorithms = list(ALGORITHM_PARAMETER.keys())
        for algorithm in all_algorithms:
            if not hasattr(target, 'matching_algorithm') or algorithm not in target.matching_algorithm:
                self.available_list.addItem(algorithm)

    def add_algorithm_by_double_click(self, item):
        """더블클릭으로 알고리즘 추가"""
        if not self.selected_targets:
            QMessageBox.warning(self, "경고", "ROI를 선택해주세요.")
            return
            
        algorithm = item.text()
        # 선택된 모든 ROI에 알고리즘 추가
        for target in self.selected_targets:
            if algorithm not in target.matching_algorithm:
                target.matching_algorithm.append(algorithm)
        
        # 현재 보고 있는 ROI의 알고리즘 목록 업데이트
        current_row = self.roi_table.currentRow()
        if current_row >= 0:
            self.on_row_clicked(self.roi_table.item(current_row, 1))

    def add_algorithm(self):
        """알고리즘 추가"""
        if not self.selected_targets:
            QMessageBox.warning(self, "경고", "ROI를 선택해주세요.")
            return
            
        selected_items = self.available_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "경고", "추가할 알고리즘을 선택해주세요.")
            return
            
        algorithm = selected_items[0].text()
        # 선택된 모든 ROI에 알고리즘 추가
        for target in self.selected_targets:
            if algorithm not in target.matching_algorithm:
                target.matching_algorithm.append(algorithm)
        
        # 알고리즘 목록 업데이트
        self.update_algorithm_list()

    def remove_algorithm(self):
        """알고리즘 제거"""
        if not self.selected_targets:
            QMessageBox.warning(self, "경고", "ROI를 선택해주세요.")
            return
            
        selected_items = self.selected_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "경고", "제거할 알고리즘을 선택해주세요.")
            return
            
        algorithm = selected_items[0].text()
        # 선택된 모든 ROI에서 알고리즘 제거
        for target in self.selected_targets:
            if algorithm in target.matching_algorithm:
                target.matching_algorithm.remove(algorithm)
        
        # 알고리즘 목록 업데이트
        self.update_algorithm_list()

    def remove_algorithm_by_double_click(self, item):
        """더블클릭으로 알고리즘 제거"""
        if not self.selected_targets:
            QMessageBox.warning(self, "경고", "ROI를 선택해주세요.")
            return
            
        algorithm = item.text()
        # 선택된 모든 ROI에서 알고리즘 제거
        for target in self.selected_targets:
            if algorithm in target.matching_algorithm:
                target.matching_algorithm.remove(algorithm)
        
        # 현재 보고 있는 ROI의 알고리즘 목록 업데이트
        current_row = self.roi_table.currentRow()
        if current_row >= 0:
            self.on_row_clicked(self.roi_table.item(current_row, 1))

    def save_settings(self):
        """ROI 설정 저장"""
        if save_roi_settings(self, self.target_manager, self.product_id, self.db_manager):
            self.db_manager.roi_settings_updated.emit(self.product_id)
            self.refresh_data()

    def load_product_roi_settings(self):
        """제품의 ROI 설정을 DB에서 로드"""
        if not self.product_id or not self.db_manager:
            return
        
        # UI 업데이트를 위한 콜백 함수 정의
        def update_ui():
            self.update_roi_table()
            self.update_algorithm_list()
        
        # 공통 유틸리티 함수 사용
        load_roi_settings(
            dialog=self,
            product_id=self.product_id,
            db_manager=self.db_manager,
            target_manager=self.target_manager,
            frame=None,  # 프레임은 없을 수 있음
            update_ui_callback=update_ui
        )

    def refresh_data(self):
        """데이터 갱신"""
        if self.product_id:
            self.load_product_roi_settings()
            self.update_roi_table()
            self.update_algorithm_list() 

    def cleanup(self):
        """다이얼로그 정리"""
        try:
            # 리소스 정리 로직
            if hasattr(self, 'target_manager'):
                self.target_manager.clear_targets()
        except Exception as e:
            print(f"다이얼로그 정리 중 오류: {e}") 