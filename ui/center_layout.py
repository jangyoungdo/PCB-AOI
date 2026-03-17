from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy, QDialog, QFrame, QMessageBox
from PyQt5.QtCore import Qt, pyqtSlot, QPoint
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor
import cv2
import numpy as np
from algorithms.hsv_matching import HSVMatching
from ui.dialog.detail_dialog import DetailDialog
from PIL import Image, ImageDraw, ImageFont
from ui.dialog.roi_detail_dialog import ROIDetailDialog
from utils.roi_utils import visualize_rois, draw_text_with_korean

class MaskViewDialog(QDialog):
    def __init__(self, reference_mask, target_mask, parent=None):
        super().__init__(parent)
        self.setWindowTitle("마스크 이미지 비교")
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        # 레퍼런스 마스크
        ref_label = QLabel("레퍼런스 마스크:")
        layout.addWidget(ref_label)
        ref_pixmap = self.mask_to_pixmap(reference_mask)
        ref_image_label = QLabel()
        ref_image_label.setPixmap(ref_pixmap)
        layout.addWidget(ref_image_label)
        
        # 타겟 마스크
        target_label = QLabel("타겟 마스크:")
        layout.addWidget(target_label)
        target_pixmap = self.mask_to_pixmap(target_mask)
        target_image_label = QLabel()
        target_image_label.setPixmap(target_pixmap)
        layout.addWidget(target_image_label)
        
        self.setLayout(layout)
    
    def mask_to_pixmap(self, mask):
        # 마스크를 3채널로 변환 (시각화를 위해)
        colored_mask = cv2.cvtColor(mask, cv2.COLOR_GRAY2RGB)
        height, width = colored_mask.shape[:2]
        bytes_per_line = 3 * width
        q_img = QImage(colored_mask.data, width, height, bytes_per_line, QImage.Format_RGB888)
        return QPixmap.fromImage(q_img)

