import cv2
import numpy as np
import colorsys
from typing import Dict, List, Tuple, Any
from models.algorithm_model import AlgorithmModel
from utils.util_function import get_center_color

class HSVMatching(AlgorithmModel):
    
    @classmethod
    def set_settings(cls, settings):
        """모델의 설정을 업데이트합니다."""
        cls.parameter_settings = settings
        print(cls.parameter_settings)
    
    @classmethod
    def get_settings(cls):
        return cls.parameter_settings
    
    @classmethod
    def get_color_range(cls, color):
        print(f"\n[DEBUG] HSV 색상 범위 계산")
        print(f"기준 HSV 색상: {color}")
        print(f"파라미터 설정: {cls.parameter_settings}")  # 이 값이 어떻게 나오는지 확인
        
        h, s, v = color
        # offset을 채널별로 다르게 설정
        h_offset = cls.parameter_settings["h_offset"]  # 색상은 작은 범위
        s_offset = cls.parameter_settings["s_offset"]  # 채도는 더 넓은 범위
        v_offset = cls.parameter_settings["v_offset"]  # 명도도 더 넓은 범위
        
        h_min = max(0, h - h_offset)
        h_max = min(179, h + h_offset)
        s_min = max(0, s - s_offset)
        s_max = min(255, s + s_offset)
        v_min = max(0, v - v_offset)
        v_max = min(255, v + v_offset)
        
        # numpy 배열로 변환하고 uint8 타입 지정
        lower_bound = np.array([h_min, s_min, v_min], dtype=np.uint8)
        upper_bound = np.array([h_max, s_max, v_max], dtype=np.uint8)

        print(f"계산된 범위: {lower_bound} ~ {upper_bound}")
        return lower_bound, upper_bound

    @classmethod
    def inspect(cls, reference_image, target_image):
        print("\n[DEBUG] HSV 매칭 검사")
        print(f"레퍼런스 이미지 정보:")
        print(f"- 크기: {reference_image.shape if reference_image is not None else 'None'}")
        print(f"- 타입: {type(reference_image)}")
        print(f"- 데이터 범위: {reference_image.min()} ~ {reference_image.max()}")
        
        print(f"\n타겟 이미지 정보:")
        print(f"- 크기: {target_image.shape if target_image is not None else 'None'}")
        print(f"- 타입: {type(target_image)}")
        print(f"- 데이터 범위: {target_image.min()} ~ {target_image.max()}")
        
        center_color = get_center_color(reference_image)
        print(f"\n[DEBUG] 중심 BGR 색상: {center_color}")
        hsv_color = cv2.cvtColor(np.uint8([[center_color]]), cv2.COLOR_BGR2HSV)[0][0]
        print(f"[DEBUG] 변환된 HSV 색상: {hsv_color}")

        # 이미지 유효성 검사
        if reference_image is None or target_image is None:
            print("[오류] 이미지가 None입니다")
            return 0.0, 0.0, False
            
        if reference_image.size == 0 or target_image.size == 0:
            print("[오류] 이미지가 비어있습니다")
            return 0.0, 0.0, False
        
        hsv_reference_image = cv2.cvtColor(reference_image, cv2.COLOR_BGR2HSV)
        hsv_target_image = cv2.cvtColor(target_image, cv2.COLOR_BGR2HSV)

        lower_bound, upper_bound = cls.get_color_range(hsv_color)
        
        mask_ref = cv2.inRange(hsv_reference_image, lower_bound, upper_bound)
        mask_targ = cv2.inRange(hsv_target_image, lower_bound, upper_bound)
        
        # 마스크 결과 확인
        print(f"마스크 픽셀 수 - 레퍼런스: {cv2.countNonZero(mask_ref)}, 타겟: {cv2.countNonZero(mask_targ)}")
        print(f"전체 픽셀 수: {mask_ref.shape[0] * mask_ref.shape[1]}")
        
        total_pixels = mask_ref.shape[0] * mask_ref.shape[1]
        matching_rate_ref = cv2.countNonZero(mask_ref) / total_pixels
        matching_rate_targ = cv2.countNonZero(mask_targ) / total_pixels
        
        print(f"매칭 비율 - 레퍼런스: {matching_rate_ref:.4f}, 타겟: {matching_rate_targ:.4f}")
        
        result = matching_rate_ref < matching_rate_targ + cls.parameter_settings["matching_rate_threshold"]

        return matching_rate_ref, matching_rate_targ, result

