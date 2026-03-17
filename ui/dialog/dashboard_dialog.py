import os
import datetime
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                            QTabWidget, QWidget, QPushButton, QFrame,
                            QComboBox, QDateEdit, QTableWidget, QTableWidgetItem, 
                            QMessageBox, QSplitter, QSizePolicy, QHeaderView)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor
import matplotlib
matplotlib.use('Qt5Agg')  # Qt5 백엔드 사용 명시
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np
from datetime import datetime, timedelta
from manager.db_manager import DBManager
from utils.json_utils import parse_json_safely, extract_roi_data

# 차트 캔버스 클래스
class ChartCanvas(FigureCanvas):
    def __init__(self, parent=None, width=8, height=6, dpi=100):
        """차트 캔버스 초기화"""
        # 그림 객체 생성
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        
        # 여백 설정 - 차트가 잘리지 않도록 여백 늘림
        self.fig.subplots_adjust(bottom=0.15, left=0.1, right=0.9, top=0.85)
        
        # FigureCanvas 초기화
        super().__init__(self.fig)
        self.setParent(parent)
        
        # 크기 정책 설정
        FigureCanvas.setSizePolicy(
            self,
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )
        FigureCanvas.updateGeometry(self)
        
        # 한글 폰트 설정
        self.setup_fonts()
    
    def setup_fonts(self):
        """차트 폰트 설정"""
        try:
            # 이미 전역 설정된 폰트 사용
            self.axes.set_title("차트 제목", fontsize=14)
            self.fig.tight_layout()
        except Exception as e:
            print(f"차트 폰트 설정 오류: {str(e)}")

class DashboardDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db_manager = DBManager()
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle("생산 분석 대시보드")
        self.setMinimumSize(1200, 1300)
        
        # 한글 폰트 설정
        self.setup_korean_font()
        
        main_layout = QVBoxLayout()
        
        # 상단 필터 패널
        filter_panel = QFrame()
        filter_panel.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        filter_panel.setStyleSheet("""
            QFrame {
                background-color: #f5f5f5;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        
        filter_layout = QHBoxLayout()
        
        # 장비 선택
        equipment_label = QLabel("장비:")
        self.equipment_combo = QComboBox()
        self.load_equipment_list()
        self.equipment_combo.currentIndexChanged.connect(self.update_data)
        
        # 제품 선택
        product_label = QLabel("제품:")
        self.product_combo = QComboBox()
        self.load_product_list()
        self.product_combo.currentIndexChanged.connect(self.update_data)
        
        # 날짜 범위 선택
        date_label = QLabel("기간:")
        
        # 시작 날짜 (기본값: 10일 전)
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addDays(-10))
        self.start_date.setCalendarPopup(True)
        self.start_date.dateChanged.connect(self.update_data)
        
        # 종료 날짜 (기본값: 오늘)
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setCalendarPopup(True)
        self.end_date.dateChanged.connect(self.update_data)
        
        # 필터 레이아웃에 위젯 추가
        filter_layout.addWidget(equipment_label)
        filter_layout.addWidget(self.equipment_combo)
        filter_layout.addWidget(product_label)
        filter_layout.addWidget(self.product_combo)
        filter_layout.addWidget(date_label)
        filter_layout.addWidget(self.start_date)
        filter_layout.addWidget(QLabel("~"))
        filter_layout.addWidget(self.end_date)
        filter_layout.addStretch()
        
        filter_panel.setLayout(filter_layout)
        main_layout.addWidget(filter_panel)
        
        # 탭 위젯 생성
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
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
        
        # 탭1: 요약 탭
        self.tab_summary = QWidget()
        self.init_summary_tab()
        self.tabs.addTab(self.tab_summary, "검사 결과 요약")
        
        # 탭2: 장비별 분석 탭
        self.tab_equipment = QWidget()
        self.init_equipment_tab()
        self.tabs.addTab(self.tab_equipment, "장비별 분석")
        
        # 탭3: 제품별 분석 탭
        self.tab_product = QWidget()
        self.init_product_tab()
        self.tabs.addTab(self.tab_product, "제품별 분석")
        
        # 탭4: 일별 추이 탭
        self.tab_daily = QWidget()
        self.init_daily_tab()
        self.tabs.addTab(self.tab_daily, "일별 추이")
        
        # 탭5: ROI별 불량 분석 탭
        self.tab_roi_analysis = QWidget()
        self.init_roi_analysis_tab()
        self.tabs.addTab(self.tab_roi_analysis, "ROI별 불량 분석")
        
        main_layout.addWidget(self.tabs)
        
        # 하단 버튼 패널
        button_panel = QFrame()
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("새로고침")
        refresh_btn.clicked.connect(self.update_data)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #4a90e2;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #357abd;
            }
        """)
        
        close_btn = QPushButton("닫기")
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        
        button_layout.addStretch()
        button_layout.addWidget(refresh_btn)
        button_layout.addWidget(close_btn)
        
        button_panel.setLayout(button_layout)
        main_layout.addWidget(button_panel)
        
        self.setLayout(main_layout)
        
        # 초기 데이터 로드
        self.update_data()
    
    def load_equipment_list(self):
        """장비 목록 로드"""
        try:
            # 기존 항목 초기화
            self.equipment_combo.clear()
            
            # '전체' 항목 추가
            self.equipment_combo.addItem("전체", None)
            
            # 장비 목록 가져오기
            equipment_list = self.db_manager.get_all_equipments()
            
            # 콤보박스에 장비 추가
            for equipment in equipment_list:
                self.equipment_combo.addItem(
                    equipment['equipment_name'],
                    equipment['equipment_id']
                )
        except Exception as e:
            print(f"장비 목록 로드 오류: {str(e)}")
    
    def load_product_list(self):
        """제품 목록 로드"""
        try:
            # 기존 항목 초기화
            self.product_combo.clear()
            
            # '전체' 항목 추가
            self.product_combo.addItem("전체", None)
            
            # 제품 목록 가져오기
            product_list = self.db_manager.get_all_products()
            
            # 콤보박스에 제품 추가
            for product in product_list:
                self.product_combo.addItem(
                    product['product_name'],
                    product['product_id']
                )
        except Exception as e:
            print(f"제품 목록 로드 오류: {str(e)}")
    
    def init_summary_tab(self):
        """요약 탭 초기화"""
        layout = QVBoxLayout()
        
        # 요약 정보 프레임
        summary_frame = QFrame()
        summary_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        summary_frame.setStyleSheet("""
            QFrame {
                background-color: #f5f5f5;
                border-radius: 5px;
                padding: 15px;
            }
        """)
        
        summary_layout = QVBoxLayout()
        
        # 타이틀 레이블
        title_label = QLabel("검사 결과 요약")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #333333;
            }
        """)
        summary_layout.addWidget(title_label)
        
        # 요약 정보 레이블
        info_frame = QFrame()
        info_layout = QHBoxLayout()
        
        # 각 요약 정보 레이블 생성
        self.total_label = QLabel("총 검사 건수: 0")
        self.pass_label = QLabel("양품: 0")
        self.fail_label = QLabel("불량: 0")
        self.rate_label = QLabel("양품률: 0.00%")
        
        for label in [self.total_label, self.pass_label, self.fail_label, self.rate_label]:
            label.setStyleSheet("""
                QLabel {
                    font-size: 14px;
                    padding: 10px;
                    background-color: white;
                    border-radius: 5px;
                    margin: 5px;
                }
            """)
            info_layout.addWidget(label)
        
        info_frame.setLayout(info_layout)
        summary_layout.addWidget(info_frame)
        
        # 파이 차트 캔버스
        self.summary_chart = ChartCanvas(width=8, height=4)
        summary_layout.addWidget(self.summary_chart)
        
        summary_frame.setLayout(summary_layout)
        layout.addWidget(summary_frame)
        
        self.tab_summary.setLayout(layout)
    
    def init_equipment_tab(self):
        """장비별 분석 탭 초기화"""
        layout = QVBoxLayout()
        
        # 장비별 차트
        chart_frame = QFrame()
        chart_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        chart_layout = QVBoxLayout()
        
        title_label = QLabel("장비별 검사 결과")
        title_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        chart_layout.addWidget(title_label)
        
        self.equipment_chart = ChartCanvas(width=8, height=4)
        chart_layout.addWidget(self.equipment_chart)
        
        chart_frame.setLayout(chart_layout)
        layout.addWidget(chart_frame)
        
        # 테이블
        table_frame = QFrame()
        table_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        table_layout = QVBoxLayout()
        
        table_title = QLabel("장비별 상세 데이터")
        table_title.setStyleSheet("font-weight: bold;")
        table_layout.addWidget(table_title)
        
        self.equipment_table = QTableWidget()
        self.equipment_table.setColumnCount(5)
        self.equipment_table.setHorizontalHeaderLabels(["장비명", "검사 수", "양품", "불량", "양품률"])
        self.equipment_table.horizontalHeader().setStretchLastSection(True)
        
        table_layout.addWidget(self.equipment_table)
        table_frame.setLayout(table_layout)
        layout.addWidget(table_frame)
        
        self.tab_equipment.setLayout(layout)
    
    def init_product_tab(self):
        """제품별 분석 탭 초기화"""
        layout = QVBoxLayout()
        
        # 제품별 차트
        self.product_chart = ChartCanvas(width=8, height=6)
        layout.addWidget(self.product_chart, 3)
        
        # 테이블
        table_frame = QFrame()
        table_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        table_layout = QVBoxLayout()
        
        # 테이블 제목
        title_label = QLabel("제품별 검사 결과")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #333333;
            }
        """)
        table_layout.addWidget(title_label)
        
        # 테이블 위젯
        self.product_table = QTableWidget()
        self.product_table.setColumnCount(5)
        self.product_table.setHorizontalHeaderLabels(["제품명", "검사수", "양품", "불량", "양품률"])
        self.product_table.horizontalHeader().setStretchLastSection(True)
        self.product_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table_layout.addWidget(self.product_table)
        
        table_frame.setLayout(table_layout)
        layout.addWidget(table_frame, 2)
        
        self.tab_product.setLayout(layout)
    
    def init_daily_tab(self):
        """일별 추이 탭 초기화"""
        layout = QVBoxLayout()
        
        # 일별 추이 차트
        chart_frame = QFrame()
        chart_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        chart_layout = QVBoxLayout()
        
        title_label = QLabel("일별 검사 결과 추이")
        title_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        chart_layout.addWidget(title_label)
        
        self.daily_chart = ChartCanvas(width=8, height=4)
        chart_layout.addWidget(self.daily_chart)
        
        chart_frame.setLayout(chart_layout)
        layout.addWidget(chart_frame)
        
        # 테이블
        table_frame = QFrame()
        table_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        table_layout = QVBoxLayout()
        
        table_title = QLabel("일별 상세 데이터")
        table_title.setStyleSheet("font-weight: bold;")
        table_layout.addWidget(table_title)
        
        self.daily_table = QTableWidget()
        self.daily_table.setColumnCount(5)
        self.daily_table.setHorizontalHeaderLabels(["날짜", "양품", "불량", "검사 수", "양품률"])
        self.daily_table.horizontalHeader().setStretchLastSection(True)
        
        table_layout.addWidget(self.daily_table)
        table_frame.setLayout(table_layout)
        layout.addWidget(table_frame)
        
        self.tab_daily.setLayout(layout)
    
    def init_roi_analysis_tab(self):
        """ROI별 불량 분석 탭 초기화"""
        layout = QVBoxLayout()
        
        # 차트 영역
        chart_frame = QFrame()
        chart_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        chart_layout = QVBoxLayout()
        
        title_label = QLabel("ROI별 불량 발생 빈도")
        title_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        chart_layout.addWidget(title_label)
        
        self.roi_chart = ChartCanvas(width=8, height=6)
        chart_layout.addWidget(self.roi_chart)
        
        chart_frame.setLayout(chart_layout)
        layout.addWidget(chart_frame, 3)  # 3:2 비율로 차트 영역이 더 크게
        
        # 테이블 영역
        table_frame = QFrame()
        table_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        table_layout = QVBoxLayout()
        
        table_title = QLabel("ROI별 불량 상세 데이터")
        table_title.setStyleSheet("font-weight: bold;")
        table_layout.addWidget(table_title)
        
        self.roi_table = QTableWidget()
        self.roi_table.setColumnCount(5)
        self.roi_table.setHorizontalHeaderLabels(["ROI 이름", "검사 총계", "불량 횟수", "불량률", "주요 불량 유형"])
        self.roi_table.horizontalHeader().setStretchLastSection(True)
        self.roi_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        table_layout.addWidget(self.roi_table)
        table_frame.setLayout(table_layout)
        layout.addWidget(table_frame, 2)  # 3:2 비율
        
        self.tab_roi_analysis.setLayout(layout)
    
    def update_data(self):
        """선택된 필터에 따라 데이터 업데이트"""
        try:
            # 선택된 장비와 제품 ID
            equipment_id = self.equipment_combo.currentData()
            product_id = self.product_combo.currentData()
            
            # 날짜 범위
            start_date = self.start_date.date().toString(Qt.ISODate)
            end_date = self.end_date.date().toString(Qt.ISODate)
            
            print(f"데이터 업데이트: 장비={equipment_id}, 제품={product_id}, 기간={start_date}~{end_date}")
            
            # 각 탭 데이터 업데이트
            self.update_summary_tab(equipment_id, product_id, start_date, end_date)
            self.update_equipment_tab(equipment_id, product_id, start_date, end_date)
            self.update_product_tab(equipment_id, product_id, start_date, end_date)
            self.update_daily_tab(equipment_id, product_id, start_date, end_date)
            self.update_roi_analysis_tab(equipment_id, product_id, start_date, end_date)
            
        except Exception as e:
            print(f"데이터 업데이트 중 오류: {str(e)}")
            self.show_error_message(f"데이터 업데이트 중 오류가 발생했습니다: {str(e)}")
    
    def update_summary_tab(self, equipment_id, product_id, start_date, end_date):
        """요약 탭 업데이트"""
        try:
            # 요약 데이터 가져오기
            summary_data = self.get_summary_data(equipment_id, product_id, start_date, end_date)
            
            # 요약 정보 업데이트
            self.total_label.setText(f"총 검사 건수: {summary_data['total_inspections']:,}")
            self.pass_label.setText(f"양품: {summary_data['pass_count']:,}")
            self.fail_label.setText(f"불량: {summary_data['fail_count']:,}")
            self.rate_label.setText(f"양품률: {summary_data['pass_rate']:.2f}%")
            
            # 차트 업데이트
            ax = self.summary_chart.axes
            ax.clear()
            
            # 파이 차트 데이터
            labels = ['양품', '불량']
            sizes = [summary_data['pass_count'], summary_data['fail_count']]
            colors = ['#4CAF50', '#F44336']
            
            # 검사 건수가 없으면 "데이터 없음" 표시
            if summary_data['total_inspections'] == 0:
                self.show_no_data(self.summary_chart)
                return
            
            # 파이 차트 그리기
            wedges, texts, autotexts = ax.pie(
                sizes, 
                labels=labels, 
                colors=colors,
                autopct='%1.1f%%', 
                startangle=90,
                wedgeprops={'edgecolor': 'w', 'linewidth': 1}
            )
            
            # 텍스트 스타일 설정
            for text in texts:
                text.set_fontsize(12)
            
            for autotext in autotexts:
                autotext.set_fontsize(10)
                autotext.set_color('white')
            
            ax.set_title('검사 결과 비율', fontsize=14)
            
            self.summary_chart.draw()
            
        except Exception as e:
            print(f"요약 탭 업데이트 오류: {str(e)}")
            import traceback
            traceback.print_exc()  # 자세한 오류 정보 출력
            self.show_error(f"요약 데이터 업데이트 중 오류: {str(e)}")
    
    def update_equipment_tab(self, equipment_id, product_id, start_date, end_date):
        """장비별 분석 탭 업데이트"""
        try:
            # 장비별 데이터 가져오기 (실제로는 DB 쿼리로 대체)
            equipment_data = self.get_equipment_data(product_id, start_date, end_date)
            
            if not equipment_data:
                # 데이터가 없는 경우
                self.show_no_data(self.equipment_chart)
                self.equipment_table.setRowCount(0)
                return
            
            # 차트 업데이트
            ax = self.equipment_chart.axes
            ax.clear()
            
            # 데이터 준비
            equipment_names = [item['equipment_name'] for item in equipment_data]
            pass_counts = [item['pass_count'] for item in equipment_data]
            fail_counts = [item['fail_count'] for item in equipment_data]
            total_counts = [item['total_count'] for item in equipment_data]
            pass_rates = [item['pass_rate'] for item in equipment_data]
            
            # 막대 그래프 생성
            x = range(len(equipment_names))
            bar_width = 0.35
            
            # 양품/불량 막대 그래프
            bars1 = ax.bar(
                [i - bar_width/2 for i in x], 
                pass_counts, 
                bar_width, 
                label='양품', 
                color='#4CAF50'
            )
            
            bars2 = ax.bar(
                [i + bar_width/2 for i in x], 
                fail_counts, 
                bar_width, 
                label='불량', 
                color='#F44336'
            )
            
            # 양품률 선 그래프 (보조 축)
            ax2 = ax.twinx()
            line = ax2.plot(x, pass_rates, 'o-', color='#2196F3', label='양품률(%)')
            
            # 축 및 레이블 설정
            ax.set_xlabel('장비')
            ax.set_ylabel('검사 수')
            ax2.set_ylabel('양품률(%)')
            ax.set_title('장비별 검사 결과', fontsize=14)
            ax.set_xticks(x)
            ax.set_xticklabels(equipment_names, rotation=45)
            
            # Y축 범위 설정
            ax2.set_ylim(0, 100)
            
            # 범례 통합
            lines, labels = ax.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax.legend(lines + lines2, labels + labels2, loc='upper left')
            
            # 각 막대에 값 표시
            for bar in bars1:
                height = bar.get_height()
                if height > 0:
                    ax.text(
                        bar.get_x() + bar.get_width()/2.,
                        height,
                        str(int(height)),
                        ha='center', va='bottom',
                        fontsize=8
                    )
            
            for bar in bars2:
                height = bar.get_height()
                if height > 0:
                    ax.text(
                        bar.get_x() + bar.get_width()/2.,
                        height,
                        str(int(height)),
                        ha='center', va='bottom',
                        fontsize=8
                    )
            
            # 그리드 설정
            ax.grid(True, linestyle='--', alpha=0.7, axis='y')
            
            # 레이아웃 조정
            self.equipment_chart.fig.tight_layout()
            self.equipment_chart.draw()
            
            # 테이블 업데이트
            self.equipment_table.setRowCount(len(equipment_data))
            
            for row, data in enumerate(equipment_data):
                self.equipment_table.setItem(row, 0, QTableWidgetItem(data['equipment_name']))
                self.equipment_table.setItem(row, 1, QTableWidgetItem(str(data['total_count'])))
                self.equipment_table.setItem(row, 2, QTableWidgetItem(str(data['pass_count'])))
                self.equipment_table.setItem(row, 3, QTableWidgetItem(str(data['fail_count'])))
                
                # 양품률 셀 및 배경색 설정
                pass_rate_item = QTableWidgetItem(f"{data['pass_rate']:.2f}%")
                
                if data['pass_rate'] >= 90:
                    pass_rate_item.setBackground(QColor('#C8E6C9'))  # 녹색 (양호)
                elif data['pass_rate'] >= 70:
                    pass_rate_item.setBackground(QColor('#FFECB3'))  # 노란색 (주의)
                else:
                    pass_rate_item.setBackground(QColor('#FFCDD2'))  # 빨간색 (불량)
                    
                self.equipment_table.setItem(row, 4, pass_rate_item)
                
            # 열 너비 조정
            self.equipment_table.resizeColumnsToContents()
            
        except Exception as e:
            print(f"장비별 분석 탭 업데이트 오류: {str(e)}")
            self.show_error(f"장비별 데이터 업데이트 중 오류: {str(e)}")
    
    def update_product_tab(self, equipment_id, product_id, start_date, end_date):
        """제품별 분석 탭 업데이트"""
        try:
            # 제품별 데이터 가져오기
            product_data = self.get_product_data(equipment_id, start_date, end_date)
            
            # 데이터가 없는 경우 처리
            if not product_data:
                self.show_no_data(self.product_chart)
                self.product_table.setRowCount(0)
                return
            
            # 차트 업데이트
            ax = self.product_chart.axes
            ax.clear()
            
            # 데이터 준비
            product_names = [item['product_name'] for item in product_data]
            pass_rates = [item['pass_rate'] for item in product_data]
            
            # 가로 막대 그래프 생성
            bars = ax.barh(product_names, pass_rates, color='#2196F3')
            
            # Y축 레이블 이름 설정 - 글꼴 크기 조정
            ax.set_yticks(range(len(product_names)))
            ax.set_yticklabels(product_names, fontsize=10)
            
            # X축 범위 설정 (0-100%)
            ax.set_xlim(0, 100)
            ax.set_xlabel('양품률 (%)')
            
            # 제목 설정
            ax.set_title('제품별 검사 결과', fontsize=14, pad=20)  # 제목과 그래프 사이 여백 추가
            
            # 각 막대 위에 값 표시
            for i, bar in enumerate(bars):
                ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2, 
                       f'{pass_rates[i]:.1f}%', 
                       va='center', fontsize=9)
            
            # 그리드 설정
            ax.grid(axis='x', linestyle='--', alpha=0.7)
            
            # 차트 레이아웃 조정
            self.product_chart.fig.tight_layout()
            
            # 차트 그리기
            self.product_chart.draw()
            
            # 표 업데이트
            self.product_table.setRowCount(len(product_data))
            
            for i, data in enumerate(product_data):
                self.product_table.setItem(i, 0, QTableWidgetItem(data['product_name']))
                self.product_table.setItem(i, 1, QTableWidgetItem(f"{data['total_count']:,}"))
                self.product_table.setItem(i, 2, QTableWidgetItem(f"{data['pass_count']:,}"))
                self.product_table.setItem(i, 3, QTableWidgetItem(f"{data['fail_count']:,}"))
                self.product_table.setItem(i, 4, QTableWidgetItem(f"{data['pass_rate']:.2f}%"))
                
                # 가운데 정렬
                for j in range(1, 5):
                    item = self.product_table.item(i, j)
                    item.setTextAlignment(Qt.AlignCenter)
            
        except Exception as e:
            print(f"제품별 탭 업데이트 오류: {str(e)}")
            import traceback
            traceback.print_exc()
            self.show_error(f"제품별 데이터 업데이트 중 오류: {str(e)}")
    
    def update_daily_tab(self, equipment_id, product_id, start_date, end_date):
        """일별 추이 탭 업데이트"""
        try:
            # 일별 데이터 가져오기 (실제로는 DB 쿼리로 대체)
            daily_data = self.get_daily_data(equipment_id, product_id, start_date, end_date)
            
            if not daily_data:
                # 데이터가 없는 경우
                self.show_no_data(self.daily_chart)
                self.daily_table.setRowCount(0)
                return
            
            # 차트 업데이트
            ax = self.daily_chart.axes
            ax.clear()
            
            # 데이터 준비
            dates = [item['date'] for item in daily_data]
            pass_counts = [item['pass_count'] for item in daily_data]
            fail_counts = [item['fail_count'] for item in daily_data]
            total_counts = [item['total_count'] for item in daily_data]
            pass_rates = [item['pass_rate'] for item in daily_data]
            
            # 선 그래프 생성
            ax.plot(dates, pass_counts, label='양품')
            ax.plot(dates, fail_counts, label='불량')
            
            # 축 및 레이블 설정
            ax.set_xlabel('날짜')
            ax.set_ylabel('검사 수')
            ax.set_title('일별 검사 결과', fontsize=14)
            
            # 범례 표시
            ax.legend()
            
            # 그리드 설정
            ax.grid(True, linestyle='--', alpha=0.7)
            
            # 레이아웃 조정
            self.daily_chart.fig.tight_layout()
            self.daily_chart.draw()
            
            # 테이블 업데이트
            self.daily_table.setRowCount(len(daily_data))
            self.daily_table.setColumnCount(5)
            self.daily_table.setHorizontalHeaderLabels(["날짜", "양품", "불량", "검사 수", "양품률"])
            self.daily_table.horizontalHeader().setStretchLastSection(True)
            
            for row, data in enumerate(daily_data):
                self.daily_table.setItem(row, 0, QTableWidgetItem(data['date']))
                self.daily_table.setItem(row, 1, QTableWidgetItem(str(data['pass_count'])))
                self.daily_table.setItem(row, 2, QTableWidgetItem(str(data['fail_count'])))
                self.daily_table.setItem(row, 3, QTableWidgetItem(str(data['total_count'])))
                self.daily_table.setItem(row, 4, QTableWidgetItem(f"{data['pass_rate']:.2f}%"))
            
            # 열 너비 조정
            self.daily_table.resizeColumnsToContents()
            
        except Exception as e:
            print(f"일별 추이 탭 업데이트 오류: {str(e)}")
            self.show_error(f"일별 데이터 업데이트 중 오류: {str(e)}")
    
    def update_roi_analysis_tab(self, equipment_id, product_id, start_date, end_date):
        """ROI별 불량 분석 탭 업데이트"""
        try:
            # ROI별 불량 데이터 가져오기
            roi_data = self.get_roi_analysis_data(equipment_id, product_id, start_date, end_date)
            
            # 데이터가 없는 경우 처리
            if not roi_data:
                self.show_no_data(self.roi_chart)
                self.roi_table.setRowCount(0)
                return
            
            # 차트 업데이트
            ax = self.roi_chart.axes
            ax.clear()
            
            # None 값 필터링 및 데이터 준비 (상위 10개만 표시)
            # None 값이나 빈 문자열은 "이름 없음"으로 대체
            valid_roi_data = []
            for item in roi_data:
                if item['roi_name'] is None or item['roi_name'].strip() == '':
                    item['roi_name'] = "이름 없음"
                valid_roi_data.append(item)
            
            top_rois = valid_roi_data[:10]
            
            # 데이터가 없는 경우 처리
            if not top_rois:
                self.show_no_data(self.roi_chart)
                self.roi_table.setRowCount(0)
                return
            
            roi_names = [item['roi_name'] for item in top_rois]
            fail_rates = [float(item['fail_rate']) for item in top_rois]  # 명시적으로 float 변환
            
            # 데이터 디버깅 출력
            print(f"ROI 이름: {roi_names}")
            print(f"불량률: {fail_rates}")
            
            # 수평 막대 그래프로 표시 (불량률이 높은 순)
            bars = ax.barh(roi_names, fail_rates, color='#F44336')
            
            # 차트 스타일 설정
            ax.set_xlabel('불량률 (%)')
            ax.set_title('ROI별 불량률 (상위 10개)', fontsize=14)
            
            # 각 막대에 값 표시
            for i, bar in enumerate(bars):
                ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2, 
                       f'{fail_rates[i]:.1f}%', 
                       va='center', fontsize=9)
            
            # 축 범위 및 그리드 설정
            ax.set_xlim(0, max(fail_rates) * 1.2 if fail_rates else 100)
            ax.grid(axis='x', linestyle='--', alpha=0.7)
            
            # 차트 레이아웃 조정
            self.roi_chart.fig.tight_layout()
            self.roi_chart.draw()
            
            # 테이블 업데이트
            self.roi_table.setRowCount(len(valid_roi_data))
            
            for i, data in enumerate(valid_roi_data):
                self.roi_table.setItem(i, 0, QTableWidgetItem(data['roi_name']))
                self.roi_table.setItem(i, 1, QTableWidgetItem(f"{data['total_count']:,}"))
                self.roi_table.setItem(i, 2, QTableWidgetItem(f"{data['fail_count']:,}"))
                
                # 불량률 셀 - 배경색 설정
                fail_rate_item = QTableWidgetItem(f"{data['fail_rate']:.2f}%")
                if data['fail_rate'] >= 20:
                    fail_rate_item.setBackground(QColor('#FFCDD2'))  # 빨간색 (심각)
                elif data['fail_rate'] >= 10:
                    fail_rate_item.setBackground(QColor('#FFECB3'))  # 노란색 (주의)
                else:
                    fail_rate_item.setBackground(QColor('#C8E6C9'))  # 녹색 (양호)
                    
                self.roi_table.setItem(i, 3, fail_rate_item)
                self.roi_table.setItem(i, 4, QTableWidgetItem(data['main_fail_algorithm']))
                
                # 가운데 정렬
                for j in range(1, 5):
                    item = self.roi_table.item(i, j)
                    item.setTextAlignment(Qt.AlignCenter)
        
        except Exception as e:
            print(f"ROI별 분석 탭 업데이트 오류: {str(e)}")
            import traceback
            traceback.print_exc()  
            self.show_error(f"ROI별 분석 데이터 업데이트 중 오류: {str(e)}")
    
    def show_error_message(self, message):
        """에러 메시지 표시"""
        QMessageBox.warning(self, "오류", message)
    
    def get_summary_data(self, equipment_id, product_id, start_date, end_date):
        """요약 데이터 가져오기"""
        try:
            conn = self.db_manager._get_connection()
            cursor = conn.cursor()
            
            query_params = []
            query = """
                SELECT 
                    COUNT(*) as total_inspections,
                    SUM(CASE WHEN overall_result = 'PASS' THEN 1 ELSE 0 END) as pass_count,
                    SUM(CASE WHEN overall_result = 'FAIL' THEN 1 ELSE 0 END) as fail_count
                FROM inspection_result_table
                WHERE inspection_datetime BETWEEN ? AND ?
            """
            query_params.extend([f"{start_date} 00:00:00", f"{end_date} 23:59:59"])
            
            if equipment_id:
                query += " AND equipment_id = ?"
                query_params.append(equipment_id)
            
            if product_id:
                query += " AND product_id = ?"
                query_params.append(product_id)
            
            cursor.execute(query, query_params)
            result = cursor.fetchone()
            
            # 딕셔너리로 결과 반환 (인덱스가 아닌 키로 접근하기 위함)
            if result:
                return {
                    'total_inspections': result[0] or 0,
                    'pass_count': result[1] or 0,
                    'fail_count': result[2] or 0,
                    'pass_rate': (result[1] / result[0] * 100) if result[0] and result[1] else 0
                }
            else:
                return {
                    'total_inspections': 0,
                    'pass_count': 0,
                    'fail_count': 0,
                    'pass_rate': 0
                }
            
        except Exception as e:
            print(f"요약 데이터 조회 오류: {str(e)}")
            return {
                'total_inspections': 0,
                'pass_count': 0,
                'fail_count': 0,
                'pass_rate': 0
            }
        finally:
            if conn:
                conn.close()
    
    def get_equipment_data(self, product_id, start_date, end_date):
        """장비별 데이터 가져오기"""
        try:
            conn = self.db_manager._get_connection()
            cursor = conn.cursor()
            
            query_params = []
            query = """
                SELECT 
                    e.equipment_id,
                    e.equipment_name,
                    COUNT(ir.result_id) as total_count,
                    SUM(CASE WHEN ir.overall_result = 'PASS' THEN 1 ELSE 0 END) as pass_count,
                    SUM(CASE WHEN ir.overall_result = 'FAIL' THEN 1 ELSE 0 END) as fail_count
                FROM equipment_table e
                LEFT JOIN inspection_result_table ir ON e.equipment_id = ir.equipment_id
                WHERE ir.inspection_datetime BETWEEN ? AND ?
            """
            query_params.extend([f"{start_date} 00:00:00", f"{end_date} 23:59:59"])
            
            if product_id:
                query += " AND ir.product_id = ?"
                query_params.append(product_id)
            
            query += " GROUP BY e.equipment_id, e.equipment_name"
            
            cursor.execute(query, query_params)
            results = cursor.fetchall()
            
            equipment_data = []
            for row in results:
                total_count = row[2] or 0
                pass_count = row[3] or 0
                fail_count = row[4] or 0
                
                if total_count > 0:
                    pass_rate = (pass_count / total_count * 100)
                    
                    equipment_data.append({
                        'equipment_id': row[0],
                        'equipment_name': row[1],
                        'total_count': total_count,
                        'pass_count': pass_count,
                        'fail_count': fail_count,
                        'pass_rate': pass_rate
                    })
            
            return equipment_data
            
        except Exception as e:
            print(f"장비별 데이터 조회 오류: {str(e)}")
            return []
        finally:
            if conn:
                conn.close()
    
    def get_product_data(self, equipment_id, start_date, end_date):
        """제품별 데이터 가져오기"""
        try:
            conn = self.db_manager._get_connection()
            cursor = conn.cursor()
            
            query_params = []
            query = """
                SELECT 
                    p.product_id,
                    p.product_name,
                    COUNT(ir.result_id) as total_count,
                    SUM(CASE WHEN ir.overall_result = 'PASS' THEN 1 ELSE 0 END) as pass_count,
                    SUM(CASE WHEN ir.overall_result = 'FAIL' THEN 1 ELSE 0 END) as fail_count
                FROM product_table p
                LEFT JOIN inspection_result_table ir ON p.product_id = ir.product_id
                WHERE ir.inspection_datetime BETWEEN ? AND ?
            """
            query_params.extend([f"{start_date} 00:00:00", f"{end_date} 23:59:59"])
            
            if equipment_id:
                query += " AND ir.equipment_id = ?"
                query_params.append(equipment_id)
            
            query += " GROUP BY p.product_id, p.product_name"
            
            cursor.execute(query, query_params)
            results = cursor.fetchall()
            
            product_data = []
            for row in results:
                total_count = row[2] or 0
                pass_count = row[3] or 0
                fail_count = row[4] or 0
                
                if total_count > 0:
                    pass_rate = (pass_count / total_count * 100)
                    
                    product_data.append({
                        'product_id': row[0],
                        'product_name': row[1],
                        'total_count': total_count,
                        'pass_count': pass_count,
                        'fail_count': fail_count,
                        'pass_rate': pass_rate
                    })
            
            return product_data
            
        except Exception as e:
            print(f"제품별 데이터 조회 오류: {str(e)}")
            return []
        finally:
            if conn:
                conn.close()
    
    def get_daily_data(self, equipment_id, product_id, start_date, end_date):
        """일별 데이터 가져오기"""
        try:
            conn = self.db_manager._get_connection()
            cursor = conn.cursor()
            
            query_params = []
            # DATE 함수 사용하여 inspection_datetime을 날짜로 변환
            query = """
                SELECT 
                    DATE(inspection_datetime) as date,
                    COUNT(result_id) as total_count,
                    SUM(CASE WHEN overall_result = 'PASS' THEN 1 ELSE 0 END) as pass_count,
                    SUM(CASE WHEN overall_result = 'FAIL' THEN 1 ELSE 0 END) as fail_count
                FROM inspection_result_table
                WHERE inspection_datetime BETWEEN ? AND ?
            """
            query_params.extend([f"{start_date} 00:00:00", f"{end_date} 23:59:59"])
            
            if equipment_id:
                query += " AND equipment_id = ?"
                query_params.append(equipment_id)
            
            if product_id:
                query += " AND product_id = ?"
                query_params.append(product_id)
            
            # inspection_date 대신 date로 그룹화 (위에서 지정한 별칭)
            query += " GROUP BY DATE(inspection_datetime) ORDER BY DATE(inspection_datetime)"
            
            cursor.execute(query, query_params)
            results = cursor.fetchall()
            
            daily_data = []
            for row in results:
                # 인덱스로 접근 (0: date, 1: total_count, 2: pass_count, 3: fail_count)
                date_str = row[0]
                total_count = row[1] or 0
                pass_count = row[2] or 0
                fail_count = row[3] or 0
                
                if total_count > 0:
                    pass_rate = (pass_count / total_count * 100)
                    
                    daily_data.append({
                        'date': date_str,
                        'total_count': total_count,
                        'pass_count': pass_count,
                        'fail_count': fail_count,
                        'pass_rate': pass_rate
                    })
            
            return daily_data
            
        except Exception as e:
            print(f"일별 데이터 조회 오류: {str(e)}")
            return []
        finally:
            if conn:
                conn.close()
    
    def get_roi_analysis_data(self, equipment_id, product_id, start_date, end_date):
        """ROI별 불량 데이터 가져오기"""
        try:
            conn = self.db_manager._get_connection()
            cursor = conn.cursor()
            
            # 샘플 데이터 구조 파악
            cursor.execute("SELECT roi_results FROM inspection_result_table LIMIT 1")
            sample = cursor.fetchone()
            print(f"샘플 ROI 결과 데이터: {sample[0] if sample else '없음'}")
            
            # 검사 결과 조회 및 Python에서 JSON 파싱
            query = """
                SELECT 
                    result_id, 
                    roi_results,
                    overall_result
                FROM 
                    inspection_result_table
                WHERE 
                    inspection_datetime BETWEEN ? AND ?
            """
            query_params = [f"{start_date} 00:00:00", f"{end_date} 23:59:59"]
            
            if equipment_id:
                query += " AND equipment_id = ?"
                query_params.append(equipment_id)
            
            if product_id:
                query += " AND product_id = ?"
                query_params.append(product_id)
            
            cursor.execute(query, query_params)
            raw_results = cursor.fetchall()
            
            # Python에서 JSON 파싱 및 집계
            roi_data = {}
            
            for row in raw_results:
                result_id, roi_results_json, overall_result = row
                try:
                    if not roi_results_json:
                        continue
                    
                    # 공통 유틸리티 함수로 JSON 파싱
                    roi_results = parse_json_safely(roi_results_json)
                    if roi_results is None:
                        continue
                    
                    # 유틸리티 함수로 ROI 데이터 추출
                    roi_name, results, is_fail, main_fail_algorithm = extract_roi_data(roi_results)
                    
                    # 전체 검사 결과가 FAIL이면 ROI도 FAIL로 간주
                    if overall_result == 'FAIL' and not is_fail:
                        is_fail = True
                        if not main_fail_algorithm:
                            main_fail_algorithm = "미상"
                    
                    # roi_name이 없으면 다음 결과로
                    if not roi_name:
                        continue
                    
                    # ROI 통계 집계
                    if roi_name not in roi_data:
                        roi_data[roi_name] = {
                            'total_count': 1,
                            'fail_count': 1 if is_fail else 0,
                            'main_fail_algorithm': main_fail_algorithm
                        }
                    else:
                        roi_data[roi_name]['total_count'] += 1
                        if is_fail:
                            roi_data[roi_name]['fail_count'] += 1
                            # 주요 불량 알고리즘 업데이트
                            if main_fail_algorithm:
                                roi_data[roi_name]['main_fail_algorithm'] = main_fail_algorithm
                
                except Exception as e:
                    print(f"ROI 결과 처리 중 오류: {str(e)}")
                    import traceback
                    traceback.print_exc()
            
            # 결과를 리스트로 변환
            result_list = []
            for roi_name, data in roi_data.items():
                # None 값이나 빈 문자열 대신 "이름 없음" 사용
                if roi_name is None or roi_name.strip() == '':
                    roi_name = "이름 없음"
                    
                if data['total_count'] > 0:
                    result_list.append({
                        'roi_name': roi_name,
                        'total_count': data['total_count'],
                        'fail_count': data['fail_count'],
                        'fail_rate': (data['fail_count'] / data['total_count'] * 100) if data['total_count'] > 0 else 0,
                        'main_fail_algorithm': data['main_fail_algorithm'] or "미상"
                    })
            
            # 불량률에 따라 정렬
            result_list.sort(key=lambda x: x['fail_rate'], reverse=True)
            
            print(f"ROI 분석 최종 결과: {len(result_list)}개 ROI 통계 생성")
            return result_list
            
        except Exception as e:
            print(f"ROI별 불량 데이터 조회 오류: {str(e)}")
            import traceback
            traceback.print_exc()
            return []
        finally:
            if conn:
                conn.close()
    
    def show_no_data(self, chart):
        """데이터 없음 표시"""
        ax = chart.axes
        ax.clear()
        ax.text(0.5, 0.5, '데이터가 없습니다', horizontalalignment='center', 
                verticalalignment='center', transform=ax.transAxes)
        chart.draw()
    
    def show_error(self, message):
        """에러 메시지 표시 (show_error_message의 별칭)"""
        self.show_error_message(message)
    
    def setup_korean_font(self):
        """한글 폰트 설정"""
        try:
            import matplotlib
            import matplotlib.font_manager as fm
            import platform
            
            # 운영체제별 기본 폰트 설정
            system = platform.system()
            
            if system == 'Windows':
                # Windows 기본 폰트
                font_path = 'C:/Windows/Fonts/malgun.ttf'  # 맑은 고딕
                font_family = 'Malgun Gothic'
            elif system == 'Darwin':  # macOS
                # macOS 기본 폰트
                font_path = '/System/Library/Fonts/AppleSDGothicNeo.ttc'
                font_family = 'AppleSDGothicNeo'
            else:  # Linux 등
                # 나눔고딕 폰트 (미리 설치되어 있어야 함)
                font_path = '/usr/share/fonts/truetype/nanum/NanumGothic.ttf'
                font_family = 'NanumGothic'
            
            # 폰트 파일 존재 여부 확인
            import os
            if not os.path.exists(font_path):
                # 대체 폰트 찾기
                font_list = fm.findSystemFonts()
                korean_fonts = []
                
                # 한글 지원 가능한 폰트 찾기
                for font in font_list:
                    try:
                        font_name = fm.FontProperties(fname=font).get_name()
                        # 한글 관련 폰트 이름에 포함될만한 키워드
                        if any(keyword in font_name.lower() for keyword in ['gothic', 'gulim', 'batang', 'malgun', 'nanum', '고딕', '굴림', '바탕']):
                            korean_fonts.append(font)
                    except:
                        pass
                
                if korean_fonts:
                    font_path = korean_fonts[0]
                    font_family = fm.FontProperties(fname=font_path).get_name()
                    print(f"대체 한글 폰트 사용: {font_family} ({font_path})")
                else:
                    print("한글 폰트를 찾을 수 없습니다. 기본 폰트를 사용합니다.")
                    return
            
            # 폰트 설정 적용
            font_prop = fm.FontProperties(fname=font_path)
            matplotlib.rcParams['font.family'] = font_prop.get_name()
            matplotlib.rcParams['axes.unicode_minus'] = False  # 마이너스 기호 깨짐 방지
            
            print(f"한글 폰트 설정 완료: {font_family}")
            
        except Exception as e:
            print(f"폰트 설정 중 오류 발생: {str(e)}") 