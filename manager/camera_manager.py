from PyQt5.QtCore import QObject, pyqtSignal, QThread
import cv2
import time

class CameraThread(QThread):
    frame_ready = pyqtSignal(object)
    
    def __init__(self, camera):
        super().__init__()
        self._camera = camera
        self._running = True
        
    def run(self):
        while self._running and self._camera and self._camera.isOpened():
            ret, frame = self._camera.read()
            if ret:
                self.frame_ready.emit(frame)
            time.sleep(0.03)  # ~30 FPS로 제한
            
    def stop(self):
        self._running = False
        self.wait()

class CameraManager(QObject):
    frame_updated = pyqtSignal(object)  # 새 프레임 시그널
    
    def __init__(self):
        super().__init__()
        self._camera = None
        self._camera_thread = None
        self._current_frame = None
        self._captured_frame = None  # 캡처된 프레임 저장
    
    def initialize(self, camera_index=0):
        """카메라 초기화"""
        try:
            if self._camera:
                self.stop()
                
            self._camera = cv2.VideoCapture(camera_index)
            if not self._camera.isOpened():
                raise Exception("카메라를 열 수 없습니다.")
                
            # 카메라 설정 최적화
            self._camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # 버퍼 크기 최소화
            return True
            
        except Exception as e:
            print(f"카메라 초기화 실패: {str(e)}")
            return False
    
    def start(self):
        """카메라 스트리밍 시작"""
        if self._camera and not self._camera_thread:
            self._camera_thread = CameraThread(self._camera)
            self._camera_thread.frame_ready.connect(self._handle_frame)
            self._camera_thread.start()
    
    def stop(self):
        """카메라 스트리밍 중지"""
        if self._camera_thread:
            self._camera_thread.stop()
            self._camera_thread = None
            
        if self._camera:
            self._camera.release()
            self._camera = None
            
        self._current_frame = None
    
    def _handle_frame(self, frame):
        """프레임 업데이트 (내부 메서드)"""
        self._current_frame = frame
        self.frame_updated.emit(frame)
    
    def get_current_frame(self):
        """현재 프레임 반환"""
        return self._current_frame
    
    def capture_frame(self):
        """현재 프레임을 캡처하여 저장"""
        if self._current_frame is not None:
            self._captured_frame = self._current_frame.copy()
            return True
        return False
    
    def get_captured_frame(self):
        """캡처된 프레임 반환"""
        return self._captured_frame
    
    def __del__(self):
        self.stop() 