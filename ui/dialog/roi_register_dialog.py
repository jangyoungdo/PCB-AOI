from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
    QLabel, QLineEdit, QMessageBox, QWidget, QInputDialog, QSpinBox, QTableWidget, QTableWidgetItem
)
from PyQt5.QtCore import Qt, QObject, pyqtSignal
from PyQt5.QtGui import QPen, QPainter, QPixmap, QImage
import cv2
from manager.target_manager import InspectionTargetListManager
from ui.dialog.fullscreen_image_dialog import FullscreenImageDialog
from utils.util_function import crop_image
from models.target import InspectionTarget
import json
import os
from utils.roi_utils import save_roi_settings, load_roi_settings, select_roi_from_image, visualize_rois
from utils.json_utils import parse_json_safely

class ROIRegisterDialog(QDialog):
    def __init__(self, parent=None, camera_manager=None, target_manager=None, 
                 product_id=None, db_manager=None):
        super().__init__(parent)
        self.camera_manager = camera_manager
        self.target_manager = target_manager or InspectionTargetListManager()
        self.product_id = product_id
        self.db_manager = db_manager
        
        print(f"\n=== ROI 등록 다이얼로그 초기화 ===")
        print(f"제품 ID: {self.product_id}")
        if self.product_id and self.db_manager:  # db_manager 존재 여부 확인
            product = self.db_manager.get_product_by_id(self.product_id)  # db_manager 사용
            print(f"제품 정보: {product}")
        print("===========================\n")
        
        # 알고리즘 파라미터 초기화 추가
        InspectionTarget.set_parameter()
        
        self.frame = None  # 캡처된 프레임 저장
        
        # 카메라에서 현재 프레임 캡처
        if self.camera_manager:
            self.camera_manager.capture_frame()
            self.frame = self.camera_manager.get_captured_frame()
        
        # UI 초기화를 먼저 수행
        self.initUI()
        
        # 제품의 ROI 설정 로드 (UI 초기화 후)
        if product_id:
            self.load_product_roi_settings()
        
        # 카메라 매니저 연결
        if self.camera_manager:
            self.camera_manager.frame_updated.connect(self.update_preview)

    def initUI(self):
        self.setWindowTitle('ROI 등록')
        self.setGeometry(200, 200, 1000, 600)
        
        main_layout = QHBoxLayout(self)
        
        # 좌측 테이블 영역
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 제품 정보 표시 추가
        if self.product_id:
            product = self.db_manager.get_product_by_id(self.product_id)
            if product:
                product_info = QLabel(f"제품: {product['product_name']} ({product['product_id']})")
                left_layout.insertWidget(0, product_info)
        
        # ROI 목록 테이블
        self.roi_table = QTableWidget()
        self.roi_table.setColumnCount(5)
        self.roi_table.setHorizontalHeaderLabels(['이름', 'X', 'Y', '너비', '높이'])
        self.roi_table.itemChanged.connect(self.on_table_item_changed)
        self.roi_table.setSelectionBehavior(QTableWidget.SelectRows)
        left_layout.addWidget(self.roi_table)
        
        # 버튼
        button_layout = QHBoxLayout()
        fullscreen_button = QPushButton('확대')
        delete_button = QPushButton('삭제')
        save_button = QPushButton('저장')
        close_button = QPushButton('닫기')
        
        fullscreen_button.clicked.connect(self.show_fullscreen)
        delete_button.clicked.connect(self.delete_selected_roi)
        save_button.clicked.connect(self.save_settings)
        close_button.clicked.connect(self.accept)
        
        button_layout.addWidget(fullscreen_button)
        button_layout.addWidget(delete_button)
        button_layout.addWidget(save_button)
        button_layout.addWidget(close_button)
        left_layout.addLayout(button_layout)
        
        # 우측 프리뷰 영역
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setStyleSheet("background-color: black;")
        self.preview_label.setMinimumSize(640, 480)
        right_layout.addWidget(self.preview_label)
        
        main_layout.addWidget(left_widget, 1)
        main_layout.addWidget(right_widget, 2)
        
        self.update_preview()
        self.update_table()

    def update_table(self):
        """ROI 테이블 업데이트"""
        self.roi_table.setRowCount(0)
        for target in self.target_manager.target_list.values():
            row = self.roi_table.rowCount()
            self.roi_table.insertRow(row)
            self.roi_table.setItem(row, 0, QTableWidgetItem(target.name))
            self.roi_table.setItem(row, 1, QTableWidgetItem(str(target.x)))
            self.roi_table.setItem(row, 2, QTableWidgetItem(str(target.y)))
            self.roi_table.setItem(row, 3, QTableWidgetItem(str(target.w)))
            self.roi_table.setItem(row, 4, QTableWidgetItem(str(target.h)))

    def on_table_item_changed(self, item):
        """테이블 항목 변경 시 처리"""
        try:
            row = item.row()
            col = item.column()
            target_id = list(self.target_manager.target_list.keys())[row]
            target = self.target_manager.target_list[target_id]
            
            # 모든 셀이 유효한지 확인
            cells = [self.roi_table.item(row, i) for i in range(5)]
            if any(cell is None for cell in cells):
                return  # 하나라도 None이면 처리하지 않음
            
            value = item.text()
            if col == 0:  # 이름
                target.update_name(value)
            else:  # 좌표/크기
                x = int(cells[1].text())
                y = int(cells[2].text())
                w = int(cells[3].text())
                h = int(cells[4].text())
                target.update_ROI(x, y, w, h, crop_image(self.frame, x, y, w, h))
            
            self.update_preview()
        except (ValueError, IndexError) as e:
            QMessageBox.warning(self, "경고", "올바른 값을 입력하세요.")
            self.update_table()

    def delete_selected_roi(self):
        """선택된 ROI 삭제"""
        try:
            # 선택된 행이 있는지 확인
            selected_rows = set(item.row() for item in self.roi_table.selectedItems())
            if not selected_rows:
                QMessageBox.warning(self, "경고", "삭제할 ROI를 선택해주세요.")
                return
                
            # 삭제 확인 메시지
            reply = QMessageBox.question(self, '삭제 확인', 
                                       "선택한 ROI를 삭제하시겠습니까?",
                                       QMessageBox.Yes | QMessageBox.No, 
                                       QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                # itemChanged 시그널 일시 중지
                self.roi_table.blockSignals(True)
                
                # 선택된 ROI 삭제
                for row in sorted(selected_rows, reverse=True):
                    target_id = list(self.target_manager.target_list.keys())[row]
                    target = self.target_manager.target_list[target_id]
                    print(f"[DEBUG] ROI 삭제: {target.name}")  # 디버깅용 로그
                    self.target_manager.remove_target(target_id)
                
                # itemChanged 시그널 재개
                self.roi_table.blockSignals(False)
                
                # UI 업데이트
                self.roi_table.clearSelection()  # 선택 초기화
                self.update_table()             # 테이블 업데이트
                self.update_preview()           # 프리뷰 업데이트
                
        except Exception as e:
            print(f"[ERROR] ROI 삭제 중 오류 발생: {str(e)}")
            QMessageBox.critical(self, "오류", f"ROI 삭제 중 오류가 발생했습니다: {str(e)}")
            # 에러 발생 시에도 UI 업데이트
            self.update_table()
            self.update_preview()

    def update_preview(self, frame=None):
        """프리뷰 영역을 업데이트합니다."""
        if self.frame is not None:
            # visualize_rois 함수 사용
            from utils.roi_utils import visualize_rois
            
            # ROI 표시한 이미지 생성
            display_frame = visualize_rois(
                self.frame,
                self.target_manager,
                selected_id=self.selected_roi_id if hasattr(self, 'selected_roi_id') else None,
                scale_factor=1.0
            )
            
            # RGB 변환 (OpenCV는 BGR, Qt는 RGB 사용)
            rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            
            # QImage 및 QPixmap으로 변환
            height, width, channels = rgb_frame.shape
            bytes_per_line = channels * width
            image = QImage(rgb_frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(image)
            
            # 크기 조정 및 표시
            scaled_pixmap = pixmap.scaled(
                self.preview_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.preview_label.setPixmap(scaled_pixmap)
        else:
            self.preview_label.setText("카메라 스트림이 없습니다.")

    def register_roi(self):
        """ROI를 등록합니다."""
        try:
            x = self.x_spin.value()
            y = self.y_spin.value()
            w = self.w_spin.value()
            h = self.h_spin.value()
            
            if w <= 0 or h <= 0:
                QMessageBox.warning(self, "경고", "올바른 크기를 입력하세요.")
                return

            # ROI 이름 입력 다이얼로그 표시
            default_name = f"ROI_{self.target_manager.get_next_id()}"
            name, ok = QInputDialog.getText(
                self, 
                'ROI 이름 입력', 
                'ROI의 이름을 입력하세요:', 
                QLineEdit.Normal, 
                default_name
            )

            if ok and name:
                # 레퍼런스 이미지 확인용 로그
                roi_image = crop_image(self.frame, x, y, w, h)
                print(f"\n[DEBUG] ROI 등록: {name}")
                print(f"ROI 크기: {roi_image.shape if roi_image is not None else 'None'}")
                
                success = self.target_manager.add_target(
                    name=name,
                    x=x,
                    y=y,
                    w=w,
                    h=h,
                    image=self.frame,
                    algorithms=["hsv"]  # HSV 알고리즘 추가
                )

                if success:
                    self.accept()
                else:
                    QMessageBox.warning(self, "경고", "ROI 등록에 실패했습니다.")
                
        except Exception as e:
            QMessageBox.critical(self, "오류", f"ROI 등록 중 오류가 발생했습니다: {str(e)}")

    def show_fullscreen(self):
        """전체 화면 이미지 대화상자를 표시합니다."""
        if self.frame is not None:
            dialog = FullscreenImageDialog(
                parent=self,
                frame=self.frame,  # 캡처된 프레임 전달
                roi_list=self.target_manager.target_list.values(),
                roi_manager=self.target_manager
            )
            dialog.exec_()
        else:
            QMessageBox.warning(self, "경고", "표시할 이미지가 없습니다.")

    def get_target_manager(self):
        """등록된 ROI 정보가 있는 타겟 매니저를 반환합니다."""
        return self.target_manager 

    def save_settings(self):
        """ROI 설정을 저장"""
        if not all([self.target_manager, self.product_id, self.db_manager]):
            QMessageBox.warning(self, "경고", "저장에 필요한 정보가 누락되었습니다.")
            return False
        
        try:
            if save_roi_settings(self, self.target_manager, self.product_id, self.db_manager):
                self.db_manager.roi_settings_updated.emit(self.product_id)
                self.refresh_data()
                return True
        except Exception as e:
            QMessageBox.critical(self, "오류", f"저장 중 오류가 발생했습니다: {str(e)}")
        return False

    def load_roi_settings(self):
        """제품의 ROI 설정을 DB에서 로드"""
        if not self.product_id:
            QMessageBox.warning(self, "경고", "제품이 선택되지 않았습니다.")
            return
        
        try:
            cursor = self.target_manager.execute_query(
                "SELECT roi_settings FROM product_table WHERE product_id = ?",
                (self.product_id,)
            )
            row = cursor.fetchone()
            
            if row and row['roi_settings']:
                # json.loads 대신 parse_json_safely 사용
                settings = parse_json_safely(row['roi_settings'], {})
                
                # 기존 ROI 목록 초기화
                self.target_manager.clear()
                
                # 저장된 ROI 설정 불러오기
                if settings and 'roi_list' in settings:  # None 체크 추가
                    for roi_data in settings['roi_list']:
                        self.target_manager.add_target(
                            name=roi_data['name'],
                            x=roi_data['x'],
                            y=roi_data['y'],
                            w=roi_data['w'],
                            h=roi_data['h'],
                            image=self.frame,
                            algorithms=roi_data.get('algorithms', ["hsv"])  # 기본값 설정
                        )
                    
                    # UI 업데이트
                    self.update_table()
                    self.update_preview()
                    QMessageBox.information(self, "알림", "ROI 설정을 불러왔습니다.")
                else:
                    QMessageBox.information(self, "알림", "유효한 ROI 설정이 없습니다.")
            else:
                QMessageBox.information(self, "알림", "저장된 ROI 설정이 없습니다.")
                
        except Exception as e:
            QMessageBox.critical(self, "오류", f"설정 불러오기 중 오류가 발생했습니다: {str(e)}")

    def load_product_roi_settings(self):
        """제품의 ROI 설정을 DB에서 로드"""
        if not self.product_id or not self.db_manager:
            return
        
        # UI 업데이트를 위한 콜백 함수 정의
        def update_ui():
            self.update_table()
            self.update_preview()
        
        # 공통 유틸리티 함수 사용
        load_roi_settings(
            dialog=self,
            product_id=self.product_id,
            db_manager=self.db_manager,
            target_manager=self.target_manager,
            frame=self.frame,
            update_ui_callback=update_ui
        )

    def refresh_data(self):
        """데이터 갱신"""
        if self.product_id:
            self.load_product_roi_settings()
            self.update_roi_table()
            self.update_preview()  # 미리보기 업데이트
            
    def update_roi_table(self):
        """ROI 테이블 업데이트"""
        self.roi_table.setRowCount(0)
        for target in self.target_manager.target_list.values():
            row = self.roi_table.rowCount()
            self.roi_table.insertRow(row)
            self.roi_table.setItem(row, 0, QTableWidgetItem(target.name))
            self.roi_table.setItem(row, 1, QTableWidgetItem(str(target.x)))
            self.roi_table.setItem(row, 2, QTableWidgetItem(str(target.y)))
            self.roi_table.setItem(row, 3, QTableWidgetItem(str(target.w)))
            self.roi_table.setItem(row, 4, QTableWidgetItem(str(target.h)))

    def select_roi(self):
        """현재 이미지에서 ROI 선택"""
        if self.frame is None:
            QMessageBox.warning(self, "경고", "이미지가 없습니다.")
            return
        
        # roi_utils에서 제공하는 select_roi_from_image 함수 활용
        roi = select_roi_from_image(self.frame, self)
        
        if roi:
            x, y, w, h = roi
            
            # 선택한 ROI 정보로 스핀박스 값 설정
            self.x_spin.setValue(x)
            self.y_spin.setValue(y)
            self.w_spin.setValue(w)
            self.h_spin.setValue(h)
            
            # 선택 영역 표시
            self.update_preview()
            
            # 알림 메시지
            QMessageBox.information(self, "ROI 선택 완료", 
                                   f"ROI가 선택되었습니다 (x={x}, y={y}, w={w}, h={h}).") 