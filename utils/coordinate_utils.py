def calculate_scaling_parameters(original_size, display_size):
    """원본 이미지 크기와 화면 크기에 따른 스케일링 매개변수 계산
    
    Args:
        original_size: 원본 이미지 크기 (width, height)
        display_size: 화면 표시 크기 (width, height)
        
    Returns:
        tuple: (scale_factor, offset_x, offset_y, new_width, new_height)
    """
    orig_w, orig_h = original_size
    disp_w, disp_h = display_size
    
    # 종횡비 계산
    orig_ratio = orig_w / orig_h
    disp_ratio = disp_w / disp_h
    
    if orig_ratio > disp_ratio:
        # 이미지가 더 넓은 경우
        new_w = disp_w
        new_h = int(disp_w / orig_ratio)
        scale_factor = disp_w / orig_w
        offset_x = 0
        offset_y = (disp_h - new_h) // 2
    else:
        # 이미지가 더 높은 경우
        new_h = disp_h
        new_w = int(disp_h * orig_ratio)
        scale_factor = disp_h / orig_h
        offset_x = (disp_w - new_w) // 2
        offset_y = 0
    
    return scale_factor, offset_x, offset_y, new_w, new_h

def screen_to_image(screen_x, screen_y, scale_factor, offset_x, offset_y):
    """화면 좌표를 이미지 좌표로 변환
    
    Args:
        screen_x, screen_y: 화면 좌표
        scale_factor: 스케일링 인자
        offset_x, offset_y: 이미지 오프셋
        
    Returns:
        tuple: (img_x, img_y) - 이미지 좌표
    """
    img_x = (screen_x - offset_x) / scale_factor
    img_y = (screen_y - offset_y) / scale_factor
    return int(img_x), int(img_y)

def image_to_screen(img_x, img_y, scale_factor, offset_x, offset_y):
    """이미지 좌표를 화면 좌표로 변환
    
    Args:
        img_x, img_y: 이미지 좌표
        scale_factor: 스케일링 인자
        offset_x, offset_y: 이미지 오프셋
        
    Returns:
        tuple: (screen_x, screen_y) - 화면 좌표
    """
    screen_x = int(img_x * scale_factor) + offset_x
    screen_y = int(img_y * scale_factor) + offset_y
    return screen_x, screen_y 