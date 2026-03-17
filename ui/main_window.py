from PyQt5.QtWidgets import (QMainWindow, QAction, QWidget, QVBoxLayout, 
                           QToolBar, QStatusBar, QFileDialog, QMessageBox,
                           QDialog, QSplitter, QLabel, QLineEdit, QPushButton, QDesktopWidget)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt
import os
import json
from functools import partial
import numpy as np
from PyQt5.QtWidgets import QApplication

from ui.dialog.roi_register_dialog import ROIRegisterDialog
from ui.dialog.roi_setting_dialog import ROISettingDialog
from ui.dialog.db_setting_dialog import DBSettingDialog
from ui.dialog.equipment_register_dialog import EquipmentRegisterDialog
from ui.dialog.product_register_dialog import ProductRegisterDialog
from ui.dialog.color_picker_dialog import ColorPickerDialog
from ui.left_layout import LeftLayout
from ui.center_layout import CenterLayout

from manager.camera_manager import CameraManager
from manager.target_manager import InspectionTargetListManager
from manager.db_manager import DBManager
from utils.roi_utils import save_roi_settings
from utils.json_utils import parse_json_safely


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setStatusBar(QStatusBar(self))

        # 매니저 초기화
        self.camera_manager = CameraManager()
        self.target_manager = InspectionTargetListManager()
        
        # DB 매니저 초기화 및 시그널 연결
        self.db_manager = DBManager()
        self.db_manager.db_error.connect(self.show_db_error)
        self.db_manager.db_changed.connect(self.on_db_changed)
        self.db_manager.roi_settings_updated.connect(self.on_roi_settings_updated)
        
        # UI 초기화
        self.initUI()
        
        # 카메라 초기화 및 시작
        self.camera_manager.initialize()
        # 스트리밍은 LeftLayout으로만 전달
        self.camera_manager.frame_updated.connect(self.left_widget.displayImage)
        self.camera_manager.start() 

        # 검사 결과 시그널 연결 (right_widget 제거)
        self.left_widget.inspection_completed.connect(self.center_widget.update_inspection_results)

        self.current_product = None  # 현재 선택된 제품 정보 저장 변수 추가
        self.active_dialogs = []  # 활성 다이얼로그 추적

    def initUI(self):
        """UI 초기화"""
        self.setWindowTitle('검사 프로그램')
        
        # 화면 크기 및 위치 설정 방식 변경
        desktop = QDesktopWidget()
        screen_number = desktop.screenNumber(self)
        available_geometry = desktop.availableGeometry(screen_number)
        
        # 화면 크기에 맞게 윈도우 크기 조정 (화면의 85%)
        window_width = int(available_geometry.width() * 0.85)
        window_height = int(available_geometry.height() * 0.85)
        
        # 메뉴바/툴바/상태바 고려한 높이 조정 (메뉴+툴바 약 80px 가정)
        estimated_chrome_height = 80  # 메뉴바+툴바+상태바 예상 높이
        window_height = min(window_height, available_geometry.height() - estimated_chrome_height)
        
        # 화면 중앙에 위치시키기
        x = (available_geometry.width() - window_width) // 2 + available_geometry.left()
        y = (available_geometry.height() - window_height) // 2 + available_geometry.top()
        
        # 위치와 크기 설정
        self.setGeometry(x, y, window_width, window_height)
        
        # 메인 레이아웃 설정
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # QSplitter 생성
        splitter = QSplitter(Qt.Horizontal)
        
        # 좌측 레이아웃
        self.left_widget = LeftLayout(target_manager=self.target_manager)
        splitter.addWidget(self.left_widget)
        
        # 중앙 레이아웃
        self.center_widget = CenterLayout(
            parent=self,
            target_manager=self.target_manager,
            camera_manager=self.camera_manager
        )
        splitter.addWidget(self.center_widget)
        
        # 좌측:중앙 비율 설정 (1:4)
        splitter.setSizes([int(window_width * 0.2), int(window_width * 0.8)])
        
        main_layout.addWidget(splitter)

        # 메뉴바 생성
        self.createMenuBar()
        
        # 툴바 생성
        self.createToolBar()

    def createToolBar(self):
        """툴바 생성"""
        # 메뉴바 아래에 정보 표시용 툴바 생성 (버튼 대신 등록 정보 표시)
        toolbar = self.addToolBar("등록 정보")
        toolbar.setMovable(False)
        toolbar.setStyleSheet("""
            QToolBar {
                spacing: 15px;       /* 간격 축소 */
                padding: 3px;        /* 패딩 축소 */
                height: 40px;        /* 높이 감소 */
            }
            QLabel {
                font-size: 14px;     /* 폰트 크기 감소 */
                margin-left: 10px;   /* 여백 감소 */
            }
            QLineEdit {
                font-size: 14px;     /* 폰트 크기 감소 */
                padding: 3px;        /* 패딩 감소 */
                height: 25px;        /* 높이 감소 */
            }
        """)
        
        # 장비 ID 레이블과 QLineEdit
        toolbar.addWidget(QLabel("장비 ID :"))
        self.device_id_edit = QLineEdit()
        self.device_id_edit.setReadOnly(True)
        self.device_id_edit.setPlaceholderText("장비 ID")
        self.device_id_edit.setStyleSheet("background-color: white;")
        self.device_id_edit.setFixedWidth(200)  # 너비 더 증가
        toolbar.addWidget(self.device_id_edit)
        
        # 장비 이름 레이블과 QLineEdit
        toolbar.addWidget(QLabel("장비 이름 :"))
        self.device_name_edit = QLineEdit()
        self.device_name_edit.setReadOnly(True)
        self.device_name_edit.setPlaceholderText("장비 이름")
        self.device_name_edit.setStyleSheet("background-color: white;")
        self.device_name_edit.setFixedWidth(250)  # 너비 더 증가
        toolbar.addWidget(self.device_name_edit)
        
        toolbar.addSeparator()
        
        # 제품 ID 레이블과 QLineEdit
        toolbar.addWidget(QLabel("제품 ID :"))
        self.product_id_edit = QLineEdit()
        self.product_id_edit.setReadOnly(True)
        self.product_id_edit.setPlaceholderText("제품 ID")
        self.product_id_edit.setStyleSheet("background-color: white;")
        self.product_id_edit.setFixedWidth(200)  # 너비 더 증가
        toolbar.addWidget(self.product_id_edit)
        
        # 제품 이름 레이블과 QLineEdit
        toolbar.addWidget(QLabel("제품 이름 :"))
        self.product_name_edit = QLineEdit()
        self.product_name_edit.setReadOnly(True)
        self.product_name_edit.setPlaceholderText("제품 이름")
        self.product_name_edit.setStyleSheet("background-color: white;")
        self.product_name_edit.setFixedWidth(250)  # 너비 더 증가
        toolbar.addWidget(self.product_name_edit)
        
        # 제품 이름 입력란 다음에 새로고침 버튼 추가
        refresh_button = QPushButton("새로고침")
        refresh_button.setFixedSize(120, 30)  # 버튼 크기 증가
        refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #4a90e2;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
                font-size: 16px;  /* 폰트 크기 증가 */
            }
            QPushButton:hover {
                background-color: #357abd;
            }
        """)
        refresh_button.clicked.connect(self.refresh_roi_settings)
        toolbar.addWidget(refresh_button)
        
        # 장비 ID와 이름 초기값 설정
        self.device_id_edit.setText('EQ001')
        self.device_name_edit.setText('PCB 검사기 1호기')
        
        # 제품 ID와 이름 초기값 설정
        self.product_id_edit.setText('PCB001')
        self.product_name_edit.setText('PCB 기판')

    def createMenuBar(self):
        """메뉴바 생성"""
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                font-size: 16px;
                padding: 5px;
                background-color: #f0f0f0;
            }
            QMenuBar::item {
                padding: 5px 10px;
                margin: 2px;
            }
            QMenuBar::item:selected {
                background-color: #e0e0e0;
                border-radius: 3px;
            }
            QMenu {
                font-size: 15px;
                padding: 5px;
            }
            QMenu::item {
                padding: 5px 20px;
            }
            QMenu::item:selected {
                background-color: #e0e0e0;
            }
        """)

        # 상세 설정 메뉴
        detailMenu = menubar.addMenu('상세 설정')
        
        # ROI 등록 액션
        roiRegAction = QAction('ROI 등록', self)
        roiRegAction.setStatusTip('새로운 ROI 영역 등록')
        roiRegAction.triggered.connect(self.registerROI)
        
        # ROI 설정 액션
        roiSetAction = QAction('ROI 설정', self)
        roiSetAction.setStatusTip('ROI 파라미터 설정')
        roiSetAction.triggered.connect(self.settingROI)
        
        # 색상 설정 액션 추가
        colorSetAction = QAction('색상 설정', self)
        colorSetAction.setStatusTip('ROI 검사 색상 설정')
        colorSetAction.triggered.connect(self.settingColor)
                
        # 알고리즘 설정 액션
        algorithm_settings_action = QAction('파라미터 설정', self)
        algorithm_settings_action.setStatusTip('알고리즘 파라미터 설정')
        algorithm_settings_action.triggered.connect(self.open_algorithm_settings)

        # ROI 서브메뉴 생성
        roiSubMenu = detailMenu.addMenu('ROI 관리')
        roiSubMenu.addAction(roiRegAction)
        roiSubMenu.addAction(roiSetAction)
        roiSubMenu.addAction(colorSetAction)  # 색상 설정 메뉴 추가
        roiSubMenu.addAction(algorithm_settings_action)

        
        # DB 설정 메뉴
        dbMenu = menubar.addMenu('DB 설정')
        
        # DB 연결 설정
        dbConnectAction = QAction('DB 연결 설정', self)
        dbConnectAction.setStatusTip('데이터베이스 연결 설정')
        dbConnectAction.triggered.connect(self.settingDBConnection)
        dbMenu.addAction(dbConnectAction)
        
        # 장비 등록 메뉴
        equipMenu = menubar.addMenu('장비 등록')
        
        # 새 장비 등록
        newEquipAction = QAction('새 장비 등록', self)
        newEquipAction.setStatusTip('새로운 장비 등록')
        newEquipAction.triggered.connect(self.registerNewEquipment)
        equipMenu.addAction(newEquipAction)
        
        # 제품 등록 메뉴
        productMenu = menubar.addMenu('제품 등록')
        
        # 새 제품 등록
        newProductAction = QAction('새 제품 등록', self)
        newProductAction.setStatusTip('새로운 제품 등록')
        newProductAction.triggered.connect(self.registerNewProduct)
        productMenu.addAction(newProductAction)
        
        # 대시보드 메뉴 추가
        dashboardMenu = menubar.addMenu('대시보드')
        
        # 생산 분석 대시보드
        dashboardAction = QAction('생산 분석 대시보드', self)
        dashboardAction.setStatusTip('생산 및 검사 결과 통계 대시보드')
        dashboardAction.triggered.connect(self.showAnalyticsDashboard)
        dashboardMenu.addAction(dashboardAction)

        

    def cleanup_dialog(self, dialog):
        """다이얼로그 정리"""
        try:
            if dialog in self.active_dialogs:
                self.active_dialogs.remove(dialog)
                if hasattr(dialog, 'cleanup'):
                    dialog.cleanup()
        except Exception as e:
            print(f"다이얼로그 정리 중 오류: {e}")

    def registerROI(self):
        if not self.current_product:
            QMessageBox.warning(self, "경고", "제품을 먼저 선택해주세요.")
            return
        
        print(f"ROI 등록 - 선택된 제품: {self.current_product}")
        dialog = ROIRegisterDialog(
            parent=self,
            camera_manager=self.camera_manager,
            target_manager=self.target_manager,
            product_id=self.current_product['product_id'],
            db_manager=self.db_manager
        )
        
        self.active_dialogs.append(dialog)
        dialog.finished.connect(partial(self.cleanup_dialog, dialog))
        dialog.destroyed.connect(partial(self.cleanup_dialog, dialog))
        dialog.exec_()

    def settingROI(self):
        if not self.current_product:
            QMessageBox.warning(self, "경고", "제품을 먼저 선택해주세요.")
            return
            
        print(f"ROI 설정 - 선택된 제품: {self.current_product}")
        dialog = ROISettingDialog(
            parent=self,
            target_manager=self.target_manager,
            product_id=self.current_product['product_id'],
            db_manager=self.db_manager
        )
        
        self.active_dialogs.append(dialog)
        dialog.finished.connect(partial(self.cleanup_dialog, dialog))
        dialog.destroyed.connect(partial(self.cleanup_dialog, dialog))
        dialog.exec_()

    def get_current_product(self):
        """현재 선택된 제품 정보 반환"""
        return self.current_product

    def on_db_changed(self, new_db_path):
        """DB 변경 시 처리"""
        self.left_widget.reload_data()  # 좌측 위젯 데이터 갱신
        self.statusBar().showMessage('DB 설정이 변경되었습니다.', 3000)

    def settingDBConnection(self):
        """DB 연결 설정"""
        dialog = DBSettingDialog(self)
        dialog.exec_()  # accept()에서 자동으로 DB 변경 처리

    def registerNewEquipment(self):
        """새 장비 등록"""
        dialog = EquipmentRegisterDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            # 장비 정보를 툴바와 좌측 레이아웃에 업데이트
            equipment_data = dialog.equipment_data
            # 툴바 업데이트
            self.device_id_edit.setText(equipment_data['equipment_id'])
            self.device_name_edit.setText(equipment_data['equipment_name'])
            # 좌측 레이아웃 업데이트
            self.left_widget.update_equipment_info(equipment_data)
            self.statusBar().showMessage('장비 등록 완료', 3000)

    def registerNewProduct(self):
        """새 제품 등록"""
        # 현재 등록된 장비 ID 가져오기
        current_equipment_id = self.device_id_edit.text()
        
        # 장비가 등록되어 있지 않으면 경고
        if not current_equipment_id:
            QMessageBox.warning(self, "등록 오류", "먼저 장비를 등록해주세요.")
            return
            
        dialog = ProductRegisterDialog(self, equipment_id=current_equipment_id)
        if dialog.exec_() == QDialog.Accepted:
            # 제품 정보를 툴바와 좌측 레이아웃에 업데이트
            product_data = dialog.product_data
            # 툴바 업데이트
            self.product_id_edit.setText(product_data['product_id'])
            self.product_name_edit.setText(product_data['product_name'])
            # 좌측 레이아웃 업데이트
            self.left_widget.update_product_info(product_data)
            # current_product 업데이트 추가
            self.current_product = product_data
            self.statusBar().showMessage('제품 등록 완료', 3000)
        
    def create_equipment_dialog(self):
        """장비 등록 다이얼로그 생성"""
        return EquipmentRegisterDialog(self)
        
    def create_product_dialog(self, equipment_id):
        """제품 등록 다이얼로그 생성"""
        return ProductRegisterDialog(self, equipment_id=equipment_id)

    def show_db_error(self, error_msg):
        """DB 에러 메시지 표시"""
        QMessageBox.critical(self, "DB 오류", error_msg)

    def on_product_double_clicked(self, item):
        """제품 더블클릭 시 처리"""
        try:
            product_id = item.data(Qt.UserRole)  # 또는 해당하는 방식으로 product_id 가져오기
            self.current_product = self.db_manager.get_product_by_id(product_id)
            print(f"선택된 제품: {self.current_product}")
        except Exception as e:
            print(f"제품 선택 중 오류 발생: {str(e)}")

    def on_roi_settings_updated(self, product_id):
        """ROI 설정 업데이트 시 호출되는 메서드"""
        if not self.current_product or self.current_product['product_id'] != product_id:
            return
        
        try:
            updated_product = self.db_manager.get_product_by_id(product_id)
            if not updated_product:
                return
            
            self.current_product = updated_product
            self.left_widget.update_product_info(self.current_product)
            
            # 다이얼로그 갱신
            for dialog in self.active_dialogs[:]:  # 복사본으로 순회
                try:
                    if hasattr(dialog, 'refresh_data'):
                        dialog.refresh_data()
                except Exception as e:
                    print(f"다이얼로그 갱신 중 오류: {e}")
                    self.cleanup_dialog(dialog)
        except Exception as e:
            print(f"ROI 설정 업데이트 중 오류: {e}")

    def on_product_changed(self, new_product):
        try:
            current_frame = self.camera_manager.get_current_frame()
            if current_frame is None:
                print("경고: 현재 프레임을 가져올 수 없습니다")
                return
            
            print("\n=== 제품 변경 시작 ===")
            print(f"제품 ID: {new_product['product_id']}")
            
            self.target_manager.clear()  # ROI 초기화
            
            product = self.db_manager.get_product_by_id(new_product['product_id'])
            if product and 'roi_settings' in product:
                # json.loads 대신 parse_json_safely 사용
                roi_settings = parse_json_safely(product['roi_settings'], {})
                
                if roi_settings and 'roi_list' in roi_settings:
                    for roi in roi_settings['roi_list']:
                        print(f"ROI 추가: {roi['name']}")
                        target_id = self.target_manager.add_target(
                            name=roi['name'],
                            x=roi['x'],
                            y=roi['y'],
                            w=roi['w'],
                            h=roi['h'],
                            image=current_frame,
                            algorithms=roi.get('algorithms', ["hsv"])
                        )
                        
                        if target_id and 'color' in roi and roi['color']:
                            target = self.target_manager.target_list[target_id]
                            target.color = np.array(roi['color'], dtype=np.uint8)
                    
                    print(f"ROI 로드 완료: {len(self.target_manager.target_list)}개")
            
            self.left_widget.update_product_info(new_product)
            print("=== 제품 변경 완료 ===\n")
            
        except Exception as e:
            print(f"제품 변경 중 오류: {str(e)}")

    def refresh_roi_settings(self):
        """ROI 설정 새로고침"""
        if not self.current_product:
            QMessageBox.warning(self, "경고", "선택된 제품이 없습니다.")
            return
        
        try:
            # 현재 제품의 최신 정보 로드
            product = self.db_manager.get_product_by_id(self.current_product['product_id'])
            if product:
                self.on_product_changed(product)
                self.statusBar().showMessage('ROI 설정이 새로고침되었습니다.', 3000)
        except Exception as e:
            print(f"ROI 설정 새로고침 중 오류: {e}")

    def settingColor(self):
        print("\n=== 색상 설정 시작 ===")
        print(f"현재 제품: {self.current_product['product_id'] if self.current_product else 'None'}")
        print(f"ROI 개수: {len(self.target_manager.target_list) if self.target_manager else 0}")
        
        if not self.current_product:
            print("제품이 선택되지 않음")
            QMessageBox.warning(self, "경고", "제품을 먼저 선택해주세요.")
            return
        
        # 먼저 ROI 설정을 다시 로드
        try:
            product = self.db_manager.get_product_by_id(self.current_product['product_id'])
            if product and 'roi_settings' in product:
                self.on_product_changed(product)  # ROI 설정 다시 로드
        except Exception as e:
            print(f"ROI 설정 로드 중 오류: {e}")
        
        # ROI 존재 여부 체크
        if not self.target_manager or len(self.target_manager.target_list) == 0:
            QMessageBox.warning(self, "경고", "등록된 ROI가 없습니다. ROI를 먼저 등록해주세요.")
            return
        
        current_frame = self.camera_manager.get_current_frame()
        if current_frame is None:
            QMessageBox.warning(self, "경고", "카메라 프레임을 가져올 수 없습니다.")
            return
        
        print(f"settingColor - ROI 개수: {len(self.target_manager.target_list)}")
        
        dialog = ColorPickerDialog(
            self,
            current_frame,
            self.target_manager
        )
        
        result = dialog.exec_()
        print(f"다이얼로그 결과: {'수락됨' if result == QDialog.Accepted else '거부됨'}")
        
        # 저장 로직 추가 (결과와 관계없이 저장 시도)
        if True:  # 임시로 항상 저장
            print("ROI 설정을 저장합니다...")
            save_roi_settings(self, self.target_manager, self.current_product['product_id'], self.db_manager)
            
            # 저장 후 ROI 설정을 다시 로드하여 확인
            updated_product = self.db_manager.get_product_by_id(self.current_product['product_id'])
            print(f"\n=== 저장 후 제품 정보 ===")
            print(f"제품 ID: {updated_product['product_id']}")
            print(f"ROI 설정: {updated_product['roi_settings']}")

    def showAnalyticsDashboard(self):
        """생산 분석 대시보드 표시"""
        try:
            # 분석 대시보드 대화상자 임포트 및 실행
            from ui.dialog.dashboard_dialog import DashboardDialog
            dialog = DashboardDialog(self)
            
            # 활성 다이얼로그 목록에 추가
            self.active_dialogs.append(dialog)
            dialog.finished.connect(partial(self.cleanup_dialog, dialog))
            dialog.destroyed.connect(partial(self.cleanup_dialog, dialog))
            
            dialog.exec_()
        except ImportError as e:
            QMessageBox.warning(self, "모듈 오류", f"분석 모듈을 불러올 수 없습니다: {str(e)}")
        except Exception as e:
            QMessageBox.warning(self, "오류", f"분석 대시보드 실행 중 오류가 발생했습니다: {str(e)}")

    def open_algorithm_settings(self):
        """알고리즘 설정 다이얼로그 열기"""
        from ui.dialog.algorithm_setting_dialog import AlgorithmSettingDialog
        dialog = AlgorithmSettingDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            # 타겟 매니저 설정 업데이트
            if hasattr(self.target_manager, 'update_algorithm_parameters'):
                self.target_manager.update_algorithm_parameters()


    