class CenterLayout(QWidget):
    def __init__(self, parent=None, target_manager=None, camera_manager=None):
        super().__init__(parent)
        self.target_manager = target_manager
        self.camera_manager = camera_manager
        self.current_frame = None
        self.current_results = None  # 현재 검사 결과 저장
        self.selected_target_id = None
        self.initUI()
        self.setMouseTracking(True)  # 마우스 이벤트 활성화
        
        # 카메라 매니저 시그널 연결 제거 (실시간 스트리밍 불필요)
        # if self.camera_manager:
        #     self.camera_manager.frame_updated.connect(self.updateStream)

    def initUI(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 상단 영역 (4)
        top_frame = QFrame()
        top_layout = QVBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(0)
        
        # 단일 레이블 사용 (preview_label만 사용)
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.preview_label.setStyleSheet("""
            QLabel { 
                background-color: #000000;
                border: none;
            }
        """)
        top_layout.addWidget(self.preview_label)
        top_frame.setLayout(top_layout)
        
        # 기존 streamLabel을 preview_label로 참조 변경
        self.streamLabel = self.preview_label  # 하위 호환성 유지
        
        # 하단 영역 (1) - 결과 표시
        bottom_frame = QFrame()
        bottom_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        bottom_frame.setStyleSheet("""
            QFrame {
                background-color: #4CAF50;    
                border-radius: 10px;
                margin: 10px;
                padding: 10px;
            }
        """)
        
        bottom_layout = QVBoxLayout()
        bottom_layout.setAlignment(Qt.AlignCenter)
        
        # 통과 상태 레이블
        self.status_label = QLabel("통과") 
        self.status_label.setStyleSheet("""
            QLabel {
                color: white;
                font-weight: bold;
                font-size: 36px;     /* 폰트 크기 감소 (48 → 36) */
                padding: 10px;       /* 패딩 감소 (15 → 10) */
                text-align: center;
                min-width: 200px;
            }
        """)
        self.status_label.setAlignment(Qt.AlignCenter)
        bottom_layout.addWidget(self.status_label)
        
        bottom_frame.setLayout(bottom_layout)
        
        # 메인 레이아웃에 상/하단 프레임 추가 (4:1 비율)
        main_layout.addWidget(top_frame, stretch=5)
        main_layout.addWidget(bottom_frame, stretch=1)
        
        self.setLayout(main_layout)

    # updateStream 메서드 제거 (실시간 스트리밍 불필요)
    # @pyqtSlot(object)
    # def updateStream(self, frame):
    #     self.displayInspectionImage(frame)

    def displayInspectionImage(self, frame):
        """검사용 이미지 표시 (캡처 이미지만)"""
        if frame is not None:
            try:
                self.current_frame = frame.copy()
                display_frame = frame.copy()
                
                # ROI 박스 그리기
                if self.target_manager and self.target_manager.target_list:
                    for target_id, target in self.target_manager.target_list.items():
                        # 기본 색상 (녹색)
                        box_color = (0, 255, 0)  # BGR 형식
                        text_color = (0, 255, 0)  # BGR 형식
                        thickness = 2
                        
                        # 선택된 ROI는 파란색으로 강조
                        if target_id == self.selected_target_id:
                            box_color = (255, 0, 0)  # BGR 형식 (파란색)
                            text_color = (255, 0, 0)  # BGR 형식 (파란색)
                            thickness = 3
                        
                        # 현재 검사 결과가 있고, 해당 ROI의 결과가 있는 경우에만 색상 변경
                        if self.current_results:
                            for result in self.current_results:
                                if result.get('roi_id') == target_id:
                                    # 디버그 출력 추가
                                    print(f"\n[DEBUG] ROI {target.name} 결과:")
                                    print(f"결과 데이터: {result['results']}")
                                    
                                    is_pass = all(values[-1] for values in result['results'].values())
                                    print(f"Pass/Fail: {is_pass}")
                                    
                                    if not is_pass:
                                        box_color = (0, 0, 255)    # BGR 형식 (빨간색)
                                        text_color = (0, 0, 255)   # BGR 형식 (빨간색)
                                        thickness = 3  # 두껍게 표시
                                    break
                        
                        # 사각형 그리기
                        cv2.rectangle(
                            display_frame,
                            (target.x, target.y),
                            (target.x + target.w, target.y + target.h),
                            box_color,
                            thickness
                        )
                        
                        # 한글 텍스트 처리
                        display_frame = draw_text_with_korean(
                            display_frame,
                            target.name,
                            (target.x, target.y - 20),
                            text_color,
                            font_size=20
                        )
                
                # 이미지 변환 및 표시
                rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
                height, width = rgb_frame.shape[:2]
                bytesPerLine = 3 * width
                qImg = QImage(rgb_frame.data, width, height, bytesPerLine, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qImg)
                
                scaled_pixmap = pixmap.scaled(
                    self.preview_label.size(),
                    Qt.IgnoreAspectRatio,
                    Qt.SmoothTransformation
                )
                
                self.preview_label.setPixmap(scaled_pixmap)
                
            except Exception as e:
                print(f"이미지 처리 중 오류 발생: {str(e)}")
                import traceback
                traceback.print_exc()

    def resizeEvent(self, event):
        """위젯 크기가 변경될 때 이미지 다시 표시"""
        super().resizeEvent(event)
        if self.current_frame is not None:
            self.displayInspectionImage(self.current_frame) 

    def mousePressEvent(self, event):
        if not self.current_frame is None and self.target_manager:
            try:
                # 이미지에서의 실제 클릭 위치 계산
                label_rect = self.preview_label.geometry()
                if not label_rect.contains(event.pos()):
                    return  # 이미지 외부 클릭 무시
                    
                # 이미지 크기에 맞게 좌표 변환
                scale_x = self.current_frame.shape[1] / self.preview_label.width()
                scale_y = self.current_frame.shape[0] / self.preview_label.height()
                
                img_x = int((event.x() - label_rect.x()) * scale_x)
                img_y = int((event.y() - label_rect.y()) * scale_y)
                
                # 클릭된 ROI 찾기
                for target_id, target in self.target_manager.target_list.items():
                    if (target.x <= img_x <= target.x + target.w and 
                        target.y <= img_y <= target.y + target.h):
                        try:
                            # ROI 영역 추출
                            current_roi = self.current_frame[
                                target.y:target.y+target.h, 
                                target.x:target.x+target.w
                            ].copy()
                            
                            # 색상 정보 초기화 체크
                            if not hasattr(target, 'color') or target.color is None:
                                # 중심 색상 이용하여 기본값 설정
                                h, w = current_roi.shape[:2]
                                center_color = current_roi[h//2, w//2]
                                hsv_color = cv2.cvtColor(np.uint8([[center_color]]), cv2.COLOR_BGR2HSV)[0][0]
                                target.color = hsv_color  # 기본 색상 설정
                                print(f"[INFO] ROI {target.name}에 기본 색상 설정: {hsv_color}")
                                
                            # DetailDialog 표시
                            dialog = DetailDialog(target, current_roi, self)
                            dialog.exec_()
                            self.selected_target_id = target_id
                            break
                            
                        except Exception as e:
                            print(f"ROI 상세 정보 표시 중 오류: {str(e)}")
                            import traceback
                            traceback.print_exc()
            except Exception as e:
                print(f"마우스 이벤트 처리 중 오류: {str(e)}")

    def show_mask_for_target(self, target):
        """선택된 ROI의 마스크 이미지 표시"""
        if "hsv" not in target.matching_algorithm:
            return
            
        # 현재 프레임에서 ROI 추출
        current_roi = self.current_frame[
            target.y:target.y+target.h, 
            target.x:target.x+target.w
        ]
        
        # HSV 변환 및 마스크 생성
        hsv_reference = cv2.cvtColor(target.reference_image, cv2.COLOR_BGR2HSV)
        hsv_target = cv2.cvtColor(current_roi, cv2.COLOR_BGR2HSV)
        
        lower_bound, upper_bound = HSVMatching.get_color_range(target.color)
        
        mask_ref = cv2.inRange(hsv_reference, lower_bound, upper_bound)
        mask_targ = cv2.inRange(hsv_target, lower_bound, upper_bound)
        
        # 마스크 이미지 다이얼로그 표시
        dialog = MaskViewDialog(mask_ref, mask_targ, self)
        dialog.exec_()

    def update_inspection_results(self, results):
        """검사 결과 업데이트"""
        self.current_results = results
        
        # 통과 여부 판정 로직 통일
        all_pass = all(
            all(values[-1] for values in result['results'].values())
            for result in results
        )
        
        # 상태 텍스트와 색상 설정
        status_text = "통과" if all_pass else "불통과"
        bg_color = "#4CAF50" if all_pass else "#f44336"
        
        # 상태 레이블 스타일 업데이트
        self.status_label.setText(status_text)
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: white;
                font-weight: bold;
                font-size: 36px;     /* 폰트 크기 감소 (48 → 36) */
                padding: 10px;       /* 패딩 감소 (15 → 10) */
                background-color: {bg_color};
                border-radius: 8px;
                min-width: 200px;
                text-align: center;
            }}
        """)
        
        # 프레임 스타일 업데이트
        self.status_label.parent().setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border-radius: 10px;
                margin: 10px;
                padding: 10px;
            }}
        """)
        
        # 현재 프레임 다시 표시하여 ROI 박스 색상 업데이트
        if self.current_frame is not None:
            self.displayInspectionImage(self.current_frame)
        
        # 불통과 ROI가 있는 경우 상세 다이얼로그 표시
        if not all_pass:
            for result in results:
                if not all(values[-1] for values in result['results'].values()):
                    target = self.target_manager.target_list.get(result['roi_id'])
                    if target:
                        roi_image = self.current_frame[
                            target.y:target.y+target.h, 
                            target.x:target.x+target.w
                        ]
                        dialog = ROIDetailDialog(
                            roi_image,
                            result['roi_name'],
                            result['results'],
                            self
                        )
                        dialog.show()

    def update_preview(self):
        """현재 이미지 업데이트"""
        frame = self.current_frame
        if frame is None:
            return
        
        try:
            # 원본 이미지 복사
            display_frame = frame.copy()
            
            # ROI 박스 그리기
            if self.target_manager and self.target_manager.target_list:
                for target_id, target in self.target_manager.target_list.items():
                    # 기본 색상 (녹색)
                    box_color = (0, 255, 0)  # BGR 형식 (녹색)
                    text_color = (0, 255, 0)  # BGR 형식 (녹색)
                    thickness = 2
                    
                    # 선택된 ROI는 파란색으로 강조
                    if target_id == self.selected_target_id:
                        box_color = (255, 0, 0)  # BGR 형식 (파란색)
                        text_color = (255, 0, 0)  # BGR 형식 (파란색)
                        thickness = 3
                    
                    # 현재 검사 결과가 있고, 해당 ROI의 결과가 있는 경우에만 색상 변경
                    if hasattr(self, 'current_results') and self.current_results:
                        for result in self.current_results:
                            if result.get('roi_id') == target_id:
                                # 알고리즘 결과 확인 
                                is_pass = all(values[-1] for values in result['results'].values())
                                
                                if not is_pass:
                                    box_color = (0, 0, 255)    # BGR 형식 (빨간색)
                                    text_color = (0, 0, 255)   # BGR 형식 (빨간색)
                                    thickness = 3  # 두껍게 표시
                                break
                    
                    # 사각형 그리기
                    cv2.rectangle(
                        display_frame,
                        (target.x, target.y),
                        (target.x + target.w, target.y + target.h),
                        box_color,
                        thickness
                    )
                    
                    # 한글 텍스트 처리
                    display_frame = draw_text_with_korean(
                        display_frame,
                        target.name,
                        (target.x, target.y - 20),
                        text_color,
                        font_size=20
                    )
            
            # QImage로 변환 및 표시
            rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
            h, w, c = rgb_frame.shape
            bytesPerLine = 3 * w
            qImg = QImage(rgb_frame.data, w, h, bytesPerLine, QImage.Format_RGB888)
            self.preview_label.setPixmap(QPixmap.fromImage(qImg))
        
        except Exception as e:
            print(f"미리보기 업데이트 중 오류: {e}")
            import traceback
            traceback.print_exc() 