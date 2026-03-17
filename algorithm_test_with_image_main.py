from manager.target_manager import InspectionTargetListManager
from utils.util_function import crop_image
import cv2

def main():
    image_path1 = "./resource/back_pcb_unBlocked_1.png"
    image_path2 = "./resource/back_pcb_unBlocked_4.png"
    image = cv2.imread(image_path1)

    inspector = InspectionTargetListManager()
    inspector.add_target("PART1", 486, 310, 72, 67, image, ["sift", "hsv", "orb"])
    inspector.add_target("PART2", 338, 351, 42, 35, image, ["sift", "hsv"])
    inspector.add_target("PART3", 338, 249, 44, 39, image, ["sift", "hsv"])
    inspector.add_target("PART4", 289, 252, 45, 44, image, ["sift", "hsv"])

    image = cv2.imread(image_path2)

    result = inspector.run_inspection(1, crop_image(image, 486, 310, 72, 67))
    print(result)

main()