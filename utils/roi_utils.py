from PyQt5.QtWidgets import QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QImage, QPixmap, QCursor
import json
import cv2
import numpy as np
from utils.json_utils import serialize_json_safely, parse_json_safely
from models.target import InspectionTarget
from PIL import Image, ImageDraw, ImageFont
import logging
from config.app_settings import FONT_PATHS, FONT_SIZES
import os
import platform

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("debug.log"),
        logging.StreamHandler()
    ]
)

# ROI 시스템 로거
logger = logging.getLogger("ROISystem")

def save_roi_settings(dialog, target_manager, product_id, db_manager):
    """ROI 설정을 저장하는 공통 유틸리티 함수"""
    
    try:
        if not target_manager.target_list:
            QMessageBox.warning(dialog, "경고", "저장할 ROI가 없습니다.")
            return False
        
        print("\n=== ROI 설정 저장 시작 ===")
        
        settings = {
            'roi_list': [],
            'roi_algorithms': {}
        }
        
        for target_id, target in target_manager.target_list.items():
            # 색상 정보 직렬화 - None 체크 추가
            color = None
            if hasattr(target, 'color') and target.color is not None:
                try:
                    print(f"ROI '{target.name}'의 색상: {target.color}, 타입: {type(target.color)}")
                    color = target.color.tolist()
                    print(f"변환 후 색상: {color}, 타입: {type(color)}")
                except Exception as e:
                    print(f"색상 변환 실패: {target.name}, 원인: {e}")
            else:
                print(f"ROI '{target.name}'의 색상이 None입니다.")
            
            # 모든 ROI 데이터를 표준화된 형식으로 저장
            roi_data = {
                'name': target.name,
                'x': target.x,
                'y': target.y,
                'w': target.w,
                'h': target.h,
                'algorithms': target.matching_algorithm,
                'color': color  # 모든 color는 최상위 레벨에 저장
            }
            settings['roi_list'].append(roi_data)
            settings['roi_algorithms'][target.name] = {
                'algorithms': target.matching_algorithm
            }
        
        print(f"저장할 설정: {settings}")
        
        settings_json = serialize_json_safely(settings)
        success = db_manager.update_product_roi_settings(product_id, settings_json)
        if success:
            print(f"ROI 설정 저장 성공 - {len(settings['roi_list'])}개")
        else:
            print("ROI 설정 저장 실패")
        
        return success
            
    except Exception as e:
        print(f"ROI 설정 저장 중 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def load_roi_settings(dialog, product_id, db_manager, target_manager, frame=None, update_ui_callback=None):
    """제품의 ROI 설정을 DB에서 로드하는 공통 유틸리티 함수
    
    Args:
        dialog: 상위 다이얼로그 인스턴스
        product_id: 제품 ID
        db_manager: DB 관리자 인스턴스
        target_manager: 타겟 관리자 인스턴스
        frame: 참조 이미지 프레임 (옵션)
        update_ui_callback: UI 업데이트를 위한 콜백 함수
    
    Returns:
        bool: 성공 여부
    """
    if not product_id or not db_manager:
        QMessageBox.warning(dialog, "경고", "제품이 선택되지 않았습니다.")
        return False
    
    try:
        product = db_manager.get_product_by_id(product_id)
        
        if product and 'roi_settings' in product and product['roi_settings']:
            # json.loads 대신 parse_json_safely 사용
            settings = parse_json_safely(product['roi_settings'], {})
            
            # 기존 ROI 목록 초기화
            target_manager.clear()
            logger.info(f"ROI 목록 초기화 완료 (제품 ID: {product_id})")
            
            # 저장된 ROI 설정 불러오기
            if settings and 'roi_list' in settings:
                for roi_data in settings['roi_list']:
                    # 최소한의 필요 정보 확인
                    if not all(k in roi_data for k in ['name', 'x', 'y', 'w', 'h']):
                        logger.warning(f"경고: 불완전한 ROI 데이터 - {roi_data}")
                        continue
                    
                    # 알고리즘 목록 확인 (기본값: ["hsv"])
                    algorithms = roi_data.get('algorithms', ["hsv"])
                    
                    # 색상 정보 처리
                    color = None
                    if 'color' in roi_data and roi_data['color'] is not None:
                        try:
                            color = np.array(roi_data['color'], dtype=np.uint8)
                        except (TypeError, ValueError) as e:
                            logger.warning(f"경고: {roi_data['name']}의 색상 값이 유효하지 않습니다 - {e}")
                    
                    # 타겟 직접 생성 (빈 이미지 사용)
                    if frame is None:
                        # 빈 이미지 생성
                        empty_image = np.zeros((roi_data['h'], roi_data['w'], 3), dtype=np.uint8)
                        reference_image = empty_image
                    else:
                        # 프레임에서 ROI 영역 추출
                        x, y, w, h = roi_data['x'], roi_data['y'], roi_data['w'], roi_data['h']
                        # 경계 체크
                        if x >= 0 and y >= 0 and x+w <= frame.shape[1] and y+h <= frame.shape[0]:
                            reference_image = frame[y:y+h, x:x+w].copy()
                        else:
                            logger.warning(f"경고: ROI {roi_data['name']}가 프레임 범위를 벗어납니다")
                            empty_image = np.zeros((roi_data['h'], roi_data['w'], 3), dtype=np.uint8)
                            reference_image = empty_image
                    
                    # 타겟 생성 및 속성 설정
                    target_id = target_manager.add_target(
                        name=roi_data['name'],
                        x=roi_data['x'],
                        y=roi_data['y'],
                        w=roi_data['w'],
                        h=roi_data['h'],
                        image=reference_image,
                        algorithms=algorithms
                    )
                    
                    # 타겟 가져오기
                    target = target_manager.get_target(target_id)
                    if target and color is not None:
                        target.color = color
                
                logger.info(f"총 {len(target_manager.target_list)}개의 ROI를 로드했습니다")
                
                # UI 업데이트 콜백 실행
                if update_ui_callback:
                    update_ui_callback()
                
                return True
            else:
                logger.info("유효한 ROI 설정이 없습니다")
                QMessageBox.information(dialog, "알림", "유효한 ROI 설정이 없습니다.")
        else:
            logger.info("저장된 ROI 설정이 없습니다")
            QMessageBox.information(dialog, "알림", "저장된 ROI 설정이 없습니다.")
    
    except Exception as e:
        logger.error(f"ROI 설정 로드 중 오류: {e}")
        import traceback
        traceback.print_exc()
        QMessageBox.warning(dialog, "오류", f"ROI 설정 로드 중 오류가 발생했습니다: {str(e)}")
    
    return False

class ROISelectDialog(QDialog):
    """이미지에서 드래그로 ROI를 선택하는 다이얼로그"""
    
    roi_selected = pyqtSignal(int, int, int, int)  # x, y, width, height
    
    def __init__(self, image, parent=None):
        super().__init__(parent)
        self.image = image
        self.image_copy = image.copy()
        self.drawing = False
        self.ix, self.iy = -1, -1
        self.selected_roi = None
        
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle("ROI 선택")
        self.setMinimumSize(800, 600)
        
        layout = QVBoxLayout()
        
        # 안내 레이블
        label = QLabel("마우스로 드래그하여 ROI 영역을 선택하세요.")
        layout.addWidget(label)
        
        # 이미지 표시 레이블
        self.image_label = QLabel()
        self.update_image(self.image)
        layout.addWidget(self.image_label)
        
        # 버튼 레이아웃
        btn_layout = QHBoxLayout()
        
        self.reset_btn = QPushButton("초기화")
        self.reset_btn.clicked.connect(self.reset_selection)
        btn_layout.addWidget(self.reset_btn)
        
        self.confirm_btn = QPushButton("선택 완료")
        self.confirm_btn.clicked.connect(self.confirm_selection)
        self.confirm_btn.setEnabled(False)
        btn_layout.addWidget(self.confirm_btn)
        
        self.cancel_btn = QPushButton("취소")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(btn_layout)
        self.setLayout(layout)
        
        # 마우스 이벤트 설정
        self.image_label.setMouseTracking(True)
        self.image_label.mousePressEvent = self.mousePressEvent
        self.image_label.mouseMoveEvent = self.mouseMoveEvent
        self.image_label.mouseReleaseEvent = self.mouseReleaseEvent
    
    def update_image(self, image):
        """이미지 업데이트"""
        height, width, channel = image.shape
        bytesPerLine = 3 * width
        qImg = QImage(image.data, width, height, bytesPerLine, QImage.Format_RGB888).rgbSwapped()
        self.image_label.setPixmap(QPixmap.fromImage(qImg))
    
    def mousePressEvent(self, event):
        """마우스 누르기 이벤트"""
        if event.button() == Qt.LeftButton:
            self.drawing = True
            self.ix, self.iy = event.x(), event.y()
            self.image_copy = self.image.copy()
    
    def mouseMoveEvent(self, event):
        """마우스 이동 이벤트"""
        if self.drawing:
            image_copy = self.image.copy()
            cv2.rectangle(image_copy, (self.ix, self.iy), (event.x(), event.y()), (0, 255, 0), 2)
            self.update_image(image_copy)
    
    def mouseReleaseEvent(self, event):
        """마우스 떼기 이벤트"""
        if event.button() == Qt.LeftButton and self.drawing:
            self.drawing = False
            ex, ey = event.x(), event.y()
            
            # 최소 크기 확인 (10x10 픽셀)
            if abs(ex - self.ix) < 10 or abs(ey - self.iy) < 10:
                return
            
            # 최종 이미지에 ROI 표시
            image_copy = self.image.copy()
            cv2.rectangle(image_copy, (self.ix, self.iy), (ex, ey), (0, 255, 0), 2)
            self.update_image(image_copy)
            
            # ROI 좌표 및 크기 계산
            x0, y0 = min(self.ix, ex), min(self.iy, ey)
            width = abs(ex - self.ix)
            height = abs(ey - self.iy)
            
            self.selected_roi = (x0, y0, width, height)
            logger.info(f"선택한 ROI: x={x0}, y={y0}, width={width}, height={height}")
            
            # 선택 버튼 활성화
            self.confirm_btn.setEnabled(True)
    
    def reset_selection(self):
        """선택 초기화"""
        self.update_image(self.image)
        self.selected_roi = None
        self.confirm_btn.setEnabled(False)
    
    def confirm_selection(self):
        """선택 완료"""
        if self.selected_roi:
            x, y, w, h = self.selected_roi
            self.roi_selected.emit(x, y, w, h)
            self.accept()

def select_roi_from_image(frame, parent_dialog=None):
    """이미지에서 ROI 영역 선택
    
    Args:
        frame: 이미지 프레임
        parent_dialog: 부모 다이얼로그 인스턴스
    
    Returns:
        tuple: (x, y, w, h) 형태의 ROI 좌표 또는 None (취소 시)
    """
    if frame is None:
        if parent_dialog:
            QMessageBox.warning(parent_dialog, "경고", "이미지가 없습니다.")
        return None
    
    # 이미지 복사본 생성
    temp_frame = frame.copy()
    window_name = "ROI 선택 (드래그하여 영역 지정)"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.imshow(window_name, temp_frame)
    
    # cv2.selectROI 사용
    roi = cv2.selectROI(window_name, temp_frame, False)
    cv2.destroyWindow(window_name)
    
    # 선택 취소 처리
    if roi[2] == 0 or roi[3] == 0:
        if parent_dialog:
            QMessageBox.information(parent_dialog, "알림", "ROI 선택이 취소되었습니다.")
        return None
    
    x, y, w, h = roi
    return (int(x), int(y), int(w), int(h))

def create_roi_from_selection(target_manager, frame, roi_name, x, y, w, h, algorithms=None):
    """선택한 영역으로 새 ROI 생성 및 등록
    
    Args:
        target_manager: 타겟 매니저 인스턴스
        frame: ROI 추출에 사용할 이미지 프레임
        roi_name: ROI 이름
        x, y, w, h: ROI 위치 및 크기
        algorithms: 적용할 알고리즘 목록 (기본값: ["hsv"])
    
    Returns:
        int: 생성된 ROI의 ID 또는 None (실패 시)
    """
    if algorithms is None:
        algorithms = ["hsv"]
    
    try:
        # ROI 이미지 추출
        roi_image = frame[y:y+h, x:x+w].copy() if frame is not None else None
        
        # target_manager에 ROI 추가
        target_id = target_manager.add_target(
            name=roi_name,
            x=x,
            y=y,
            w=w,
            h=h,
            image=frame,
            algorithms=algorithms
        )
        
        logger.info(f"ROI 생성 완료: {roi_name} (ID: {target_id})")
        return target_id
        
    except Exception as e:
        logger.error(f"ROI 생성 오류: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def extract_roi_image(frame, x, y, w, h):
    """프레임에서 ROI 영역 추출
    
    Args:
        frame: 원본 이미지 프레임
        x, y, w, h: ROI 좌표 및 크기
    
    Returns:
        numpy.ndarray: 추출된 ROI 이미지 또는 None (실패 시)
    """
    if frame is None:
        return None
    
    try:
        # 좌표 유효성 검사
        h_frame, w_frame = frame.shape[:2]
        
        # 범위를 벗어나는 경우 조정
        if x < 0 or y < 0 or x + w > w_frame or y + h > h_frame:
            # 안전하게 좌표 조정
            x = max(0, x)
            y = max(0, y) 
            w = min(w, w_frame - x)
            h = min(h, h_frame - y)
            logger.warning(f"경고: ROI 좌표가 이미지 범위를 벗어나 조정되었습니다. (x={x}, y={y}, w={w}, h={h})")
        
        # 영역 추출
        roi_image = frame[y:y+h, x:x+w].copy()
        return roi_image
    
    except Exception as e:
        logger.error(f"ROI 이미지 추출 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return None

def visualize_rois(frame, target_manager, selected_id=None, scale_factor=1.0):
    """프레임에 ROI 시각화
    
    Args:
        frame: 원본 이미지 프레임
        target_manager: 타겟 관리자 인스턴스
        selected_id: 현재 선택된 ROI ID (하이라이트 표시)
        scale_factor: 화면 표시 배율 (기본값: 1.0)
    
    Returns:
        numpy.ndarray: ROI가 시각화된 이미지
    """
    if frame is None or target_manager is None:
        return frame
    
    # 원본 이미지 복사
    display_frame = frame.copy()
    
    # 모든 ROI 그리기
    for target_id, target in target_manager.target_list.items():
        try:
            # 강조 여부에 따른 색상 설정
            if target_id == selected_id:
                color = (0, 0, 255)  # 선택된 항목: 빨간색
                thickness = 2
            else:
                color = (0, 255, 0)  # 일반 항목: 초록색
                thickness = 1
            
            # 스케일 적용
            x = int(target.x * scale_factor)
            y = int(target.y * scale_factor)
            w = int(target.w * scale_factor)
            h = int(target.h * scale_factor)
            
            # 디버그 정보 출력
            if target_id == selected_id:
                logger.info(f"선택된 ROI 표시: id={target_id}, 원본좌표=({target.x}, {target.y}), 변환좌표=({x}, {y})")
            
            # 사각형 그리기
            cv2.rectangle(
                display_frame,
                (x, y),
                (x + w, y + h),
                color,
                thickness
            )
            
            # 한글 이름 표시 
            display_frame = draw_text_with_korean(
                display_frame,
                target.name,
                (x, y - 20),  # 텍스트 위치 약간 위로 조정
                color,
                font_size=20
            )
        except Exception as e:
            logger.error(f"ROI {target_id} 시각화 중 오류: {e}")
    
    return display_frame

def set_roi_color(target, roi_image=None, auto_detect=True):
    """ROI 색상 설정 (자동 또는 수동)
    
    Args:
        target: 대상 ROI
        roi_image: ROI 이미지 (자동 감지 시 필요)
        auto_detect: 자동 색상 감지 여부
    
    Returns:
        np.ndarray: 설정된 색상
    """
    if not hasattr(target, 'color') or target.color is None:
        if auto_detect and roi_image is not None:
            # 중심 색상 이용하여 기본값 설정
            try:
                h, w = roi_image.shape[:2]
                center_color = roi_image[h//2, w//2]
                hsv_color = cv2.cvtColor(np.uint8([[center_color]]), cv2.COLOR_BGR2HSV)[0][0]
                target.color = hsv_color
                logger.info(f"[INFO] ROI {target.name}에 기본 색상 설정: {hsv_color}")
            except Exception as e:
                logger.warning(f"색상 자동 감지 실패: {e}")
                # 기본 색상 설정 (중간 회색의 HSV)
                target.color = np.array([0, 0, 128], dtype=np.uint8)
        else:
            # 기본 색상 설정 (중간 회색의 HSV)
            target.color = np.array([0, 0, 128], dtype=np.uint8)
    
    return target.color 

def draw_text_with_korean(image, text, position, color, font_size=20):
    """한글을 포함한 텍스트를 이미지에 그리는 유틸리티 함수
    
    Args:
        image: 원본 이미지 (BGR 형식)
        text: 표시할 텍스트
        position: 텍스트 위치 (x, y)
        color: 텍스트 색상 (BGR 형식)
        font_size: 폰트 크기
        
    Returns:
        numpy.ndarray: 텍스트가 추가된 이미지
    """
    try:
        # BGR에서 RGB로 변환
        rgb_img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb_img)
        draw = ImageDraw.Draw(pil_img)
        
        # 폰트 로드 - 시스템에 따른 경로 설정
        try:
            # 시스템별 폰트 경로 설정
            font_paths = []
            
            if platform.system() == 'Windows':
                font_paths = [
                    "malgun.ttf",
                    os.path.join(os.environ.get('SystemRoot', 'C:/Windows'), 'Fonts/malgun.ttf'),
                    os.path.join(os.environ.get('SystemRoot', 'C:/Windows'), 'Fonts/gulim.ttc')
                ]
            elif platform.system() == 'Linux':
                font_paths = [
                    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
                    "/usr/share/fonts/truetype/korean/UnGraphic.ttf"
                ]
            elif platform.system() == 'Darwin':  # macOS
                font_paths = [
                    "/Library/Fonts/AppleGothic.ttf",
                    "/System/Library/Fonts/AppleGothic.ttf"
                ]
            else:
                font_paths = ["malgun.ttf"]
                
            # 사용 가능한 첫 번째 폰트 찾기
            font = None
            for path in font_paths:
                try:
                    if os.path.exists(path):
                        font = ImageFont.truetype(path, font_size)
                        break
                except:
                    continue
                    
            if font is None:
                logger.warning("경고: 한글 폰트를 찾을 수 없어 기본 폰트를 사용합니다.")
                font = ImageFont.load_default()
                
        except Exception as e:
            logger.error(f"폰트 로드 중 오류: {e}")
            font = ImageFont.load_default()
        
        # BGR -> RGB 색상 변환
        rgb_color = (color[2], color[1], color[0]) if isinstance(color, tuple) and len(color) == 3 else color
        
        # 텍스트 그리기
        draw.text(position, text, font=font, fill=rgb_color)
        
        # RGB에서 BGR로 변환하여 반환
        return cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    except Exception as e:
        logger.error(f"텍스트 렌더링 중 오류: {e}")
        import traceback
        traceback.print_exc()
        return image  # 오류 발생 시 원본 이미지 반환

def calculate_scaling_factors(frame, widget_size, maintain_aspect_ratio=True):
    """이미지와 위젯 크기에 따른 스케일링 인자 계산
    
    Args:
        frame: 원본 이미지
        widget_size: 표시될 위젯 크기 (width, height)
        maintain_aspect_ratio: 종횡비 유지 여부
        
    Returns:
        tuple: (scale_x, scale_y, offset_x, offset_y, new_width, new_height)
    """
    if frame is None:
        return 1.0, 1.0, 0, 0, 0, 0
    
    img_h, img_w = frame.shape[:2]
    widget_w, widget_h = widget_size
    
    if maintain_aspect_ratio:
        img_ratio = img_w / img_h
        widget_ratio = widget_w / widget_h
        
        if img_ratio > widget_ratio:
            new_w = widget_w
            new_h = int(widget_w / img_ratio)
            scale_x = widget_w / img_w
            scale_y = scale_x  # 동일한 스케일 인자
            offset_x = 0
            offset_y = (widget_h - new_h) // 2
        else:
            new_h = widget_h
            new_w = int(widget_h * img_ratio)
            scale_y = widget_h / img_h
            scale_x = scale_y  # 동일한 스케일 인자
            offset_x = (widget_w - new_w) // 2
            offset_y = 0
    else:
        scale_x = widget_w / img_w
        scale_y = widget_h / img_h
        new_w = widget_w
        new_h = widget_h
        offset_x = 0
        offset_y = 0
    
    return scale_x, scale_y, offset_x, offset_y, new_w, new_h 

def screen_to_image_coords(screen_pos, scale_factor, offset_x, offset_y):
    """화면 좌표를 이미지 좌표로 변환
    
    Args:
        screen_pos: 화면 좌표 (x, y)
        scale_factor: 스케일링 인자
        offset_x, offset_y: 이미지 오프셋
        
    Returns:
        tuple: (img_x, img_y) - 이미지 좌표 또는 None (범위 밖일 경우)
    """
    screen_x, screen_y = screen_pos
    
    # 오프셋 제거 후 스케일링 역산
    img_x = (screen_x - offset_x) / scale_factor
    img_y = (screen_y - offset_y) / scale_factor
    
    return int(img_x), int(img_y)

def image_to_screen_coords(img_pos, scale_factor, offset_x, offset_y):
    """이미지 좌표를 화면 좌표로 변환
    
    Args:
        img_pos: 이미지 좌표 (x, y)
        scale_factor: 스케일링 인자
        offset_x, offset_y: 이미지 오프셋
        
    Returns:
        tuple: (screen_x, screen_y) - 화면 좌표
    """
    img_x, img_y = img_pos
    
    # 스케일링 적용 및 오프셋 추가
    screen_x = int(img_x * scale_factor) + offset_x
    screen_y = int(img_y * scale_factor) + offset_y
    
    return screen_x, screen_y

# 사용 가능한 첫 번째 폰트 로드
def load_korean_font(size=FONT_SIZES['normal']):
    """시스템에서 사용 가능한 한글 폰트 로드
    
    Args:
        size: 폰트 크기
        
    Returns:
        PIL.ImageFont: 로드된 폰트 또는 기본 폰트
    """
    for font_path in FONT_PATHS:
        try:
            if os.path.exists(font_path):
                return ImageFont.truetype(font_path, size)
        except:
            continue
    
    # 모든 경로에서 폰트를 찾지 못한 경우
    logger.warning("경고: 한글 폰트를 찾을 수 없어 기본 폰트를 사용합니다.")
    return ImageFont.load_default() 

def calculate_scaling_parameters(frame_size, display_size, padding_top=0):
    """원본 이미지 크기와 화면 크기에 따른 스케일링 매개변수 계산
    
    Args:
        frame_size: 원본 이미지 크기 (width, height)
        display_size: 화면 표시 크기 (width, height)
        padding_top: 상단 패딩 (예: 컨트롤 패널 높이)
        
    Returns:
        tuple: (scale_factor, offset_x, offset_y, new_width, new_height)
    """
    frame_w, frame_h = frame_size
    disp_w, disp_h = display_size
    
    # 패딩 적용
    disp_h = disp_h - padding_top
    
    # 종횡비 계산
    frame_ratio = frame_w / frame_h
    disp_ratio = disp_w / disp_h
    
    if frame_ratio > disp_ratio:
        # 이미지가 더 넓은 경우
        new_w = disp_w
        new_h = int(disp_w / frame_ratio)
        scale_factor = disp_w / frame_w
        offset_x = 0
        offset_y = padding_top + (disp_h - new_h) // 2
    else:
        # 이미지가 더 높은 경우
        new_h = disp_h
        new_w = int(disp_h * frame_ratio)
        scale_factor = disp_h / frame_h
        offset_x = (disp_w - new_w) // 2
        offset_y = padding_top
    
    return scale_factor, offset_x, offset_y, new_w, new_h 