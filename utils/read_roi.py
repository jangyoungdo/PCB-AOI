import cv2

# 전역 변수 설정
drawing = False      # 드래그 중 여부
ix, iy = -1, -1      # 드래그 시작 좌표
image = None         # 원본 이미지
image_copy = None    # 사본 이미지 (실시간으로 사각형을 그리기 위함)

def mouse_callback(event, x, y, flags, param):
    global ix, iy, drawing, image, image_copy

    if event == cv2.EVENT_LBUTTONDOWN:
        # 마우스 왼쪽 버튼을 누르면 드래그 시작
        drawing = True
        ix, iy = x, y
        # 드래그 시작 시점의 이미지 복사본 생성
        image_copy = image.copy()

    elif event == cv2.EVENT_MOUSEMOVE:
        if drawing:
            # 드래그 중일 때 현재 위치까지 사각형 그리기
            image_copy = image.copy()  # 매번 새로 그리기 위해 원본을 복사
            cv2.rectangle(image_copy, (ix, iy), (x, y), (0, 255, 0), 2)
            cv2.imshow("Image", image_copy)

    elif event == cv2.EVENT_LBUTTONUP:
        # 마우스 왼쪽 버튼을 떼면 드래그 종료
        drawing = False
        # 최종 사각형 그리기
        cv2.rectangle(image_copy, (ix, iy), (x, y), (0, 255, 0), 2)
        cv2.imshow("Image", image_copy)
        
        # ROI 좌표 및 크기 계산 (왼쪽 상단 좌표, 너비, 높이)
        x0, y0 = min(ix, x), min(iy, y)
        width = abs(x - ix)
        height = abs(y - iy)
        print("선택한 ROI (x, y, width, height):", x0, y0, width, height)


# 이미지 파일 경로 (자신의 이미지 경로로 수정하세요)
image_path = "./resource/back_pcb_unBlocked_1.png"  
image = cv2.imread(image_path)
if image is None:
    print("이미지를 불러올 수 없습니다. 경로를 확인하세요!")
    exit()
# 초기 이미지 복사본 생성
image_copy = image.copy()
# 창 생성 및 마우스 콜백 함수 등록
cv2.namedWindow("Image")
cv2.setMouseCallback("Image", mouse_callback)
print("마우스로 드래그하여 ROI 영역을 선택하세요. 선택 후 ROI 값이 콘솔에 출력됩니다.")
print("종료하려면 ESC 키를 누르세요.")
while True:
    cv2.imshow("Image", image_copy)
    key = cv2.waitKey(1) & 0xFF
    if key == 27:  # ESC 키를 누르면 종료
        break
cv2.destroyAllWindows()