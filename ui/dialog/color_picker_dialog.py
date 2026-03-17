from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QPushButton, QFrame, QSplitter, QGroupBox,
                           QListWidget, QListWidgetItem, QMessageBox, QWidget)
from PyQt5.QtCore import Qt, QPoint, QTimer
from PyQt5.QtGui import QImage, QPixmap, QCursor, QPainter, QColor
import cv2
import numpy as np
import json
from algorithms.hsv_matching import HSVMatching
from PIL import Image, ImageDraw, ImageFont
from utils.roi_utils import visualize_rois, calculate_scaling_parameters, screen_to_image_coords

class ColorPickerDialog(QDialog):
    def __init__(self, parent=None, frame=None, target_manager=None):
        super().__init__(parent)
        self.frame = frame
        self.target_manager = target_manager
        self.selected_roi = None
        self.selected_color = None
        self.is_picking_color = False
        self.scale_factor = 1.0
        self.display_offset_x = 0
        self.display_offset_y = 0
        self.dropper_cursor = None
        
        # 창 크기 조정 (고정 크기 해제, 최소 크기 설정)
        self.setMinimumSize(1200, 700)
        self.setWindowTitle("ROI 색상 설정")
        
        # 스포이드 커서 생성
        self.create_dropper_cursor()
        
        # 기본 초기화 확인
        if frame is None:
            print("경고: 프레임이 None입니다")
            # 더미 프레임 생성 (회색 이미지)
            self.frame = np.ones((600, 800, 3), dtype=np.uint8) * 200
            cv2.putText(self.frame, "이미지 없음", (300, 300), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
        
        if not target_manager or len(target_manager.target_list) == 0:
            print("경고: ROI가 없습니다")
            # 계속 진행 (빈 목록 표시)
        
        print(f"ColorPickerDialog 초기화 - ROI 개수: {len(self.target_manager.target_list) if self.target_manager else 0}")
        
        # UI 초기화
        self.initUI()
        
        # 초기 프레임 업데이트
        self.update_frame()

    def create_dropper_cursor(self):
        """스포이드 모양의 커서를 생성합니다"""
        try:
            # 커스텀 커서 이미지 생성
            cursor_size = 32
            cursor_img = QPixmap(cursor_size, cursor_size)
            cursor_img.fill(Qt.transparent)
            
            painter = QPainter(cursor_img)
            painter.setPen(QColor(0, 0, 0))
            
            # 스포이드 모양 그리기
            painter.drawLine(8, 8, 20, 20)  # 대각선
            painter.drawLine(20, 20, 25, 20)  # 가로
            painter.drawLine(25, 20, 25, 25)  # 세로
            painter.drawRect(19, 19, 7, 7)  # 스포이드 끝
            
            painter.end()
            
            # 커서 생성
            self.dropper_cursor = QCursor(cursor_img, 8, 8)
        
        except Exception as e:
            print(f"커서 생성 중 오류: {str(e)}")
            self.dropper_cursor = QCursor(Qt.CrossCursor)  # 대체 커서

    def initUI(self):
        """UI 초기화"""
        main_layout = QHBoxLayout()
        
        # 왼쪽 패널 (이미지 표시 영역)
        image_panel = QFrame()
        image_panel.setFrameShape(QFrame.StyledPanel)
        image_layout = QVBoxLayout(image_panel)
        
        # 이미지 라벨
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMinimumSize(800, 600)
        image_layout.addWidget(self.image_label)
        
        # 오른쪽 패널 (컨트롤 영역)
        control_panel = QFrame()
        control_panel.setFrameShape(QFrame.StyledPanel)
        control_panel.setMaximumWidth(350)
        control_layout = QVBoxLayout(control_panel)
        
        # ROI 목록
        roi_group = QGroupBox("ROI 목록")
        roi_layout = QVBoxLayout()
        
        self.roi_list = QListWidget()
        self.roi_list.setSelectionMode(QListWidget.SingleSelection)
        self.roi_list.itemClicked.connect(self.on_list_item_clicked)
        
        # ROI 목록 채우기
        if self.target_manager:
            for target_id, target in self.target_manager.target_list.items():
                item = QListWidgetItem(target.name)
                item.setData(Qt.UserRole, target_id)  # target_id 저장
                self.roi_list.addItem(item)
                
            if self.roi_list.count() > 0:
                self.roi_list.setCurrentRow(0)  # 첫 번째 항목 선택
                self.on_list_item_clicked(self.roi_list.item(0))  # 선택 처리
        
        roi_layout.addWidget(self.roi_list)
        roi_group.setLayout(roi_layout)
        control_layout.addWidget(roi_group)
        
        # 색상 표시 영역
        color_group = QGroupBox("색상 정보")
        color_layout = QVBoxLayout()
        
        # 색상 미리보기 라벨 생성
        self.color_preview = QLabel("색상 미리보기")
        self.color_preview.setFixedHeight(80)
        self.color_preview.setStyleSheet("background-color: #CCCCCC; border: 1px solid black;")
        self.color_preview.setAlignment(Qt.AlignCenter)
        
        self.hsv_value_label = QLabel("HSV: ---, ---, ---")
        self.hsv_value_label.setAlignment(Qt.AlignCenter)
        
        color_layout.addWidget(self.color_preview)
        color_layout.addWidget(self.hsv_value_label)
        color_group.setLayout(color_layout)
        control_layout.addWidget(color_group)
        
        # 동작 버튼
        action_group = QGroupBox("동작")
        action_layout = QVBoxLayout()
        
        self.pick_button = QPushButton("스포이드")
        self.pick_button.clicked.connect(self.on_pick_color)
        
        self.apply_button = QPushButton("선택한 색상 적용")
        self.apply_button.clicked.connect(self.apply_color)
        self.apply_button.setEnabled(False)  # 초기 비활성화
        
        # 버튼 레이아웃
        action_layout.addWidget(self.pick_button)
        action_layout.addWidget(self.apply_button)
        action_group.setLayout(action_layout)
        control_layout.addWidget(action_group)
        
        # 확인/취소 버튼
        button_layout = QHBoxLayout()
        
        self.confirm_button = QPushButton("확인")
        self.confirm_button.clicked.connect(self.accept)
        
        self.cancel_button = QPushButton("취소")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.confirm_button)
        button_layout.addWidget(self.cancel_button)
        
        control_layout.addLayout(button_layout)
        
        # 스트레치 추가 (위젯 간격 조정)
        control_layout.addStretch(1)
        
        # 메인 레이아웃에 패널 추가
        main_layout.addWidget(image_panel)
        main_layout.addWidget(control_panel)
        
        self.setLayout(main_layout)

    def update_color_preview(self, hsv_color):
        """색상 미리보기 업데이트"""
        try:
            if hsv_color is None:
                return
            
            self.selected_color = hsv_color
            
            # 여기서 위젯이 초기화되어 있는지 확인
            if not hasattr(self, 'color_preview') or self.color_preview is None:
                print("경고: color_preview 위젯이 초기화되지 않았습니다.")
                return
            
            # HSV에서 RGB로 변환하여 스타일시트 설정
            hsv_pixel = np.uint8([[[hsv_color[0], hsv_color[1], hsv_color[2]]]])
            bgr_pixel = cv2.cvtColor(hsv_pixel, cv2.COLOR_HSV2BGR)
            rgb_color = (bgr_pixel[0][0][2], bgr_pixel[0][0][1], bgr_pixel[0][0][0])
            
            # 스타일시트 적용
            self.color_preview.setStyleSheet(
                f"background-color: rgb({rgb_color[0]}, {rgb_color[1]}, {rgb_color[2]}); "
                f"border: 1px solid black;"
            )
            
            # HSV 값 업데이트
            if hasattr(self, 'hsv_value_label'):
                self.hsv_value_label.setText(f"HSV: {hsv_color[0]}, {hsv_color[1]}, {hsv_color[2]}")
            
        except Exception as e:
            print(f"색상 미리보기 업데이트 중 오류: {str(e)}")

    def update_frame(self):
        """프레임 이미지 업데이트"""
        print(f"[DEBUG] update_frame 호출됨: {id(self)}")
        
        if self.frame is None:
            print("경고: 표시할 프레임이 없습니다!")
            # 빈 이미지 표시
            empty_image = np.ones((400, 600, 3), dtype=np.uint8) * 200
            cv2.putText(empty_image, "이미지 없음", (150, 200), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)
            self.display_image(empty_image)
            return
            
        try:
            # 이미지 스케일 계산
            self.scale_factor = calculate_scaling_parameters(
                (self.frame.shape[1], self.frame.shape[0]),  # 튜플로 변경
                (self.image_label.width(), self.image_label.height())  # 튜플로 변경
            )
            
            print(f"[DEBUG] scale_factor: {self.scale_factor}, 타입: {type(self.scale_factor)}")
            
            # 수정: 함수가 튜플을 반환하는 경우 첫 번째 값만 사용
            if isinstance(self.scale_factor, tuple):
                self.scale_factor = self.scale_factor[0]
            
            # 직접 오프셋 계산
            scaled_width = int(self.frame.shape[1] * self.scale_factor)
            scaled_height = int(self.frame.shape[0] * self.scale_factor)
            self.display_offset_x = (self.image_label.width() - scaled_width) // 2
            self.display_offset_y = (self.image_label.height() - scaled_height) // 2
            
            # 원본 프레임 복사
            display_frame = self.frame.copy()
            
            # ROI 시각화 - 직접 구현 대신 visualize_rois 함수 사용
            if self.target_manager and self.target_manager.target_list:
                display_frame = visualize_rois(
                    display_frame,
                    self.target_manager,
                    selected_id=self.get_selected_target_id(),
                    scale_factor=1.0
                )
            
            # 이미지 표시
            self.display_image(display_frame)
            
        except Exception as e:
            print(f"프레임 업데이트 중 오류: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # 오류 발생 시 빈 이미지 표시
            error_image = np.ones((400, 600, 3), dtype=np.uint8) * 200
            cv2.putText(error_image, f"오류: {str(e)}", (50, 200), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            self.display_image(error_image)

    def display_image(self, image):
        """이미지를 라벨에 표시"""
        print(f"[DEBUG] 이미지 표시: {image.shape if image is not None else 'None'}")
        
        try:
            # OpenCV BGR -> Qt RGB 변환
            rgb_frame = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_frame.shape
            bytes_per_line = ch * w
            
            # QImage 생성
            q_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
            
            # QPixmap으로 변환하여 라벨에 표시
            pixmap = QPixmap.fromImage(q_image)
            
            # 라벨 크기에 맞게 스케일링
            label_size = self.image_label.size()
            scaled_pixmap = pixmap.scaled(
                label_size.width(),
                label_size.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            self.image_label.setPixmap(scaled_pixmap)
            
        except Exception as e:
            print(f"이미지 표시 중 오류: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # 오류 발생 시 텍스트로 표시
            self.image_label.setText(f"이미지 표시 오류: {str(e)}")

    def get_selected_target_id(self):
        """현재 선택된 ROI의 target_id 반환"""
        try:
            if not self.selected_roi:
                return None
                
            for target_id, target in self.target_manager.target_list.items():
                if target.name == self.selected_roi:
                    return target_id
            
            return None
            
        except Exception as e:
            print(f"selected_target_id 조회 중 오류: {str(e)}")
            return None

    def on_list_item_clicked(self, item):
        """ROI 목록 항목 클릭 시 처리"""
        if item is None:
            return
            
        try:
            self.selected_roi = item.text()
            target_id = item.data(Qt.UserRole)  # 저장된 target_id 가져오기
            print(f"\n=== ROI 선택: {self.selected_roi} (ID: {target_id}) ===")
            
            # 선택된 ROI의 기존 색상 정보 표시
            for target_id, target in self.target_manager.target_list.items():
                if target.name == self.selected_roi:
                    if hasattr(target, 'color') and target.color is not None:
                        self.selected_color = target.color
                        print(f"기존 색상: {self.selected_color}")
                        self.update_color_preview(self.selected_color)
                        self.apply_button.setEnabled(True)
                    else:
                        print(f"ROI '{self.selected_roi}'에 설정된 색상이 없습니다")
                        self.selected_color = None
                        self.update_color_preview(None)
                        self.apply_button.setEnabled(False)
                    break
            
            # 프레임 업데이트하여 선택된 ROI 강조
            self.update_frame()
            
        except Exception as e:
            print(f"ROI 선택 중 오류: {str(e)}")
            import traceback
            traceback.print_exc()

    def on_pick_color(self):
        """색상 선택 모드 시작"""
        if not self.selected_roi:
            QMessageBox.warning(self, "경고", "먼저 ROI를 선택해주세요")
            return
        
        self.is_picking_color = True
        self.pick_button.setEnabled(False)
        
        # 스포이드 커서 설정
        if self.dropper_cursor:
            self.image_label.setCursor(self.dropper_cursor)
        else:
            self.image_label.setCursor(Qt.CrossCursor)
            
        QMessageBox.information(self, "알림", "이미지에서 색상을 선택해주세요")

    def apply_color(self):
        """선택된 색상을 현재 ROI에 적용"""
        if not self.selected_roi or self.selected_color is None:
            QMessageBox.warning(self, "경고", "ROI와 색상을 모두 선택해주세요")
            return
        
        try:
            # 선택한 ROI에 색상 적용
            for target_id, target in self.target_manager.target_list.items():
                if target.name == self.selected_roi:
                    target.color = self.selected_color.copy()
                    print(f"ROI '{self.selected_roi}'에 색상 적용됨: {self.selected_color}")
                    
                    # 성공 메시지
                    QMessageBox.information(
                        self, 
                        "알림", 
                        f"ROI '{self.selected_roi}'에 색상이 적용되었습니다"
                    )
                    break
            
            # 프레임 업데이트
            self.update_frame()
            
        except Exception as e:
            print(f"색상 적용 중 오류: {str(e)}")
            QMessageBox.warning(self, "오류", f"색상 적용 중 오류가 발생했습니다: {str(e)}")

    def mousePressEvent(self, event):
        """마우스 클릭 이벤트"""
        # 스포이드 툴 모드가 아니면 무시
        if not self.is_picking_color:
            super().mousePressEvent(event)
            return
            
        try:
            # 이미지 라벨 영역 내에 있는지 확인
            pos = event.pos()
            label_pos = self.image_label.mapFrom(self, pos)
            
            # 라벨 내부가 아니면 무시
            if not self.image_label.rect().contains(label_pos):
                return
                
            # 이미지 영역 계산
            label_size = self.image_label.size()
            pixmap_size = self.image_label.pixmap().size()
            
            # 이미지가 라벨에 가득 차지 않는 경우의 오프셋 계산
            offset_x = (label_size.width() - pixmap_size.width()) / 2
            offset_y = (label_size.height() - pixmap_size.height()) / 2
            
            # 이미지 내 좌표로 변환
            img_x_scaled = label_pos.x() - offset_x
            img_y_scaled = label_pos.y() - offset_y
            
            # 스케일링 역적용
            img_x = int(img_x_scaled / self.scale_factor)
            img_y = int(img_y_scaled / self.scale_factor)
            
            # 여기에 추가 - 이미지 크기 초기화
            img_h, img_w = self.frame.shape[:2]
            
            if 0 <= img_x < img_w and 0 <= img_y < img_h:
                # 색상 선택
                bgr_color = self.frame[img_y, img_x]
                print(f"선택된 색상(BGR): {bgr_color}")
                
                # HSV로 변환
                hsv_color = cv2.cvtColor(np.uint8([[bgr_color]]), cv2.COLOR_BGR2HSV)[0][0]
                self.selected_color = hsv_color
                print(f"HSV 색상: {hsv_color}")
                
                # 색상 미리보기 업데이트
                self.update_color_preview(hsv_color)
                
                # 적용 버튼 활성화
                self.apply_button.setEnabled(True)
                
                # 색상 선택 모드 종료
                self.is_picking_color = False
                self.pick_button.setEnabled(True)
                self.image_label.setCursor(Qt.ArrowCursor)
                
                # 색상 선택 완료 메시지
                QMessageBox.information(
                    self, 
                    "알림", 
                    "색상이 선택되었습니다. '선택한 색상 적용' 버튼을 눌러 적용하세요."
                )
            else:
                print(f"이미지 외부 좌표: ({img_x}, {img_y}), 이미지 크기: {img_w}x{img_h}")
        
        except Exception as e:
            print(f"색상 선택 중 오류: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # 색상 선택 모드 종료
            self.is_picking_color = False
            self.pick_button.setEnabled(True)
            self.image_label.setCursor(Qt.ArrowCursor)

    def resizeEvent(self, event):
        """창 크기 변경 시 이미지 업데이트"""
        super().resizeEvent(event)
        # 크기 조정 시 지연 시간 후 업데이트 (성능 개선)
        QTimer.singleShot(100, self.update_frame)

    def accept(self):
        """확인 버튼 클릭 시 처리"""
        print("\n=== 색상 설정 저장 ===")
        for target_id, target in self.target_manager.target_list.items():
            if hasattr(target, 'color') and target.color is not None:
                print(f"ROI '{target.name}'의 색상: {target.color}")
        
        super().accept() 