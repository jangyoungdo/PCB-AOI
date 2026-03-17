from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QSplitter, QFrame, QSizePolicy, QGroupBox, QFormLayout, QLineEdit, QPushButton, QMessageBox, QMainWindow)
from PyQt5.QtCore import Qt, pyqtSignal
import cv2
from PyQt5.QtGui import QImage, QPixmap
from manager.db_manager import DBManager
from datetime import datetime
import json
import uuid  # 고유 ID 생성용
import os
from utils.json_utils import serialize_json_safely

class LeftLayout(QWidget):
    inspection_completed = pyqtSignal(list)  # 검사 완료 시그널 추가
    
    def __init__(self, parent=None, target_manager=None):
        super().__init__(parent)
        self.target_manager = target_manager
        self.current_frame = None  # 현재 프레임 저장용
        self.inspection_running = False
        # DB 매니저 초기화 추가
        self.db_manager = DBManager()
        self.db_manager.db_error.connect(self.show_db_error)
        self.db_manager.db_changed.connect(self.reload_data)
        self.initUI()

    def initUI(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)  # 레이아웃 여백 제거
        self.setLayout(main_layout)

        # 전체 splitter 생성
        self.main_splitter = QSplitter(Qt.Vertical)
        
        # 상단 영역 (2) - 스트리밍 영상
        self.top_widget = QWidget()
        top_layout = QVBoxLayout(self.top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)  # 여백 제거
        top_layout.setSpacing(0)  # 위젯 간 간격 제거
        
        # 스트리밍 영상 레이블
        self.imageLabel = QLabel()
        self.imageLabel.setAlignment(Qt.AlignCenter)
        self.imageLabel.setText("스트리밍 영상")
        self.imageLabel.setStyleSheet("""
            QLabel { 
                background-color: #f0f0f0;
                min-height: 360px;  /* 최소 높이 설정 */
            }
        """)
        self.imageLabel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # 크기 정책 설정
        top_layout.addWidget(self.imageLabel)
        
        # 상단-중단 구분선
        top_line = QFrame()
        top_line.setFrameShape(QFrame.HLine)
        top_line.setFrameShadow(QFrame.Sunken)
        top_layout.addWidget(top_line)
        
        # 중단 영역 (4)
        self.middle_widget = QWidget()
        middle_layout = QVBoxLayout(self.middle_widget)
        middle_layout.setContentsMargins(5, 5, 5, 5)  # 전체 여백 축소
        
        # 장비 정보
        equipment_group = QGroupBox("장비 정보")
        equipment_group.setStyleSheet("""
            QGroupBox {
                font-size: 20px;     /* 폰트 크기 감소 */
                font-weight: bold;
                margin-top: 10px;    /* 여백 감소 */
                padding: 10px;       /* 내부 여백 유지 */
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 3px 3px;    /* 제목 주변 여백 감소 */
                margin-top: 3px;     /* 제목과 내용 사이 간격 감소 */
            }
            QLabel {
                font-size: 16px;     /* 폰트 크기 감소 */
                margin-top: 3px;    
                margin-bottom: 2px;
            }
            QLineEdit {
                font-size: 16px;     /* 폰트 크기 감소 */
                padding: 3px;        /* 패딩 감소 */
                margin: 2px 0px;     /* 상하 여백 감소 */
                background-color: white;
                border: 1px solid #CCCCCC;
                min-height: 25px;    /* 높이 감소 */
            }
        """)
        equipment_layout = QFormLayout()
        equipment_layout.setSpacing(10)  # 항목 간 간격 축소
        equipment_layout.setContentsMargins(10, 10, 10, 10)  # 여백 축소
        
        self.equipment_id = QLineEdit()
        self.equipment_id.setReadOnly(True)
        equipment_layout.addRow("장비 ID:", self.equipment_id)
        
        self.equipment_name = QLineEdit()
        self.equipment_name.setReadOnly(True)
        equipment_layout.addRow("장비 이름:", self.equipment_name)
        
        self.manager = QLineEdit()
        self.manager.setReadOnly(True)
        equipment_layout.addRow("관리자:", self.manager)
        equipment_group.setLayout(equipment_layout)
        middle_layout.addWidget(equipment_group)
        
        # 제품 정보
        product_group = QGroupBox("제품 정보")
        product_group.setStyleSheet(equipment_group.styleSheet())
        product_layout = QFormLayout()
        product_layout.setSpacing(10)
        product_layout.setContentsMargins(10, 10, 10, 10)
        
        self.product_id = QLineEdit()
        self.product_id.setReadOnly(True)
        product_layout.addRow("제품 ID:", self.product_id)
        
        self.product_name = QLineEdit()
        self.product_name.setReadOnly(True)
        product_layout.addRow("제품 이름:", self.product_name)
        product_group.setLayout(product_layout)
        middle_layout.addWidget(product_group)
        
        # 생산 정보
        production_group = QGroupBox("생산 정보")
        production_group.setStyleSheet(equipment_group.styleSheet())
        production_layout = QFormLayout()
        production_layout.setSpacing(10)
        production_layout.setContentsMargins(10, 10, 10, 10)
        
        self.production_count = QLineEdit()
        self.production_count.setReadOnly(True)
        self.production_count.setText("0")
        production_layout.addRow("생산 개수:", self.production_count)
        
        self.defect_count = QLineEdit()
        self.defect_count.setReadOnly(True)
        self.defect_count.setText("0")
        production_layout.addRow("불량 개수:", self.defect_count)
        production_group.setLayout(production_layout)
        middle_layout.addWidget(production_group)
        
        # 나머지 공간을 채우기 위한 스트레치
        middle_layout.addStretch()
        
        # 중단-하단 구분선
        bottom_line = QFrame()
        bottom_line.setFrameShape(QFrame.HLine)
        bottom_line.setFrameShadow(QFrame.Sunken)
        middle_layout.addWidget(bottom_line)
        
        # 하단 영역 (1)
        self.bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(self.bottom_widget)
        bottom_layout.setContentsMargins(5, 5, 5, 5)  # 여백 최소화
        
        # 검사 제어 버튼 스타일
        self.button_style = """
            QPushButton {
                font-size: 25px;
                font-weight: bold;
                padding: 20px;
                min-height: 80px;
                background-color: %s;
                color: white;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: %s;
            }
            QPushButton:pressed {
                background-color: %s;
            }
        """
        
        # 검사 토글 버튼
        self.inspection_button = QPushButton('검사 시작')
        self.inspection_button.setStyleSheet(
            self.button_style % ('#4CAF50', '#45a049', '#3d8b40')  # 초록색 계열
        )
        self.inspection_button.clicked.connect(self.toggle_inspection)
        bottom_layout.addWidget(self.inspection_button)
        
        # Splitter에 위젯 추가
        self.main_splitter.addWidget(self.top_widget)
        self.main_splitter.addWidget(self.middle_widget)
        self.main_splitter.addWidget(self.bottom_widget)
        
        # Splitter 비율 설정 수정 (3:5:2 → 2.5:5.5:2)
        total_height = 700  # 예시 높이
        self.main_splitter.setSizes([
            int(total_height * 2.5/10),  # 상단 (25%)
            int(total_height * 5.5/10),  # 중단 (55%)
            int(total_height * 2/10)     # 하단 (20%)
        ])
        
        # GroupBox 스타일 조정
        equipment_group.setStyleSheet("""
            QGroupBox {
                font-size: 20px;     /* 폰트 크기 감소 */
                font-weight: bold;
                margin-top: 10px;    /* 여백 감소 */
                padding: 10px;       /* 내부 여백 유지 */
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 3px 3px;    /* 제목 주변 여백 감소 */
                margin-top: 3px;     /* 제목과 내용 사이 간격 감소 */
            }
            QLabel {
                font-size: 16px;     /* 폰트 크기 감소 */
                margin-top: 3px;    
                margin-bottom: 2px;
            }
            QLineEdit {
                font-size: 16px;     /* 폰트 크기 감소 */
                padding: 3px;        /* 패딩 감소 */
                margin: 2px 0px;     /* 상하 여백 감소 */
                background-color: white;
                border: 1px solid #CCCCCC;
                min-height: 25px;    /* 높이 감소 */
            }
        """)
        
        main_layout.addWidget(self.main_splitter)

    def displayImage(self, frame):
        """OpenCV 이미지를 QLabel에 표시"""
        if frame is not None:
            self.current_frame = frame  # 프레임 저장
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            height, width = rgb_frame.shape[:2]
            bytesPerLine = 3 * width
            qImg = QImage(rgb_frame.data, width, height, bytesPerLine, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qImg)
            
            label_size = self.imageLabel.size()
            scaled_pixmap = pixmap.scaled(label_size, 
                                        Qt.KeepAspectRatio, 
                                        Qt.SmoothTransformation)
            self.imageLabel.setPixmap(scaled_pixmap)

    def update_equipment_info(self, equipment_data):
        """장비 정보 업데이트"""
        if equipment_data:
            self.equipment_id.setText(equipment_data['equipment_id'])
            self.equipment_name.setText(equipment_data['equipment_name'])
            self.manager.setText(equipment_data['manager'])

    def update_product_info(self, product_data):
        """제품 정보 업데이트"""
        if not product_data:
            return
        
        self.product_id.setText(product_data['product_id'])
        self.product_name.setText(product_data['product_name'])
        
        # ROI 정보는 main_window에서 처리하므로 여기서는 생략

    def update_production_info(self, production_count=0, defect_count=0):
        """생산 정보 업데이트"""
        self.production_count.setText(str(production_count))
        self.defect_count.setText(str(defect_count))

    def toggle_inspection(self):
        self.inspection_running = not self.inspection_running
        
        if self.inspection_running:
            print(f"검사 시작 전 ROI 확인: {len(self.target_manager.target_list) if self.target_manager else 0}개")
            if not self.target_manager or not self.target_manager.target_list:
                QMessageBox.warning(self, "검사 오류", "등록된 검사 대상이 없습니다.")
                self.inspection_running = False
                return
            
            if self.current_frame is None:
                QMessageBox.warning(self, "검사 오류", "카메라 영상을 불러올 수 없습니다.")
                self.inspection_running = False
                return
            
            # MainWindow 찾기
            parent = self.parent()
            while parent and not isinstance(parent, QMainWindow):
                parent = parent.parent()
            
            if parent and hasattr(parent, 'center_widget'):
                parent.center_widget.displayInspectionImage(self.current_frame.copy())
            else:
                print("center_widget을 찾을 수 없습니다.")
                return
            
            self.inspection_button.setText('검사 중지')
            self.inspection_button.setStyleSheet(
                self.button_style % ('#f44336', '#e53935', '#d32f2f')
            )
            self.start_inspection()

    def start_inspection(self):
        """검사 시작"""
        if not self.target_manager or not self.target_manager.target_list:
            QMessageBox.warning(self, "검사 시작 실패", "등록된 검사 대상이 없습니다.")
            return
        
        print(f"검사 시작 - 등록된 ROI 개수: {len(self.target_manager.target_list)}")
        for target_id, target in self.target_manager.target_list.items():
            print(f"ROI 정보 - 이름: {target.name}, 알고리즘: {target.matching_algorithm}")
        
        # 기존 검사 로직
        if not self.inspection_running:
            return
            
        # 필수 정보 검증
        if not self.product_id.text():
            QMessageBox.warning(self, "검사 오류", "제품이 선택되지 않았습니다.")
            return
        
        if not self.equipment_id.text():
            QMessageBox.warning(self, "검사 오류", "장비가 선택되지 않았습니다.")
            return
        
        try:
            all_results = []
            db_manager = DBManager()
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
            
            # 프로젝트 루트 디렉토리 찾기
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            
            # 날짜별 기본 디렉토리 생성
            base_image_dir = os.path.join(project_root, 'inspection_images', 
                                        datetime.now().strftime("%Y%m%d"))
            
            # pass/fail 디렉토리 생성
            pass_dir = os.path.join(base_image_dir, 'pass')
            fail_dir = os.path.join(base_image_dir, 'fail')
            
            os.makedirs(pass_dir, exist_ok=True)
            os.makedirs(fail_dir, exist_ok=True)
            
            # 검사 시작 시 ROI 목록 복사
            target_list = dict(self.target_manager.target_list)
            
            # 한 번의 검사에 대한 전체 결과를 저장할 변수
            inspection_pass = True  # 전체 검사 결과 (하나라도 실패하면 False)
            
            for target_id, target in target_list.items():
                roi = self.current_frame[target.y:target.y+target.h, 
                                      target.x:target.x+target.w].copy()
                
                if roi is None or roi.size == 0:
                    print(f"[경고] ROI {target.name}의 영역이 유효하지 않습니다.")
                    continue
                    
                results = self.target_manager.run_inspection(target_id, roi)
                all_results.extend(results)
                
                # 각 ROI의 검사 결과 확인
                for result in results:
                    is_pass = all(values[-1] for values in result['results'].values())
                    if not is_pass:
                        inspection_pass = False  # 하나라도 실패하면 전체 검사 실패
                    
                    # 결과에 따라 저장 디렉토리 선택
                    save_dir = pass_dir if is_pass else fail_dir
                    
                    # 파일명 생성 (영문/숫자만 사용)
                    safe_name = ''.join(c if c.isascii() and c.isalnum() else '_' 
                                      for c in target.name)
                    image_filename = f'INSP_{timestamp}_{safe_name}_{uuid.uuid4().hex[:8]}.jpg'
                    image_path = os.path.join(save_dir, image_filename)
                    
                    try:
                        # ROI 이미지 그대로 저장 (텍스트 추가 없이)
                        cv2.imwrite(image_path, roi)
                        
                    except Exception as img_error:
                        print(f"[오류] 이미지 저장 실패: {str(img_error)}")
                        image_path = "저장 실패"
                    
                    # DB 저장 로직
                    inspection_data = {
                        'result_id': f"INSP_{timestamp}_{uuid.uuid4().hex[:8]}",
                        'production_date': datetime.now().date(),
                        'product_id': self.product_id.text(),
                        'equipment_id': self.equipment_id.text(),
                        'inspection_datetime': datetime.now(),
                        'roi_results': serialize_json_safely({
                            'roi_name': result['roi_name'],
                            'roi_id': result['roi_id'],
                            'results': result['results']
                        }),
                        'image_path': image_path,
                        'overall_result': 'PASS' if is_pass else 'FAIL'
                    }
                    
                    try:
                        db_manager.insert_inspection_result(inspection_data)
                    except Exception as db_error:
                        print(f"검사 결과 저장 중 오류 발생: {str(db_error)}")
            
            # 검사 결과 출력
            if not all_results:
                print("\n[알림] 검사 결과가 없습니다.")
            else:
                print("\n[알림] 검사 완료")
                print(f"전체 결과: {'통과' if inspection_pass else '불통과'}")
                print("================================")
            
            # 제품 단위로 카운트 증가 (ROI가 아닌 전체 검사 기준)
            current_prod = int(self.production_count.text()) + 1  # 한 번의 검사당 1개 증가
            current_defect = int(self.defect_count.text()) + (0 if inspection_pass else 1)  # 불량인 경우만 1 증가
            
            try:
                # 생산 정보 업데이트
                production_data = {
                    'production_date': datetime.now().date(),
                    'product_id': self.product_id.text(),
                    'equipment_id': self.equipment_id.text(),
                    'production_count': current_prod,
                    'defect_count': current_defect
                }
                db_manager.update_or_insert_production(production_data)
                
                # UI 업데이트
                self.production_count.setText(str(current_prod))
                self.defect_count.setText(str(current_defect))
                
            except Exception as db_error:
                print(f"생산 정보 저장 중 오류 발생: {str(db_error)}")
            
            # 검사 결과 전송
            self.inspection_completed.emit(all_results)
            
        except Exception as e:
            QMessageBox.critical(self, "검사 오류", f"검사 중 오류가 발생했습니다: {str(e)}")
        finally:
            # 검사 종료 후 상태 변경
            self.inspection_running = False
            self.inspection_button.setText('검사 시작')
            self.inspection_button.setStyleSheet(
                self.button_style % ('#4CAF50', '#45a049', '#3d8b40')
            ) 

    def reload_data(self):
        """DB 변경 시 데이터 갱신"""
        try:
            # 현재 표시된 장비 ID 가져오기
            equipment_id = self.equipment_id.text()
            if equipment_id:
                # 장비 정보 갱신
                equipment_data = self.db_manager.get_equipment_by_id(equipment_id)
                if equipment_data:
                    self.update_equipment_info(equipment_data)
                else:
                    self.clear_equipment_info()

            # 현재 표시된 제품 ID 가져오기
            product_id = self.product_id.text()
            if product_id:
                # 제품 정보 갱신
                product_data = self.db_manager.get_product_by_id(product_id)
                if product_data:
                    self.update_product_info(product_data)
                else:
                    self.clear_product_info()

            # 생산 정보 초기화
            self.update_production_info(0, 0)

        except Exception as e:
            QMessageBox.warning(self, "데이터 갱신 오류", f"데이터 갱신 중 오류가 발생했습니다: {str(e)}")

    def clear_equipment_info(self):
        """장비 정보 초기화"""
        self.equipment_id.clear()
        self.equipment_name.clear()
        self.manager.clear()

    def clear_product_info(self):
        """제품 정보 초기화"""
        self.product_id.clear()
        self.product_name.clear()

    # 에러 처리 메서드 추가
    def show_db_error(self, error_msg):
        """DB 에러 메시지 표시"""
        QMessageBox.critical(self, "DB 오류", error_msg) 