import json

def parse_json_safely(json_str, default=None):
    """JSON 문자열을 안전하게 파싱하는 유틸리티 함수
    
    Args:
        json_str: 파싱할 JSON 문자열
        default: 파싱 실패 시 반환할 기본값
    
    Returns:
        파싱된 객체 또는 default 값
    """
    if not json_str:
        return default
    
    try:
        # 이중 인코딩 문제 처리
        if isinstance(json_str, str) and json_str.startswith('"') and json_str.endswith('"'):
            try:
                # 첫 번째 파싱 - 바깥쪽 따옴표 제거
                decoded_json = json.loads(json_str)
                
                # 두 번째 파싱 - 내부 문자열이 JSON인 경우
                if isinstance(decoded_json, str):
                    try:
                        return json.loads(decoded_json)
                    except:
                        return decoded_json
                return decoded_json
            except:
                # 원본 문자열로 다시 시도
                return json.loads(json_str)
        else:
            # 일반적인 JSON 문자열
            return json.loads(json_str)
    except Exception as e:
        print(f"JSON 파싱 오류: {str(e)}")
        if len(str(json_str)) > 100:
            print(f"문제 데이터(일부): {str(json_str)[:100]}...")
        else:
            print(f"문제 데이터: {json_str}")
        return default

def serialize_json_safely(obj, ensure_ascii=False):
    """객체를 JSON 문자열로 안전하게 직렬화하는 유틸리티 함수
    
    Args:
        obj: 직렬화할 객체
        ensure_ascii: ASCII 문자만 사용할지 여부
    
    Returns:
        JSON 문자열
    """
    try:
        return json.dumps(obj, ensure_ascii=ensure_ascii)
    except Exception as e:
        print(f"JSON 직렬화 오류: {str(e)}")
        return "{}"

def extract_roi_data(roi_results):
    """ROI 결과 데이터에서 필요한 정보를 추출하는 유틸리티 함수
    
    Args:
        roi_results: 파싱된 ROI 결과 객체
    
    Returns:
        튜플 (roi_name, results, is_fail, main_fail_algorithm)
    """
    # 기본값 설정
    roi_name = None
    results = {}
    is_fail = False
    main_fail_algorithm = None
    algorithm_results = {}
    
    # roi_name 추출
    if isinstance(roi_results, dict) and 'roi_name' in roi_results:
        roi_name = roi_results['roi_name']
    
    # results 필드 추출 및 처리
    if isinstance(roi_results, dict) and 'results' in roi_results:
        results_value = roi_results['results']
        
        # results가 문자열인 경우 추가 파싱
        if isinstance(results_value, str):
            try:
                results = parse_json_safely(results_value, {})
            except:
                results = {}
        else:
            results = results_value
    
    # 결과가 딕셔너리가 아니면 빈 딕셔너리 반환
    if not isinstance(results, dict):
        return roi_name, {}, is_fail, main_fail_algorithm
    
    # 알고리즘 결과 처리
    for algo_name, algo_result in results.items():
        try:
            if isinstance(algo_result, list) and len(algo_result) >= 2:
                accuracy = algo_result[0]
                pass_result = algo_result[1]
                
                if not pass_result:  # 불합격인 경우
                    is_fail = True
                    if main_fail_algorithm is None or accuracy < algorithm_results.get(main_fail_algorithm, [100, True])[0]:
                        main_fail_algorithm = algo_name
                
                algorithm_results[algo_name] = [accuracy, pass_result]
        except Exception as algo_err:
            print(f"알고리즘 결과 처리 중 오류: {str(algo_err)}")
    
    return roi_name, results, is_fail, main_fail_algorithm 