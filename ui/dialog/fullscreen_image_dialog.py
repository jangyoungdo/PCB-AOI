from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QInputDialog, QLineEdit
from PyQt5.QtCore import Qt, QPoint, QRect
from PyQt5.QtGui import QPainter, QPen, QPixmap, QImage, QColor
import cv2

class FullscreenImageDialog(QDialog):
    def __init__(self, parent=None, frame=None, roi_list=None, roi_manager=None):
        super().__init__(parent)
        self.setWindowTitle("이미지 확대")
        self.setWindowState(Qt.WindowFullScreen)
        
        self.frame = frame
        self.roi_list = roi_list if roi_list else []
        self.roi_manager = roi_manager
        self.parent_dialog = parent
        
        self.drawing = False
        self.start_pos = None
        self.current_pos = None
        self.scale_factor = 1.0
        self.image_rect = None
        
        self.init_ui()
        
        # 초기 이미지 표시
        self.update_image()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setMouseTracking(True)
        layout.addWidget(self.image_label)
        
        self.setWindowFlags(Qt.Window)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            if self.image_rect and self.image_rect.contains(event.pos()):
                self.drawing = True
                self.start_pos = self.convert_to_image_coordinates(event.pos())
                self.current_pos = self.start_pos
    
    def mouseMoveEvent(self, event):
        if self.drawing and self.image_rect:
            self.current_pos = self.convert_to_image_coordinates(event.pos())
            self.update_image()
    
    def mouseReleaseEvent(self, event):
        if self.drawing and self.start_pos and self.current_pos:
            self.drawing = False
            if abs(self.current_pos.x() - self.start_pos.x()) > 10 and \
               abs(self.current_pos.y() - self.start_pos.y()) > 10:
                self.create_new_roi()
            self.update_image()
    
    def convert_to_image_coordinates(self, pos):
        if not self.image_rect:
            return pos
        
        relative_x = (pos.x() - self.image_rect.x()) / self.image_rect.width()
        relative_y = (pos.y() - self.image_rect.y()) / self.image_rect.height()
        
        image_x = int(relative_x * self.frame.shape[1])
        image_y = int(relative_y * self.frame.shape[0])
        
        return QPoint(max(0, min(image_x, self.frame.shape[1])),
                     max(0, min(image_y, self.frame.shape[0])))
    
    def create_new_roi(self):
        if self.roi_manager:
            x = min(self.start_pos.x(), self.current_pos.x())
            y = min(self.start_pos.y(), self.current_pos.y())
            w = abs(self.current_pos.x() - self.start_pos.x())
            h = abs(self.current_pos.y() - self.start_pos.y())
            
            # ROI 이름 입력 다이얼로그
            name, ok = QInputDialog.getText(
                self, 
                'ROI 이름 입력', 
                'ROI의 이름을 입력하세요:', 
                QLineEdit.Normal, 
                f"ROI_{len(self.roi_manager.target_list) + 1}"
            )
            
            if ok and name:
                self.roi_manager.add_target(
                    name=name,
                    x=x,
                    y=y,
                    w=w,
                    h=h,
                    image=self.frame,
                    algorithms=[]
                )
                
                self.roi_list = self.roi_manager.target_list.values()
                
                if self.parent_dialog:
                    self.parent_dialog.update_preview()
                    self.parent_dialog.update_table()
    
    def update_image(self):
        """프레임과 ROI를 화면에 표시합니다."""
        if self.frame is not None:
            rgb_frame = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)
            height, width, channels = rgb_frame.shape
            bytes_per_line = channels * width
            image = QImage(rgb_frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(image)
            
            painter = QPainter(pixmap)
            
            # 기존 ROI 그리기
            for roi in self.roi_list:
                pen = QPen(Qt.green, 2)
                painter.setPen(pen)
                painter.drawRect(roi.x, roi.y, roi.w, roi.h)
                painter.setPen(QPen(Qt.white, 1))
                painter.drawText(roi.x + 1, roi.y - 4, roi.name)
                painter.setPen(QPen(Qt.black, 1))
                painter.drawText(roi.x, roi.y - 5, roi.name)
            
            # 드래그 중인 임시 ROI 그리기
            if self.drawing and self.start_pos and self.current_pos:
                pen = QPen(QColor(255, 255, 0), 2)
                pen.setStyle(Qt.DashLine)
                painter.setPen(pen)
                x = min(self.start_pos.x(), self.current_pos.x())
                y = min(self.start_pos.y(), self.current_pos.y())
                w = abs(self.current_pos.x() - self.start_pos.x())
                h = abs(self.current_pos.y() - self.start_pos.y())
                painter.drawRect(x, y, w, h)
            
            painter.end()
            
            scaled_pixmap = pixmap.scaled(
                self.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
            self.image_rect = QRect(
                (self.width() - scaled_pixmap.width()) // 2,
                (self.height() - scaled_pixmap.height()) // 2,
                scaled_pixmap.width(),
                scaled_pixmap.height()
            )
            
            self.image_label.setPixmap(scaled_pixmap)
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()

    def showEvent(self, event):
        super().showEvent(event)
        self.update_image() 