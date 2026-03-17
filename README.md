<div align="center">

# 🔍 PCB-AOI System
**PCB 부품 배치 검출 및 자동화 품질 검사 시스템**

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PyQt5](https://img.shields.io/badge/PyQt5-GUI-41CD52?style=for-the-badge&logo=qt&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-Vision-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white)
![YOLOv8](https://img.shields.io/badge/YOLOv8-Deep%20Learning-00FFFF?style=for-the-badge&logo=yolo&logoColor=black)

수동 검사 공정의 한계를 극복하고, 고속 공정 환경에서 신속·정확한 품질 판정을 내리기 위해 개발된<br>
**비전 기반 자동 광학 검사(AOI) 소프트웨어**입니다.<br>
*(주)이원테크놀러지 외주 연계 프로젝트*

<img src="https://via.placeholder.com/800x450/f5f5f5/333333?text=Insert+Your+UI+Screenshot+Here" alt="PCB-AOI UI Screenshot" width="800">

</div>

<br>

## 📋 1. 프로젝트 개요
* **수행 기간**: 2024.01 ~ 2024.02
* **수행 방식**: (주)이원테크놀러지 외주 연계 및 현대오토에버 모빌리티 SW 스쿨 실무 프로젝트
* **핵심 역할**: 응용 소프트웨어 메인 개발, 비전 알고리즘 모듈화 설계, PyQt5 UI/UX 리팩토링

---

## 🚀 2. 주요 특징 (Key Features)

### 🔍 3단계 하이브리드 교차 검증 (Hybrid Inspection)
단일 알고리즘의 한계를 극복하기 위해 세 가지 기술을 순차적으로 적용하여 **검출 신뢰도 99% 이상**을 확보했습니다.
1. **HSV 색상 매칭**: 부품의 고유 색상 영역 분석으로 결측 및 오염 1차 필터링
2. **이미지 차분 & Template Matching**: 기준 이미지와의 기하학적 차이 분석으로 부품 뒤틀림 및 오차 검출
3. **YOLO v8 객체 검출**: 딥러닝 모델을 통한 최종 다중 검증으로 오검출 제로화

### 🛠 객체지향 기반의 유연한 아키텍처 (OOP Design)
* **검사 로직 모듈화**: `InspectionTarget` 클래스를 설계하여 신규 PCB 모델이나 부품 추가 시 코드 수정 없이 유연하게 대응
* **동적 ROI 관리**: 검사 영역(ROI)을 GUI 상에서 실시간으로 설정하고 JSON 형태로 직렬화하여 자동 저장 및 관리

### 👤 현장 수용성 최적화 UI/UX
* **작업자 중심 대시보드**: 복잡한 디버깅 로그 대신 **Pass/Fail 대형 컬러 인디케이터**와 시각적 판정 결과를 배치하여 작업자 인지 부하 최소화
* **공정 표준 택타임(T/T) 100% 준수**: 직관적인 인터페이스로 현장 작업자의 즉각적인 불량 대응 지원

---

## 💻 3. 기술 스택 (Tech Stack)
| 분류 | 상세 기술 | 적용 목적 |
| :--- | :--- | :--- |
| **Language** | Python 3.9+ | 시스템 범용성 및 라이브러리 호환성 확보 |
| **GUI** | PyQt5 | 실시간 스트리밍 모니터링 및 설정 UI 구축 |
| **Vision** | OpenCV, YOLO v8 | 색상/기하학적 분석 및 딥러닝 기반 객체 탐지 |
| **Data** | SQLite, JSON | ROI 설정값 DB화 및 결과값 직렬화 |

---

## 📂 4. 프로젝트 구조 (Project Structure)
```text
├── algorithms/           # 비전 검사 알고리즘 (HSV, SIFT, Template Matching 등)
├── manager/              # 카메라 제어, DB 관리, 타겟 객체 관리 모듈
├── models/               # 알고리즘 및 검사 대상(InspectionTarget) 데이터 모델
├── ui/                   # PyQt5 기반 메인 윈도우 및 대시보드 레이아웃
├── utils/                # JSON 처리 및 좌표 변환 유틸리티
└── main.py               # 어플리케이션 실행 엔트리 포인트
