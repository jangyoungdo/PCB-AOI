import cv2
import numpy as np
from models.algorithm_model import AlgorithmModel

class ORBMatching(AlgorithmModel):

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
        ORB + BF 매칭
        매칭 성공 시 matching_rate (float)를 반환, 실패 시 None 반환
        """

        # ORB 생성
        orb = cv2.ORB_create(
            nfeatures=cls.parameter_settings["n_features"],
            scaleFactor=cls.parameter_settings["scale_factor"]
        )

        kp1, des1 = orb.detectAndCompute(reference_image, None)
        kp2, des2 = orb.detectAndCompute(target_image, None)

        if des1 is None or des2 is None:
            print("특징점을 찾지 못했습니다.")
            return None

        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(des1, des2)
        matches = sorted(matches, key=lambda x: x.distance)

        total_matches = len(matches)
        # 상위 10%만 good match로 판단(예시)
        top_n = int(total_matches * 0.1)
        good_matches = matches[:top_n] if top_n > 0 else []
        good_match_count = len(good_matches)

        if total_matches > 0:
            matching_rate = (good_match_count / total_matches) * 100
        else:
            matching_rate = 0.0

        print(f"[ORB] 전체 매칭 개수: {total_matches}")
        print(f"[ORB] 상위 매칭 개수: {good_match_count}")
        print(f"[ORB] 상위 매칭 비율: {matching_rate:.2f}%")

        result = matching_rate
        # 매칭 결과 시각화
        # result_image = cv2.drawMatches(reference_image, kp1, target_image, kp2, good_matches, None, flags=2)
        
        result = matching_rate > cls.parameter_settings["matching_rate_threshold"]
        return matching_rate, result