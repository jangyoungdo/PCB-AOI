from abc import ABC, abstractmethod
from typing import Any, Dict, List, Tuple
import numpy as np

class AlgorithmModel(ABC):
    """모든 검사 모델의 기본 클래스입니다."""
    parameter_settings = None
    
    @classmethod
    @abstractmethod
    def set_settings(cls, settings: Dict[str, Any]) -> None:
        """모델의 설정을 업데이트합니다."""
        cls.parameter_settings = settings

    @classmethod
    @abstractmethod
    def get_settings(cls):
        pass
    
    @classmethod
    @abstractmethod
    def inspect(cls, reference_image, target_image) :
        """검사를 수행하고 결과를 반환합니다."""
        pass


    