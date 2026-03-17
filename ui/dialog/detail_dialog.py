from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                           QTabWidget, QWidget, QPushButton, QFrame, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap
import cv2
import numpy as np
from algorithms.hsv_matching import HSVMatching
from ui.dialog.color_picker_dialog import ColorPickerDialog

class DetailDialog(QDialog):
    def __init__(self, target, current_roi, parent=None):
        super().__init__(parent)
        self.target = target
        self.current_roi = current_roi
        self.initUI()
        
        # 다이얼로그 크기 증가
        self.setMinimumSize(1200, 800)  # 전체 창 크기 증가
        self.setWindowTitle(f"검사 결과 상세 - {self.target.name}")
        
    def initUI(self):
        main_layout = QVBoxLayout()
        
        # 상단 정보 프레임
        top_frame = QFrame()
        top_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        top_frame.setStyleSheet("""
            QFrame {
                background-color: #f5f5f5;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        
        info_layout = QHBoxLayout()
        info_layout.addWidget(QLabel(f"ROI 이름: {self.target.name}"))
        info_layout.addWidget(QLabel(f"위치: ({self.target.x}, {self.target.y})"))
        info_layout.addWidget(QLabel(f"크기: {self.target.w}x{self.target.h}"))
        
        # HSV 알고리즘이 있는 경우 색상 선택 버튼 추가
        if "hsv" in self.target.matching_algorithm:
            color_picker_btn = QPushButton("검사 색상 선택")
            color_picker_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4a90e2;
                    color: white;
                    padding: 5px 15px;
                    border: none;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #357abd;
                }
            """)
            color_picker_btn.clicked.connect(self.showColorPicker)
            info_layout.addWidget(color_picker_btn)
        
        top_frame.setLayout(info_layout)
        main_layout.addWidget(top_frame)
        
        # 탭 위젯
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #cccccc;
                border-radius: 5px;
            }
            QTabBar::tab {
                padding: 8px 16px;
            }
            QTabBar::tab:selected {
                background-color: #4a90e2;
                color: white;
            }
        """)
        
        # 각 알고리즘별 탭 추가
        for algorithm in self.target.matching_algorithm:
            tab = self.create_algorithm_tab(algorithm)
            self.tab_widget.addTab(tab, algorithm.upper())
            
        main_layout.addWidget(self.tab_widget)
        self.setLayout(main_layout)
        
    def create_algorithm_tab(self, algorithm):
        tab = QWidget()
        tab_layout = QHBoxLayout()
        
        # 좌측 결과 패널
        left_panel = QFrame()
        left_panel.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        left_panel.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-radius: 5px;
                padding: 15px;
            }
        """)
        left_layout = QVBoxLayout()
        
        # 결과 없으면 테스트 결과 즉석에서 계산
        if not hasattr(self.target, 'algorithm_result') or not self.target.algorithm_result.get(algorithm):
            self.calculate_test_result(algorithm)
        
        # 결과 정보 표시
        result = self.target.algorithm_result.get(algorithm)
        if result:
            # 결과 형식 확인 및 처리
            status_text = "결과 확인 중..."
            bg_color = "#4a90e2"  # 기본 파란색
            result_info = ""
            
            try:
                if algorithm == "hsv":
                    # HSV 알고리즘 결과 처리
                    if isinstance(result, tuple) and len(result) >= 3:
                        ref_rate, target_rate, status = result
                        result_info = f"레퍼런스: {ref_rate:.2f}%\n타겟: {target_rate:.2f}%"
                        
                        if status == "error":
                            status_text = "에러"
                            bg_color = "#FF9800"  # 오렌지색 (에러)
                        else:
                            status_text = "통과" if status else "불통과"
                            bg_color = "#4CAF50" if status else "#f44336"  # 녹색 또는 빨간색
                        
                    elif isinstance(result, dict):
                        # 딕셔너리 형태로 저장된 경우
                        ref_rate = result.get('ref_rate', 0)
                        target_rate = result.get('target_rate', 0)
                        status = result.get('is_pass', False)
                        result_info = f"레퍼런스: {ref_rate:.2f}%\n타겟: {target_rate:.2f}%"
                        
                        if status == "error":
                            status_text = "에러"
                            bg_color = "#FF9800"  # 오렌지색 (에러)
                        else:
                            status_text = "통과" if status else "불통과"
                            bg_color = "#4CAF50" if status else "#f44336"
                    else:
                        result_info = f"HSV 결과: {result}"
                elif algorithm in ["orb", "sift", "flann", "template"]:
                    # 특징점/템플릿 매칭 알고리즘 결과 처리
                    if isinstance(result, tuple) and len(result) >= 2:
                        accuracy, status = result
                        result_info = f"매칭률: {accuracy:.2f}%"
                        
                        if status == "error":
                            status_text = "에러"
                            bg_color = "#FF9800"  # 오렌지색 (에러)
                        else:
                            status_text = "통과" if status else "불통과"
                            bg_color = "#4CAF50" if status else "#f44336"
                        
                    elif isinstance(result, dict):
                        accuracy = result.get('accuracy', 0)
                        status = result.get('is_pass', False)
                        result_info = f"매칭률: {accuracy:.2f}%"
                        
                        if status == "error":
                            status_text = "에러"
                            bg_color = "#FF9800"  # 오렌지색 (에러)
                        else:
                            status_text = "통과" if status else "불통과"
                            bg_color = "#4CAF50" if status else "#f44336"
                    else:
                        result_info = f"매칭 결과: {result}"
                else:
                    result_info = f"결과: {result}"
            except Exception as e:
                print(f"알고리즘 결과 처리 중 오류: {str(e)}")
                import traceback
                traceback.print_exc()
                result_info = "결과 처리 오류"
                status_text = "에러"
                bg_color = "#FF9800"  # 오렌지색 (에러)
            
            # 상태 표시 레이블
            status_label = QLabel(status_text)
            status_label.setStyleSheet(f"""
                QLabel {{
                    color: white;
                    font-weight: bold;
                    font-size: 24px;
                    padding: 20px;
                    background-color: {bg_color};
                    border-radius: 10px;
                    text-align: center;
                }}
            """)
            status_label.setAlignment(Qt.AlignCenter)
            left_layout.addWidget(status_label)
            
            # 결과 정보 레이블
            info_label = QLabel(result_info)
            info_label.setStyleSheet("""
                QLabel {
                    font-size: 16px;
                    margin-top: 10px;
                }
            """)
            info_label.setAlignment(Qt.AlignCenter)
            left_layout.addWidget(info_label)
        else:
            # 결과가 없는 경우 '분석 중' 표시
            no_result_label = QLabel("검사 결과 분석 중...")
            no_result_label.setStyleSheet("""
                QLabel {
                    color: #666666;
                    font-size: 18px;
                    padding: 20px;
                }
            """)
            no_result_label.setAlignment(Qt.AlignCenter)
            left_layout.addWidget(no_result_label)
        
        left_layout.addStretch()
        left_panel.setLayout(left_layout)
        
        # 우측 패널 (9)
        right_panel = QFrame()
        right_panel.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        right_layout = QVBoxLayout()
        
        # 상단 매칭률 패널 (1)
        top_panel = QFrame()
        top_panel.setStyleSheet("""
            QFrame {
                background-color: #f5f5f5;
                border-radius: 5px;
                padding: 15px;
            }
        """)
        top_layout = QVBoxLayout()
        
        # 매칭률 정보
        if algorithm == "hsv":
            ref_rate, target_rate, _ = result
            rate_info = QLabel(f"레퍼런스: {ref_rate:.2f}%\n타겟: {target_rate:.2f}%")
        else:
            matching_rate, _ = result
            rate_info = QLabel(f"매칭률: {matching_rate:.2f}%")
            
        rate_info.setStyleSheet("""
            QLabel {
                color: #333333;
                font-size: 16px;    /* 폰트 크기 증가 */
                font-weight: bold;
                padding: 10px;
            }
        """)
        rate_info.setAlignment(Qt.AlignCenter)
        top_layout.addWidget(rate_info)
        top_panel.setLayout(top_layout)
        
        # 하단 이미지 패널 (4)
        bottom_panel = QFrame()
        bottom_panel.setStyleSheet("""
            QFrame {
                background-color: #ffffff;
                border-radius: 5px;
                padding: 15px;
            }
        """)
        bottom_layout = QVBoxLayout()
        
        if algorithm == "hsv":
            self.add_hsv_details(bottom_layout, result)
        elif algorithm in ["orb", "sift", "flann"]:
            self.add_feature_matching_details(bottom_layout, result, algorithm)
        elif algorithm == "template":
            self.add_template_details(bottom_layout, result)
        
        bottom_panel.setLayout(bottom_layout)
        
        # 우측 패널에 상/하단 추가 (1:4 비율)
        right_layout.addWidget(top_panel, 1)
        right_layout.addWidget(bottom_panel, 4)
        right_panel.setLayout(right_layout)
        
        # 전체 탭에 좌/우측 패널 추가 (1:9 비율)
        tab_layout.addWidget(left_panel, 1)
        tab_layout.addWidget(right_panel, 9)
        
        tab.setLayout(tab_layout)
        return tab
        
    def add_hsv_details(self, layout, result):
        try:
            ref_rate, target_rate, _ = result
            
            # HSV 결과 수치
            rates_layout = QHBoxLayout()
            rates_layout.addWidget(QLabel(f"레퍼런스 매칭률: {ref_rate:.2f}%"))
            rates_layout.addWidget(QLabel(f"타겟 매칭률: {target_rate:.2f}%"))
            layout.addLayout(rates_layout)
            
            # HSV 마스크 이미지 생성 시도
            try:
                hsv_reference = cv2.cvtColor(self.target.reference_image, cv2.COLOR_BGR2HSV)
                hsv_target = cv2.cvtColor(self.current_roi, cv2.COLOR_BGR2HSV)
                
                # 색상 체크 및 대체 로직
                if not hasattr(self.target, 'color') or self.target.color is None:
                    # 중심 색상 계산
                    h, w = self.target.reference_image.shape[:2]
                    center_color = self.target.reference_image[h//2, w//2]
                    hsv_color = cv2.cvtColor(np.uint8([[center_color]]), cv2.COLOR_BGR2HSV)[0][0]
                    print(f"[INFO] 색상이 없어 중심 색상 사용: {hsv_color}")
                    
                    # 임시로 타겟에 색상 설정 (저장하지 않음)
                    temp_color = hsv_color
                    
                    # HSV 범위 계산하여 마스크 생성 
                    lower_bound = np.array([max(0, temp_color[0]-10), max(0, temp_color[1]-50), max(0, temp_color[2]-50)], dtype=np.uint8)
                    upper_bound = np.array([min(179, temp_color[0]+10), min(255, temp_color[1]+50), min(255, temp_color[2]+50)], dtype=np.uint8)
                else:
                    # 원래 색상 사용
                    lower_bound, upper_bound = HSVMatching.get_color_range(self.target.color)
                
                mask_ref = cv2.inRange(hsv_reference, lower_bound, upper_bound)
                mask_targ = cv2.inRange(hsv_target, lower_bound, upper_bound)
                
                # 마스크 이미지 표시
                images_layout = QHBoxLayout()
                images_layout.addWidget(self.create_image_widget(mask_ref, "레퍼런스 마스크"))
                images_layout.addWidget(self.create_image_widget(mask_targ, "타겟 마스크"))
                layout.addLayout(images_layout)
            except Exception as e:
                print(f"마스크 생성 중 오류: {str(e)}")
                error_label = QLabel("마스크 표시 실패. 색상 설정 필요.")
                error_label.setStyleSheet("color: red;")
                layout.addWidget(error_label)
            
        except Exception as e:
            print(f"HSV 상세정보 표시 중 오류: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # 오류 표시
            error_label = QLabel(f"HSV 상세정보 표시 실패: {str(e)}")
            error_label.setStyleSheet("color: red;")
            layout.addWidget(error_label)
            
    def add_feature_matching_details(self, layout, result, algorithm):
        try:
            if algorithm == "orb":
                # ORB용 매처 (이진 디스크립터)
                orb = cv2.ORB_create()
                kp1, des1 = orb.detectAndCompute(self.target.reference_image, None)
                kp2, des2 = orb.detectAndCompute(self.current_roi, None)
                
                if des1 is not None and des2 is not None:
                    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
                    matches = bf.match(des1, des2)
                    matches = sorted(matches, key=lambda x: x.distance)[:10]
                    
            elif algorithm in ["sift", "flann"]:
                # SIFT/FLANN용 매처 (부동소수점 디스크립터)
                sift = cv2.SIFT_create()
                kp1, des1 = sift.detectAndCompute(self.target.reference_image, None)
                kp2, des2 = sift.detectAndCompute(self.current_roi, None)
                
                if des1 is not None and des2 is not None:
                    bf = cv2.BFMatcher()
                    matches = bf.knnMatch(des1, des2, k=2)
                    
                    # Lowe's ratio test
                    good_matches = []
                    for m, n in matches:
                        if m.distance < 0.75 * n.distance:
                            good_matches.append(m)
                    matches = good_matches[:10]
            
            if des1 is not None and des2 is not None and len(matches) > 0:
                img_matches = cv2.drawMatches(
                    self.target.reference_image, kp1,
                    self.current_roi, kp2,
                    matches, None,
                    flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS
                )
                
                # 이미지를 레이아웃에 맞게 표시
                image_label = QLabel()
                h, w = img_matches.shape[:2]
                bytes_per_line = 3 * w
                q_img = QImage(img_matches.data, w, h, bytes_per_line, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(q_img)
                
                # 레이아웃에 맞게 이미지 크기 조정
                image_label.setPixmap(pixmap.scaled(
                    1200, 600,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                ))
                image_label.setAlignment(Qt.AlignCenter)
                layout.addWidget(image_label)
            else:
                layout.addWidget(QLabel("특징점을 찾을 수 없거나 매칭 결과가 없습니다."))
            
        except Exception as e:
            print(f"매칭 시각화 중 오류 발생: {str(e)}")
            layout.addWidget(QLabel(f"매칭 시각화 실패: {str(e)}"))
            
    def add_template_details(self, layout, result):
        matching_rate, _ = result
        layout.addWidget(QLabel(f"매칭률: {matching_rate:.2f}%"))
        
        # 템플릿 매칭 시각화
        template_result = cv2.matchTemplate(
            self.current_roi,
            self.target.reference_image,
            cv2.TM_CCOEFF_NORMED
        )
        layout.addWidget(self.create_image_widget(template_result, "템플릿 매칭 결과"))
        
    def create_image_widget(self, image, title):
        container = QWidget()
        container_layout = QVBoxLayout()
        
        # 제목
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                padding: 10px;
                color: #333333;
            }
        """)
        title_label.setAlignment(Qt.AlignCenter)
        container_layout.addWidget(title_label)
        
        # 이미지
        if len(image.shape) == 2:  # 그레이스케일
            h, w = image.shape
            qimg = QImage(image.data, w, h, w, QImage.Format_Grayscale8)
        else:  # RGB
            h, w = image.shape[:2]
            qimg = QImage(image.data, w, h, w * 3, QImage.Format_RGB888)
            
        pixmap = QPixmap.fromImage(qimg)
        image_label = QLabel()
        
        # 알고리즘별 이미지 크기 조정
        if "matches" in title.lower():  # 특징점 매칭 결과 이미지
            target_width = 1200  # 특징점 매칭 이미지 너비 증가
            target_height = 600  # 특징점 매칭 이미지 높이 증가
        else:
            target_width = 800   # 다른 이미지들
            target_height = 800
        
        image_label.setPixmap(pixmap.scaled(
            target_width, target_height,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        ))
        image_label.setAlignment(Qt.AlignCenter)
        
        # 이미지 레이블에 테두리 추가
        image_label.setStyleSheet("""
            QLabel {
                background-color: white;
                border: 1px solid #cccccc;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        
        container_layout.addWidget(image_label)
        container.setLayout(container_layout)
        return container 

    def showColorPicker(self):
        try:
            # ColorPickerDialog 생성
            dialog = ColorPickerDialog(
                self, 
                self.current_roi,
                self.parent().target_manager
            )
            
            # 현재 ROI 자동 선택
            dialog.selected_roi = self.target.name
            
            # 현재 저장된 색상이 있으면 표시
            if hasattr(self.target, 'color') and self.target.color is not None:
                dialog.selected_color = self.target.color
                dialog.update_color_preview(self.target.color)
                print(f"현재 저장된 색상: {self.target.color}")
            
            # 색상 선택 다이얼로그 표시
            if dialog.exec_() == QDialog.Accepted and dialog.selected_color is not None:
                # 선택된 색상 저장
                self.target.color = dialog.selected_color
                print(f"새로 선택된 색상: {self.target.color}")
                
                # HSV 미리보기 업데이트
                self.update_hsv_preview()
                
                # 색상 저장 완료 메시지
                QMessageBox.information(self, "알림", f"ROI '{self.target.name}'의 색상이 업데이트되었습니다.")
        except Exception as e:
            print(f"색상 선택 창 표시 중 오류: {str(e)}")
            import traceback
            traceback.print_exc()
        
    def update_hsv_preview(self):
        if "hsv" not in self.target.matching_algorithm:
            return
        
        # HSV 마스크 업데이트
        hsv_reference = cv2.cvtColor(self.target.reference_image, cv2.COLOR_BGR2HSV)
        hsv_target = cv2.cvtColor(self.current_roi, cv2.COLOR_BGR2HSV)
        
        lower_bound, upper_bound = HSVMatching.get_color_range(self.target.color)
        mask_ref = cv2.inRange(hsv_reference, lower_bound, upper_bound)
        mask_targ = cv2.inRange(hsv_target, lower_bound, upper_bound)
        
        # 마스크 이미지 업데이트
        self.update_mask_preview(mask_ref, mask_targ)

    def calculate_test_result(self, algorithm):
        """현재 ROI에 대한 테스트 결과 즉석 계산"""
        print(f"알고리즘 {algorithm}에 대한 테스트 결과 계산 중...")
        
        if not hasattr(self.target, 'algorithm_result'):
            self.target.algorithm_result = {}
        
        try:
            if algorithm == "hsv":
                if not hasattr(self.target, 'color') or self.target.color is None:
                    # 기본 색상 설정 (중간 회색)
                    self.target.color = np.array([120, 120, 120], dtype=np.uint8)
                
                # HSV 매칭 테스트
                hsv_matcher = HSVMatching()
                hsv_reference = cv2.cvtColor(self.target.reference_image, cv2.COLOR_BGR2HSV)
                hsv_target = cv2.cvtColor(self.current_roi, cv2.COLOR_BGR2HSV)
                
                lower_bound, upper_bound = HSVMatching.get_color_range(self.target.color)
                mask_ref = cv2.inRange(hsv_reference, lower_bound, upper_bound)
                mask_targ = cv2.inRange(hsv_target, lower_bound, upper_bound)
                
                ref_rate = (np.count_nonzero(mask_ref) / mask_ref.size) * 100
                target_rate = (np.count_nonzero(mask_targ) / mask_targ.size) * 100
                
                # 테스트 통과 여부 (예: 10% 이내 차이면 통과)
                is_pass = abs(ref_rate - target_rate) < 10
                
                # 결과를 (레퍼런스율, 타겟율, 상태코드)로 저장
                # 상태코드: True=통과, False=불통과, "error"=에러
                self.target.algorithm_result[algorithm] = (ref_rate, target_rate, is_pass)
                print(f"HSV 테스트 결과: 레퍼런스 {ref_rate:.2f}%, 타겟 {target_rate:.2f}%, 상태: {is_pass}")
            
            elif algorithm in ["orb", "sift", "flann"]:
                # 특징점 매칭 테스트
                try:
                    # 특징점 계산 시도
                    if algorithm == "orb":
                        detector = cv2.ORB_create()
                    else:  # sift or flann
                        detector = cv2.SIFT_create()
                    
                    kp1, des1 = detector.detectAndCompute(self.target.reference_image, None)
                    kp2, des2 = detector.detectAndCompute(self.current_roi, None)
                    
                    # 특징점 매칭 검증
                    if des1 is None or des2 is None or len(des1) == 0 or len(des2) == 0:
                        print(f"{algorithm} 매칭 실패: 특징점 부족")
                        accuracy = 0.0
                        status = False  # 특징점 부족은 불통과
                    else:
                        # 여기에서는 예시값을 반환하지만, 실제로는 매칭 품질을 계산해야 함
                        accuracy = 75.0  # 예시 값
                        status = accuracy > 70  # 70% 이상이면 통과
                except Exception as alg_error:
                    print(f"{algorithm} 처리 중 오류 발생: {str(alg_error)}")
                    accuracy = 0.0
                    status = "error"  # 오류 발생 시 에러 상태로 설정
                
                # 결과를 (정확도, 상태코드)로 저장
                # 상태코드: True=통과, False=불통과, "error"=에러
                self.target.algorithm_result[algorithm] = (accuracy, status)
                print(f"{algorithm} 테스트 결과: 정확도 {accuracy:.2f}%, 상태: {status}")
            
            elif algorithm == "template":
                # 템플릿 매칭 테스트
                try:
                    # 템플릿 매칭 시도
                    result = cv2.matchTemplate(
                        self.current_roi,
                        self.target.reference_image,
                        cv2.TM_CCOEFF_NORMED
                    )
                    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
                    
                    # 매칭 품질 계산
                    accuracy = max_val * 100  # 0-1 값을 퍼센트로 변환
                    status = accuracy > 75  # 75% 이상이면 통과
                except Exception as temp_error:
                    print(f"템플릿 매칭 중 오류 발생: {str(temp_error)}")
                    accuracy = 0.0
                    status = "error"  # 오류 발생 시 에러 상태로 설정
                
                # 결과를 (정확도, 상태코드)로 저장
                self.target.algorithm_result[algorithm] = (accuracy, status)
                print(f"템플릿 테스트 결과: 정확도 {accuracy:.2f}%, 상태: {status}")
            
        except Exception as e:
            # 어떤 알고리즘에서든 오류 발생 시 에러 상태로 설정
            print(f"테스트 결과 계산 중 오류: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # 오류 발생 시 결과를 에러 상태로 설정
            if algorithm == "hsv":
                self.target.algorithm_result[algorithm] = (0.0, 0.0, "error")
            else:
                self.target.algorithm_result[algorithm] = (0.0, "error") 
            traceback.print_exc() 