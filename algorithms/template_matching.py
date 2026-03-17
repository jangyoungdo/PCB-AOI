import cv2
import numpy as np
from models.algorithm_model import AlgorithmModel

class TemplateMatching(AlgorithmModel):

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
        템플릿 매칭
        - 템플릿이 몇 개 위치에서 성공적으로 매칭되는지 세어서 (찾은 개수 / 1) * 100 으로 환산 예시
        - 매칭 성공 시 matching_rate (float)를 반환, 매칭 실패(없음) 시 0.0 반환
        """

        pcb_gray = cv2.cvtColor(target_image, cv2.COLOR_BGR2GRAY)
        template_gray = cv2.cvtColor(reference_image, cv2.COLOR_BGR2GRAY)
        result = cv2.matchTemplate(pcb_gray, template_gray, cls.parameter_settings["method"])
        locations = np.where(result >= cls.parameter_settings["threshold"])

        matches_found = False
        match_count = 0
        for pt in zip(*locations[::-1]):  # x, y 좌표 변환
            matches_found = True
            match_count += 1
            cv2.rectangle(
                target_image,
                pt,
                (pt[0] + reference_image.shape[1], pt[1] + reference_image.shape[0]),
                (0, 255, 0),
                2
            )
            print(f"매칭된 위치: (x={pt[0]}, y={pt[1]})")

        if not matches_found:
            print("매칭된 영역이 없습니다.")
            matching_rate = 0.0
        else:
            # 예시로, '매칭된 박스가 1개 이상이면 100%, 없으면 0%' 라고 가정
            # 혹은 match_count * 10 등 원하는 계산법으로 수정 가능
            matching_rate = 100.0

        print(f"[TEMPLATE] 매칭 박스 개수: {match_count}")
        print(f"[TEMPLATE] 매칭 비율: {matching_rate:.2f}%")

        result = matching_rate > cls.parameter_settings["matching_rate_threshold"]
        return matching_rate, result