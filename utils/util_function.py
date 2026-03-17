def crop_image(image, x, y, w, h):
    """
        전체 이미지에서 ROI 영역을 추출하여 reference_image로 저장
    """
    # ROI 영역 추출
    cropped_image = image[y:y+h, x:x+w]

    return cropped_image


def get_center_color(image):
    
    height, width = image.shape[:2]
    center_y = height // 2
    center_x = width // 2
    
    center_color = image[center_y, center_x]
    
    return center_color