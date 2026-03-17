import cv2
import numpy as np
import os
from config.model_setting import ALGORITHM_PARAMETER
from algorithms.flann_matching import FlannMatching
from algorithms.orb_matching import ORBMatching
from algorithms.hsv_matching import HSVMatching
from algorithms.sift_matching import SiftMatching
from algorithms.template_matching import TemplateMatching
from utils.util_function import get_center_color

class InspectionTarget:
    """
    기존에 알고리즘 관리 객체로 생각하였으나 
    각 객체마다 생성해야 하는 한계가 있어 이를 알고리즘 관리에만 사용하는 것은 비효율적이라고 생각하여 
    해당 클래스를 검사 객체 클래스로 만드는 것으로 디자인 함
    해당 클래스는 검사 객체가 갖고 있어야 할 기본 정보를 모두 갖고 있어야 함
    해당 클래스의 목표는 해당 검사 객체의 모든 정보를 갖고 있는 것으로 함

    객체에 대한 정보는 영도가 알고 있기 때문에 영도가 instance를 추가하도록 하는게 좋을 듯
    """

    def __init__(self, name, x, y, w, h, reference_image, algorithms):
        """
        현재 알고리즘, 기준 데이터, 알고리즘 동작 결과 3개의 데이터를 가지고 있음
        이는 알고리즘 기준 필요한 정보를 모두 담고 있다고 생각됨
        추가적으로 roi_info, hsv 기준 데이터, inspection_target_id 정도가 필요할 것으로 예상 
        """
        self.name = name

        """get,set, update"""
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.reference_image = reference_image

        self.matching_algorithm = algorithms # 모델 리스트 넣는 구간        
        self.algorithm_result = {}

        self.offset_x = 0  # 오프셋 초기화
        self.offset_y = 0

        self.color = None  # HSV 검사를 위한 기준 색상

        """이름 확정"""

    @staticmethod
    def set_parameter():
        """알고리즘 파라미터 초기화"""
        print("\n=== 알고리즘 파라미터 초기화 ===")
        for algorithm, params in ALGORITHM_PARAMETER.items():
            if algorithm == "hsv":
                print(f"HSV 파라미터 설정: {params}")
                HSVMatching.set_settings(params)
            elif algorithm == "flann":
                FlannMatching.set_settings(params)
            elif algorithm == "sift":
                SiftMatching.set_settings(params)
            elif algorithm == "orb":
                ORBMatching.set_settings(params)
            elif algorithm == "template":
                TemplateMatching.set_settings(params)
        print("=== 초기화 완료 ===\n")

    def compare_images(self, target_image, algorithm):
        """
        파라미터로 지정한 알고리즘(문자열)에 따라 이미지를 매칭하고,
        매칭 정확도를 리턴하는 통합 메서드
        """
        try:
            # 이미지 유효성 검사
            if self.reference_image is None or target_image is None:
                print(f"[오류] {algorithm}: 이미지가 None입니다")
                return [0.0, 0.0, False] if algorithm == "hsv" else [0.0, False]
            
            if self.reference_image.size == 0 or target_image.size == 0:
                print(f"[오류] {algorithm}: 이미지가 비어있습니다")
                return [0.0, 0.0, False] if algorithm == "hsv" else [0.0, False]

            # 알고리즘별 처리 (기존 로직 유지)
            if algorithm == "hsv":
                return HSVMatching.inspect(self.reference_image, target_image)
            elif algorithm == "flann":
                result = FlannMatching.inspect(self.reference_image, target_image)
                return result if result is not None else [0.0, False]
            elif algorithm == "sift":
                result = SiftMatching.inspect(self.reference_image, target_image)
                return result if result is not None else [0.0, False]
            elif algorithm == "orb":
                result = ORBMatching.inspect(self.reference_image, target_image)
                return result if result is not None else [0.0, False]
            elif algorithm == "template":
                result = TemplateMatching.inspect(self.reference_image, target_image)
                return result if result is not None else [0.0, False]
            
        except Exception as e:
            print(f"[오류] {algorithm} 알고리즘 실행 중 오류 발생: {str(e)}")
            return [0.0, 0.0, False] if algorithm == "hsv" else [0.0, False]
    

    def run_algorithm(self, target_image):
        """
        running inspection 
        key : algorithm
        value : [result->bool, matching_rate->float]
        """
        self.algorithm_result = {alg: self.compare_images(target_image, alg) for alg in self.matching_algorithm}
    
    def call_result():
        """너가 원하는 데이터 적으셈"""
        """결과로는 
            - 모델 리스트와 모델 별 결과
                -> 통과 여부
                -> 정확도

            그렇다면 결과 이미지는 캡쳐본 위에 target ROI를 그리고 기존에
            해당 ROI 박스 클릭해서 마스크 결과 확인하듯 모델 별 결과를 확인할 수 있으면 좋을 듯  
        """

    def update_ROI(self, x, y, w, h, reference_image) :
        """
        타켓 영역 추출 메서드
        """
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.reference_image = reference_image
        self.color = get_center_color(reference_image)

    def update_name(self, name) :
        self.name = name

    def update_matching_algorithm(self, algorithms) :
        self.matching_algorithm = algorithms

    def get_reference_image(self) :
        return self.reference_image
    
    def set_offset(self, offset_x, offset_y):
        self.offset_x = offset_x
        self.offset_y = offset_y
        
    def get_absolute_coordinates(self):
        return {
            'x': self.x - self.offset_x,
            'y': self.y - self.offset_y,
            'width': self.w,
            'height': self.h
        }

    def update_algorithm_parameters(self):
        """
        알고리즘 파라미터 업데이트 (설정 변경 시 호출)
        """
        # algorithm_result 초기화
        self.algorithm_result = {}
        
        # 알고리즘 파라미터 재설정 (class method 호출)
        InspectionTarget.set_parameter()
        
        print(f"ROI '{self.name}'의 알고리즘 파라미터 업데이트 완료")

# 디버깅 용 코드가 더 있었으면 좋을 듯
