from ultralytics.data.utils import visualize_image_annotations
from ultralytics.nn.autobackend import check_class_names


def get_classnames():
    return ['AppleGreenHalf', 'AppleGreenWhole', 'BananaHalf', 'BananaWhole', 
            'CoconutHalf', 'CoconutWhole', 'KiwifruitHalf', 'KiwifruitWhole', 
            'LemonHalf', 'LemonWhole', 'MangoHalf', 'MangoWhole', 
            'OrangeHalf', 'OrangeWhole', 'PeachHalf', 'PeachWhole', 
            'PineappleHalf', 'PineappleWhole', 'WatermelonHalf', 'WatermelonWhole', 
            'bomb']

names = check_class_names(get_classnames())

# Call the visualization function
visualize_image_annotations(r"D:\FruitNinjaDataset\YOLOformat\images\test\img4.png", r"D:\FruitNinjaDataset\YOLOformat\labels\test\img4.txt", names)
