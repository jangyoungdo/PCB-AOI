import cv2
import numpy as np
from models.target import InspectionTarget
from config.model_setting import ALGORITHM_PARAMETER
from utils.util_function import crop_image
import json
from utils.json_utils import parse_json_safely

class InspectionTargetListManager:
    """
    검사 대상(InspectionTarget) 객체들을 관리하는 매니저 클래스입니다.
    검사 대상의 생성, 삭제, 수정 및 알고리즘 관리 등을 담당합니다.
    """
    def __init__(self):
        self._target_dict = {}
        self._last_id = 0  # 인스턴스별 ID 관리
        InspectionTarget.set_parameter()

    @property
    def target_list(self):
        """검사 대상 리스트를 반환합니다."""
        return self._target_dict
    
    def _print_all_targets(self, reason=""):
        """모든 검사 대상의 현재 상태를 출력합니다."""
        if reason:
            print(f"\n=== 전체 검사 대상 상태 ({reason}) ===")
        else:
            print("\n=== 전체 검사 대상 상태 ===")
        
        for i, target in self._target_dict.items():
            print(f"\n[검사 대상 id {i}/{len(self._target_dict)}]")
            print(f"이름: {target.name}")
            print(f"위치: ({target.x}, {target.y}, {target.w}, {target.h})")
            print(f"사용 알고리즘: {target.matching_algorithm}")
            print(f"알고리즘 결과: {target.algorithm_result}")
        print("=" * 40 + "\n")

    def get_next_id(self):
        self._last_id += 1
        return self._last_id
        
    def add_target(self, name, x, y, w, h, image, algorithms=["template"]):
        """검사 대상 추가"""
        print(f"\n=== ROI 추가: {name} ===")
        print(f"위치: ({x}, {y}), 크기: {w}x{h}")
        print(f"알고리즘: {algorithms}")
        
        target_id = self.get_next_id()
        valid_algorithms = [alg for alg in algorithms if alg in ALGORITHM_PARAMETER.keys()]
        
        if image is None:
            print("경고: 이미지가 None입니다")
            return None
        
        reference_image = crop_image(image, x, y, w, h)
        if reference_image is None:
            print("경고: 참조 이미지 생성 실패")
            return None
        
        self._target_dict[target_id] = InspectionTarget(
            name, x, y, w, h, reference_image, valid_algorithms
        )
        
        print(f"ROI 추가 완료 - 총 {len(self._target_dict)}개")
        return target_id
    
    def remove_target(self, index):
        """지정된 인덱스의 검사 대상을 삭제합니다."""
        if index in self._target_dict:
            removed = self._target_dict.pop(index)
            self._print_all_targets("검사 대상 제거")
            return removed
        return None
    
    def update_target(self, index, **kwargs):
        """검사 대상 정보를 업데이트합니다."""
        if 0 <= index < len(self._target_dict):
            target = self._target_dict[index]
            changed = False
            for key, value in kwargs.items():
                if hasattr(target, key) and getattr(target, key) != value:
                    setattr(target, key, value)
                    changed = True
            if changed:
                self._print_all_targets("검사 대상 업데이트")
            return target
        return None
    
    def get_target(self, index):
        """지정된 인덱스의 검사 대상을 반환합니다."""
        if 0 <= index < len(self._target_dict):
            return self._target_dict[index]
        return None
    
    def clear(self):
        """모든 검사 대상을 삭제"""
        print("모든 ROI 초기화")
        self._target_dict.clear()
    
    def load_targets(self, target_list):
        """검사 대상 리스트를 로드합니다."""
        self._target_dict = target_list.copy()
    
    def run_inspection(self, id, target_image):
        """모든 검사 대상에 대해 검사를 실행합니다."""
        try:
            results = []
            target = self._target_dict.get(id)
            
            if target is None:
                print(f"[오류] ID {id}에 해당하는 검사 대상을 찾을 수 없습니다.")
                return results
            
            if target_image is None or target_image.size == 0:
                print("[오류] 유효하지 않은 타겟 이미지")
                return results
            
            # 알고리즘 실행
            target.run_algorithm(target_image)
            
            # 결과 구조 수정
            results.append({
                'name': target.name,
                'roi_name': target.name,
                'roi_id': id,
                'results': target.algorithm_result
            })
            
            return results
            
        except Exception as e:
            print(f"[오류] 검사 실행 중 오류 발생: {str(e)}")
            return []
    
    def add_algorithm_to_target(self, index, algorithm):
        """특정 검사 대상에 알고리즘을 추가합니다."""
        if algorithm not in self.SUPPORTED_ALGORITHMS:
            return False
            
        target = self.get_target(index)
        if target and algorithm not in target.matching_algorithm:
            target.matching_algorithm.append(algorithm)
            self._print_all_targets(f"알고리즘 추가: {algorithm}")
            return True
        return False
    
    def remove_algorithm_from_target(self, index, algorithm):
        """특정 검사 대상에서 알고리즘을 제거합니다."""
        target = self.get_target(index)
        if target and algorithm in target.matching_algorithm:
            target.matching_algorithm.remove(algorithm)
            self._print_all_targets(f"알고리즘 제거: {algorithm}")
            return True
        return False 
    
    def clear_targets(self):
        """모든 타겟 초기화"""
        self.target_list.clear()
    
    def clear_and_load_settings(self, roi_settings):
        """제품 변경 시 ROI 설정을 초기화하고 새로 로드"""
        self.clear()
        if not roi_settings:
            return
        
        try:
            settings = parse_json_safely(roi_settings, {})
            if settings and 'roi_list' in settings:
                for roi in settings['roi_list']:
                    self.add_target(
                        name=roi['name'],
                        x=roi['x'],
                        y=roi['y'],
                        w=roi['w'],
                        h=roi['h']
                    )
        except Exception as e:
            print(f"ROI 설정 로드 중 오류: {e}")
    
    def validate_targets(self):
        """검사 대상의 유효성을 검증"""
        if not self._target_dict:
            return False, "검사 대상이 없습니다."
        
        for target_id, target in self._target_dict.items():
            if not hasattr(target, 'reference_image') or target.reference_image is None:
                return False, f"ROI '{target.name}'의 참조 이미지가 없습니다."
            if not target.matching_algorithm:
                return False, f"ROI '{target.name}'의 매칭 알고리즘이 설정되지 않았습니다."
        
        return True, "검증 성공"
    
    def update_algorithm_parameters(self):
        """
        알고리즘 파라미터 업데이트 (설정 변경 후 호출)
        """
        from config.model_setting import ALGORITHM_PARAMETER
        
        # ROI가 없는 경우 무시
        if not self.target_list:
            return
        
        # 각 ROI 객체에 최신 설정 알림
        for target_id, target in self.target_list.items():
            if hasattr(target, 'update_algorithm_parameters'):
                target.update_algorithm_parameters()
        
        print("알고리즘 파라미터 업데이트 완료")
    
    