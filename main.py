import sys
from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow  # ui 폴더 내의 main_window.py에서 MainWindow 클래스를 불러옴

def main():
    app = QApplication(sys.argv)
    window = MainWindow()  # 메인 윈도우 인스턴스 생성
    window.show()         # 메인 윈도우 표시
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
