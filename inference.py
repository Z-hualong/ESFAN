import argparse
import os
import cv2
import numpy as np
from skimage import morphology
from tqdm import tqdm
import torch
from torchvision import transforms
from torch.utils.data import Dataset, DataLoader
from tool import seg_transformers as tr
from PIL import Image
import time
import segmentation_models_pytorch as smp
os.environ["CUDA_VISIBLE_DEVICES"] = "0,1"
def apply_color_map(pred):
    COLOR_MAP = {
        0: (205, 51, 51),  # TE
        1: (0, 255, 0),  # NEC
        2: (65, 105, 225),  # LYM
        3: (255, 165, 0),  # TAS
        4: (255, 255, 255)  # bg
    }
    color_pred = np.zeros((pred.shape[0], pred.shape[1], 3), dtype=np.uint8)
    for label, color in COLOR_MAP.items():
        color_pred[pred == label] = color
    return color_pred
class MultiPathDataset(Dataset):
    def __init__(self, img_files):
        self.img_files = img_files
    def __len__(self):
        return len(self.img_files)
    def __getitem__(self, index):
        img = Image.open(self.img_files[index]).convert('RGB')
        sample = {'image': img}
        composed_transforms = transforms.Compose([tr.Normalize(), tr.ToTensor()])
        return composed_transforms(sample), self.img_files[index]
def update_test_loader(parent_folder_path):
    img_folder = os.path.join(parent_folder_path, 'img')
    pred_folder = os.path.join(parent_folder_path, 'pred')
    if not os.path.exists(pred_folder):
        os.makedirs(pred_folder)
    img_paths = [os.path.join(img_folder, img) for img in os.listdir(img_folder) if img.endswith('.png')]
    dataset = MultiPathDataset(img_paths)
    data_loader = DataLoader(dataset, batch_size=1, shuffle=False)
    return data_loader

class Seg(object):
    def __init__(self, args):
        self.args = args
        self.nclass = args.n_class
        self.model = smp.PSPNet(encoder_name='timm-resnest200e', encoder_weights='imagenet', in_channels=3,
                           classes=self.nclass)
        if args.cuda:
            self.model = torch.nn.DataParallel(self.model).cuda()
    def load_the_best_checkpoint(self):
        checkpoint = torch.load('checkpoints/stage2_checkpoint_trained_on_'+self.args.dataset + '.pth')
        self.model.module.load_state_dict(checkpoint['state_dict'], strict=False)
    def gen_bg_mask(self, orig_img):
        img_array = (orig_img * 255).astype(np.uint8) if orig_img.dtype == np.float32 else orig_img.astype(np.uint8)
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        ret, binary = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        binary = np.uint8(binary)
        dst = morphology.remove_small_objects(binary == 255, min_size=10, connectivity=1)
        bg_mask = np.ones(orig_img.shape[:2]) * (-100.0)
        bg_mask[dst == True] = 100.0
        return bg_mask
    def seg(self, parent_folder_path):
        self.load_the_best_checkpoint()
        self.model.eval()
        test_loader = update_test_loader(parent_folder_path)
        img_folder = os.path.join(parent_folder_path, 'img')
        pred_folder = os.path.join(parent_folder_path, 'pred')
        overlay_folder = os.path.join(parent_folder_path, 'overlay')
        os.makedirs(pred_folder, exist_ok=True)
        os.makedirs(overlay_folder, exist_ok=True)
        img_files = [f for f in os.listdir(img_folder) if f.endswith('.png')]
        total_images_global = len(img_files)
        processed_count_global = 0
        start_time_global = time.time()
        print(f"Total images to process: {total_images_global}")
        with torch.no_grad():
            for i, (sample, img_paths) in enumerate(tqdm(test_loader, desc=f'Processing {parent_folder_path}')):
                image = sample['image']
                png_name = os.path.basename(img_paths[0]).split('.')[0]
                if self.args.cuda:
                    image = image.cuda()
                output = self.model(image)
                pred = output.data.cpu().numpy()
                pred = np.argmax(pred, axis=1)
                bg_mask = self.gen_bg_mask(image[0].cpu().numpy().transpose(1, 2, 0))
                bg_mask_bool = (bg_mask == 100)
                bg_mask_resized = cv2.resize(bg_mask_bool.astype(np.uint8), pred.shape[1:], interpolation=cv2.INTER_NEAREST)
                pred[0, bg_mask_resized == 1] = 4
                pred_img = apply_color_map(pred[0])
                pred_png = Image.fromarray(pred_img)
                savepath = os.path.join(pred_folder, f"{png_name}.png")
                pred_png.save(savepath)
                processed_count_global += 1
        elapsed_time_global = time.time() - start_time_global
        images_per_second = processed_count_global / elapsed_time_global
        print(f"Processed {processed_count_global}/{total_images_global} images.")
        print(f"Estimated remaining time: 0.00 minutes.")
        for img_file in img_files:
            img_path = os.path.join(img_folder, img_file)
            pred_path = os.path.join(pred_folder, img_file)
            overlay_savepath = os.path.join(overlay_folder, img_file)
            overlay_images(img_path, pred_path, overlay_savepath)
        print("All images processed.")
def overlay_images(img_path, pred_path, output_path):
    img = Image.open(img_path).convert("RGB")
    pred = Image.open(pred_path).convert("RGB")
    overlay = Image.blend(img, pred, alpha=0.5)
    overlay.save(output_path)
def main():
    parser = argparse.ArgumentParser(description="Seg")
    parser.add_argument('--dataset', type=str, default='luad')
    parser.add_argument('--n_class', type=int, default=4)
    parser.add_argument('--no-cuda', action='store_true', default=False)
    parser.add_argument('--gpu-ids', type=str, default='0')
    parser.add_argument('--sync-bn', type=bool, default=None)
    args = parser.parse_args()
    args.cuda = not args.no_cuda and torch.cuda.is_available()
    if args.cuda:
        args.gpu_ids = [int(s) for s in args.gpu_ids.split(',')]
    args.sync_bn = args.cuda and len(args.gpu_ids) > 1
    parent_folder_path = r"./datasets/LUAD-HistoSeg/train"
    trainer = Seg(args)
    trainer.seg(parent_folder_path)

if __name__ == "__main__":
   main()
