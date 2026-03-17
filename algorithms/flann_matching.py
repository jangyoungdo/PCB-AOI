import cv2
import numpy as np
from models.algorithm_model import AlgorithmModel

class FlannMatching(AlgorithmModel):

    @classmethod
    def set_settings(cls, settings):
        """모델의 설정을 업데이트합니다."""
        cls.parameter_settings = settings

    @classmethod
    def get_settings(cls):
        return cls.parameter_settings
    
    @classmethod
    def inspect(cls, reference_image, target_image):
        """
        FLANN + SIFT 매칭
        매칭 성공 시 matching_rate (float)를 반환, 실패 시 None 반환
        """
        # SIFT 생성
        sift = cv2.SIFT_create()

        # 특징점 및 디스크립터 계산
        kp1, des1 = sift.detectAndCompute(reference_image, None)
        kp2, des2 = sift.detectAndCompute(target_image, None)

        # 만약 특징점이 하나도 없다면 매칭 불가
        if des1 is None or des2 is None:
            print("특징점을 찾지 못했습니다.")
            return None

        # FLANN 매칭
        index_params = dict(algorithm=1, trees=cls.parameter_settings["trees"])
        search_params = dict(checks=cls.parameter_settings["checks"])
        flann = cv2.FlannBasedMatcher(index_params, search_params)
        matches = flann.knnMatch(des1, des2, k=2)

        # 좋은 매칭만 선별
        good_matches = []
        for m, n in matches:
            if m.distance < 0.75 * n.distance:
                good_matches.append(m)

        total_matches = len(matches)
        good_match_count = len(good_matches)
        # good match rate 계산
        if total_matches > 0:
            matching_rate = (good_match_count / total_matches) * 100
        else:
            matching_rate = 0.0

        print(f"[FLANN] 전체 매칭 개수: {total_matches}")
        print(f"[FLANN] 좋은 매칭 개수: {good_match_count}")
        print(f"[FLANN] 좋은 매칭 비율: {matching_rate:.2f}%")
        
        result = matching_rate > cls.parameter_settings["matching_rate_threshold"]
        
        # 매칭 결과 시각화
        # result_image = cv2.drawMatches(reference_image, kp1, target_image, kp2, good_matches, None, flags=2)

        return matching_rate, result
    
