from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget, QPushButton,
    QLabel, QMessageBox, QFormLayout, QSpinBox, QDoubleSpinBox,
    QLineEdit, QCheckBox, QGroupBox, QScrollArea, QSlider
)
from PyQt5.QtCore import Qt
import cv2
import inspect
import importlib
import shutil
import datetime
import os
from config.model_setting import ALGORITHM_PARAMETER

class AlgorithmSettingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("알고리즘 파라미터 설정")
        self.setMinimumSize(800, 600)
        
        # 설정값 로드
        self.load_settings()
        
        # UI 초기화
        self.initUI()
    
    def load_settings(self):
        """model_setting.py에서 현재 설정값 로드"""
        self.current_settings = ALGORITHM_PARAMETER.copy()
        
        # 파라미터 설명 정보 (추후 확장 가능)
        self.param_descriptions = {
            "hsv": {
                "h_offset": "색상(Hue) 허용 오차 범위 (0-180)",
                "s_offset": "채도(Saturation) 허용 오차 범위 (0-255)",
                "v_offset": "명도(Value) 허용 오차 범위 (0-255)",
                "matching_rate_threshold": "매칭 성공으로 판단할 최소 비율 (0-1)"
            },
            "template": {
                "method": "템플릿 매칭 방법 (cv2.TM_* 상수)",
                "threshold": "매칭 임계값 (0-1)",
                "matching_rate_threshold": "매칭 성공 비율 임계값 (0-1)"
            },
            "sift": {
                "n_features": "특징점 개수 (0: 자동)",
                "threshold": "특징점 매칭 임계값 (0-1)",
                "matching_rate_threshold": "매칭 성공 비율 임계값 (0-1)"
            },
            "orb": {
                "n_features": "특징점 개수",
                "scale_factor": "스케일 인자",
                "matching_rate_threshold": "매칭 성공 비율 임계값 (0-1)"
            },
            "flann": {
                "trees": "kd-tree 개수",
                "checks": "검색 반복 횟수",
                "matching_rate_threshold": "매칭 성공 비율 임계값 (0-1)"
            }
        }
        
        # 파라미터 범위 정의
        self.param_ranges = {
            "hsv": {
                "h_offset": (0, 180),
                "s_offset": (0, 255),
                "v_offset": (0, 255),
                "matching_rate_threshold": (0.0, 1.0)
            },
            "template": {
                "threshold": (0.0, 1.0),
                "matching_rate_threshold": (0.0, 1.0)
            },
            "sift": {
                "n_features": (0, 10000),
                "threshold": (0.0, 1.0),
                "matching_rate_threshold": (0.0, 1.0)
            },
            "orb": {
                "n_features": (1, 10000),
                "scale_factor": (1.0, 2.0),
                "matching_rate_threshold": (0.0, 1.0)
            },
            "flann": {
                "trees": (1, 50),
                "checks": (1, 300),
                "matching_rate_threshold": (0.0, 1.0)
            }
        }
    
    def initUI(self):
        main_layout = QVBoxLayout()
        
        # 알고리즘 탭 위젯
        tab_widget = QTabWidget()
        
        # 입력 위젯 저장
        self.inputs = {}
        
        # 각 알고리즘별 탭 생성
        for algo_name, params in self.current_settings.items():
            tab = QWidget()
            tab_layout = QVBoxLayout()
            
            # 알고리즘 설명 라벨
            info_label = QLabel(f"{algo_name.upper()} 알고리즘 파라미터")
            info_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px;")
            tab_layout.addWidget(info_label)
            
            # 스크롤 영역 생성
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            
            # 파라미터 폼
            form_widget = QWidget()
            form_layout = QFormLayout()
            form_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
            
            # 알고리즘별 입력 위젯 저장
            self.inputs[algo_name] = {}
            
            # 각 파라미터별 입력 위젯 생성
            for param_name, param_value in params.items():
                # 파라미터 그룹 박스
                param_group = QGroupBox()
                param_layout = QVBoxLayout()
                
                # 파라미터 설명 추가
                desc_text = self.param_descriptions.get(algo_name, {}).get(param_name, "")
                if desc_text:
                    desc_label = QLabel(desc_text)
                    desc_label.setWordWrap(True)
                    desc_label.setStyleSheet("color: gray; font-size: 11px;")
                    param_layout.addWidget(desc_label)
                
                # 값 유형에 따른 적절한 위젯 선택
                if isinstance(param_value, bool):
                    input_widget = QCheckBox()
                    input_widget.setChecked(param_value)
                    param_layout.addWidget(input_widget)
                elif isinstance(param_value, int) or isinstance(param_value, float):
                    # 슬라이더와 숫자 입력을 포함하는 레이아웃
                    value_layout = QHBoxLayout()
                    
                    # 범위 설정
                    min_val, max_val = self.param_ranges.get(algo_name, {}).get(param_name, 
                                                          (-9999, 9999) if isinstance(param_value, int) 
                                                          else (-9999.0, 9999.0))
                    
                    # 슬라이더 생성
                    slider = QSlider(Qt.Horizontal)
                    
                    if isinstance(param_value, int):
                        # 정수형 값을 위한 설정
                        slider.setRange(min_val, max_val)
                        slider.setValue(param_value)
                        
                        # 스핀박스 생성
                        spinbox = QSpinBox()
                        spinbox.setRange(min_val, max_val)
                        spinbox.setValue(param_value)
                        
                        # 값 동기화
                        slider.valueChanged.connect(spinbox.setValue)
                        spinbox.valueChanged.connect(slider.setValue)
                        
                        # 입력 위젯으로 스핀박스 사용
                        input_widget = spinbox
                    else:
                        # 부동 소수점 값을 위한 설정 (슬라이더는 정수만 지원하므로 스케일링)
                        scale_factor = 100  # 소수점 두 자리까지 정밀도
                        slider.setRange(int(min_val * scale_factor), int(max_val * scale_factor))
                        slider.setValue(int(param_value * scale_factor))
                        
                        # 스핀박스 생성
                        spinbox = QDoubleSpinBox()
                        spinbox.setRange(min_val, max_val)
                        spinbox.setValue(param_value)
                        spinbox.setSingleStep(0.01)
                        spinbox.setDecimals(4)
                        
                        # 값 동기화 (소수점 변환 고려)
                        slider.valueChanged.connect(lambda v, sb=spinbox, sf=scale_factor: sb.setValue(v / sf))
                        spinbox.valueChanged.connect(lambda v, sl=slider, sf=scale_factor: sl.setValue(int(v * sf)))
                        
                        # 입력 위젯으로 스핀박스 사용
                        input_widget = spinbox
                    
                    # 슬라이더와 스핀박스를 레이아웃에 추가
                    value_layout.addWidget(slider, 7)  # 슬라이더에 더 많은 공간 할당
                    value_layout.addWidget(spinbox, 3)
                    param_layout.addLayout(value_layout)
                else:
                    # cv2 상수 처리 등을 위한 문자열 입력
                    input_widget = QLineEdit(str(param_value))
                    param_layout.addWidget(input_widget)
                
                # 그룹에 레이아웃 설정
                param_group.setLayout(param_layout)
                
                # 입력 위젯 저장
                self.inputs[algo_name][param_name] = input_widget
                
                # 폼에 추가
                form_layout.addRow(f"{param_name}:", param_group)
            
            # 기본값 복원 버튼
            reset_button = QPushButton(f"{algo_name} 기본값으로 복원")
            reset_button.clicked.connect(lambda checked, a=algo_name: self.reset_algorithm(a))
            form_layout.addRow("", reset_button)
            
            form_widget.setLayout(form_layout)
            scroll.setWidget(form_widget)
            tab_layout.addWidget(scroll)
            tab.setLayout(tab_layout)
            tab_widget.addTab(tab, algo_name.upper())
        
        main_layout.addWidget(tab_widget)
        
        # 버튼 영역
        button_layout = QHBoxLayout()
        
        # 저장 버튼
        save_button = QPushButton("저장")
        save_button.clicked.connect(self.collect_and_save)
        
        # 취소 버튼
        cancel_button = QPushButton("취소")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        
        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)
    
    def collect_current_values(self):
        """UI에서 현재 설정값 수집"""
        updated_settings = {}
        
        for algo_name, params in self.inputs.items():
            updated_settings[algo_name] = {}
            
            for param_name, input_widget in params.items():
                # 위젯 유형에 따라 값 추출
                if isinstance(input_widget, QCheckBox):
                    value = input_widget.isChecked()
                elif isinstance(input_widget, QSpinBox):
                    value = input_widget.value()
                elif isinstance(input_widget, QDoubleSpinBox):
                    value = input_widget.value()
                else:
                    # QLineEdit 및 기타
                    raw_value = input_widget.text()
                    
                    # cv2 상수 문자열 처리
                    if "cv2." in raw_value:
                        const_name = raw_value.split("cv2.")[-1]
                        if hasattr(cv2, const_name):
                            value = getattr(cv2, const_name)
                        else:
                            value = raw_value
                    else:
                        # 숫자 변환 시도
                        try:
                            value = float(raw_value)
                            # 정수인 경우 int로 변환
                            if value.is_integer():
                                value = int(value)
                        except ValueError:
                            value = raw_value
                
                updated_settings[algo_name][param_name] = value
        
        return updated_settings
    
    def collect_and_save(self):
        """UI에서 설정값 수집하여 저장"""
        # 현재 설정값 수집
        self.current_settings = self.collect_current_values()
        
        # 설정 파일 백업
        backup_path = self.backup_settings_file()
        print(f"설정 파일 백업: {backup_path}")
        
        # 새 설정값 저장
        if self.write_to_settings_file():
            # 메모리 내 설정 업데이트
            self.reload_settings()
            QMessageBox.information(self, "설정 저장", "알고리즘 파라미터 설정이 저장되었습니다.")
            self.accept()
        else:
            QMessageBox.warning(self, "저장 실패", "설정 저장 중 오류가 발생했습니다.")
    
    def backup_settings_file(self):
        """설정 파일 백업"""
        import config.model_setting
        
        file_path = inspect.getfile(config.model_setting)
        backup_dir = os.path.join(os.path.dirname(file_path), "backups")
        
        # 백업 디렉토리 생성
        os.makedirs(backup_dir, exist_ok=True)
        
        # 백업 파일명 생성
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        backup_path = os.path.join(backup_dir, f"model_setting_{timestamp}.py.bak")
        
        # 파일 복사
        shutil.copy2(file_path, backup_path)
        return backup_path
    
    def write_to_settings_file(self):
        """model_setting.py 파일 수정"""
        try:
            import config.model_setting
            
            # 파일 경로 얻기
            file_path = inspect.getfile(config.model_setting)
            
            with open(file_path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
            
            # ALGORITHM_PARAMETER 정의 부분 찾기
            start_line = -1
            end_line = -1
            bracket_count = 0
            
            for i, line in enumerate(lines):
                if "ALGORITHM_PARAMETER = {" in line:
                    start_line = i
                    bracket_count = line.count('{') - line.count('}')
                elif start_line != -1 and bracket_count > 0:
                    bracket_count += line.count('{') - line.count('}')
                    if bracket_count == 0:
                        end_line = i
                        break
            
            if start_line != -1 and end_line != -1:
                # 새 설정 문자열 생성
                settings_str = ["ALGORITHM_PARAMETER = {\n"]
                
                for algo_name, params in self.current_settings.items():
                    settings_str.append(f'    "{algo_name}" : {{\n')
                    
                    for param_name, param_value in params.items():
                        # 값 유형에 따른 형식 지정
                        if isinstance(param_value, str):
                            value_str = f'"{param_value}"'
                        elif isinstance(param_value, int) or isinstance(param_value, float):
                            value_str = str(param_value)
                        elif isinstance(param_value, bool):
                            value_str = str(param_value)
                        else:
                            # cv2 상수 등 직접 참조
                            value_str = str(param_value)
                        
                        settings_str.append(f'        "{param_name}" : {value_str},\n')
                    
                    settings_str.append('    },\n')
                
                settings_str.append("}\n")
                
                # 파일 업데이트
                new_lines = lines[:start_line] + settings_str + lines[end_line+1:]
                
                with open(file_path, 'w', encoding='utf-8') as file:
                    file.writelines(new_lines)
                
                return True
                
            else:
                print("ALGORITHM_PARAMETER 정의를 찾을 수 없습니다.")
                return False
                
        except Exception as e:
            print(f"설정 파일 쓰기 오류: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def reload_settings(self):
        """메모리 내 설정 다시 로드"""
        try:
            import config.model_setting
            importlib.reload(config.model_setting)
            print("설정 모듈 다시 로드 완료")
            
            # 타겟 매니저 설정 업데이트 신호 발생
            # 메인 윈도우 찾기
            parent = self.parent()
            while parent and not hasattr(parent, 'target_manager'):
                parent = parent.parent()
            
            if parent and hasattr(parent, 'target_manager'):
                if hasattr(parent.target_manager, 'update_algorithm_parameters'):
                    parent.target_manager.update_algorithm_parameters()
                print("타겟 매니저 설정 업데이트")
                
            return True
        except Exception as e:
            print(f"설정 다시 로드 오류: {str(e)}")
            return False
    
    def reset_algorithm(self, algo_name):
        """특정 알고리즘의 설정을 기본값으로 초기화"""
        try:
            # 기본 설정 가져오기
            import importlib
            import config.model_setting
            importlib.reload(config.model_setting)
            
            default_settings = config.model_setting.ALGORITHM_PARAMETER.get(algo_name, {})
            
            # UI 업데이트
            if algo_name in self.inputs:
                for param_name, param_value in default_settings.items():
                    if param_name in self.inputs[algo_name]:
                        input_widget = self.inputs[algo_name][param_name]
                        
                        if isinstance(input_widget, QCheckBox):
                            input_widget.setChecked(param_value)
                        elif isinstance(input_widget, QSpinBox):
                            input_widget.setValue(param_value)
                        elif isinstance(input_widget, QDoubleSpinBox):
                            input_widget.setValue(param_value)
                        else:
                            input_widget.setText(str(param_value))
            
            QMessageBox.information(self, "기본값 복원", f"{algo_name.upper()} 알고리즘의 설정이 기본값으로 복원되었습니다.")
            
        except Exception as e:
            print(f"기본값 복원 오류: {str(e)}")
            QMessageBox.warning(self, "기본값 복원 실패", f"오류: {str(e)}") 