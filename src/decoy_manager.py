# decoy_manager.py
import pygame
import os
import random
from PIL import Image

# --- GLOBAL DECOYS ---
LOADED_DECOYS = {}

# --- CORE IMAGE PROCESSING HELPERS ---
# Các hàm này được sao chép từ enemy_manager để hoạt động độc lập.
# Trong một dự án lớn hơn, chúng có thể được đưa vào một file helper chung.

def _detect_sprite_frames(image_path):
    """
    Tự động phát hiện số frame trong sprite sheet (phiên bản helper).
    """
    try:
        img = Image.open(image_path)
        width, height = img.size
        
        if width > height * 1.5:
            frame_height = height
            frame_width = height
            num_frames = width // frame_width
            sheet_type = "horizontal"
        elif height > width * 1.5:
            frame_width = width
            frame_height = width
            num_frames = height // frame_height
            sheet_type = "vertical"
        else:
            frame_width = width
            frame_height = height
            num_frames = 1
            sheet_type = "single"
        
        print(f"     - Image size: {width}x{height}px")
        print(f"     - Type: {sheet_type}")
        print(f"     - Calculated: {num_frames} frames of {frame_width}x{frame_height}px each")
        
        return num_frames, frame_width, frame_height, sheet_type
    except Exception as e:
        print(f"  ⚠️ Could not auto-detect frames for {image_path}: {e}")
        return 1, 32, 32, "single"

def _crop_transparent_borders(surface):
    """
    Tự động crop phần trong suốt xung quanh sprite (phiên bản helper).
    """
    rect = surface.get_bounding_rect()
    if rect.width == 0 or rect.height == 0:
        return surface
    return surface.subsurface(rect).copy()

def _auto_detect_ground_position(frame):
    """
    Tự động tìm vị trí "chân" của sprite (phiên bản helper).
    """
    width, height = frame.get_size()
    for y in range(height - 1, -1, -1):
        for x in range(width):
            if frame.get_at((x, y)).a > 10:
                return -(height - y - 1)
    return 0

# --- MAIN LOADER FOR DECOYS ---
def load_decoys():
    """
    🚀 TỰ ĐỘNG LOAD TẤT CẢ DECOY SPRITES
    - Quét thư mục 'assets/decoys'
    - Tự động phát hiện, crop, và căn chỉnh sprites.
    """
    print("\n🌿 Auto-discovering decoy sprites...")
    
    decoys_dir = "assets/decoys"
    
    if not os.path.exists(decoys_dir):
        print(f"  ⚠️ Directory '{decoys_dir}' not found. Creating it...")
        os.makedirs(decoys_dir)
        print(f"  ℹ️ Please add decoy sprite sheets to '{decoys_dir}/'")
        return

    decoy_files = [f for f in os.listdir(decoys_dir) if f.endswith('.png')]
    
    if not decoy_files:
        print(f"  ℹ️ No decoy sprites found in '{decoys_dir}/'")
        return

    if not pygame.display.get_surface():
        print("  ⚠️ WARNING: No display surface! Creating dummy surface...")
        pygame.display.set_mode((1, 1))

    for filename in decoy_files:
        filepath = os.path.join(decoys_dir, filename)
        decoy_name = os.path.splitext(filename)[0]
        
        print(f"\n  -> Loading decoy: '{decoy_name}' from '{filename}'")
        
        num_frames, frame_width, frame_height, sheet_type = _detect_sprite_frames(filepath)
        
        try:
            spritesheet = pygame.image.load(filepath).convert_alpha()
            frames, cropped_frames = [], []
            
            for i in range(num_frames):
                if sheet_type == "horizontal": x_pos, y_pos = i * frame_width, 0
                elif sheet_type == "vertical": x_pos, y_pos = 0, i * frame_height
                else: x_pos, y_pos = 0, 0
                
                if x_pos + frame_width > spritesheet.get_width() or y_pos + frame_height > spritesheet.get_height():
                    break
                
                rect = pygame.Rect(x_pos, y_pos, frame_width, frame_height)
                frame = spritesheet.subsurface(rect).copy()
                cropped = _crop_transparent_borders(frame)
                cropped_frames.append(cropped)
            
            if not cropped_frames:
                print(f"     ✗ No frames extracted!")
                continue
            
            auto_y_offset = _auto_detect_ground_position(cropped_frames[0])
            
            LOADED_DECOYS[decoy_name] = {
                'frames': cropped_frames,
                'frame_width': cropped_frames[0].get_width(),
                'frame_height': cropped_frames[0].get_height(),
                'num_frames': len(cropped_frames),
                'animation_speed': 200,  # Default speed for decoys
                'auto_y_offset': auto_y_offset
            }
            
            print(f"     ✓ Loaded {len(cropped_frames)} frames")
            print(f"       Cropped size: {cropped_frames[0].get_width()}x{cropped_frames[0].get_height()}px")
            print(f"       Auto Y-offset: {auto_y_offset}px")
            
        except Exception as e:
            print(f"     ✗ Unexpected error: {e}")

    print(f"\n✓ Decoy loading complete. Loaded {len(LOADED_DECOYS)} decoy types.")
    if LOADED_DECOYS:
        print("\n📋 Available decoys:")
        for name, data in LOADED_DECOYS.items():
            print(f"   - {name}: {data['num_frames']} frames")


# --- GETTER FUNCTIONS ---
def get_random_decoy():
    """Lấy ngẫu nhiên một decoy type"""
    if not LOADED_DECOYS:
        return None
    return random.choice(list(LOADED_DECOYS.keys()))

def get_decoy_data(decoy_name):
    """Lấy thông tin của một decoy cụ thể"""
    return LOADED_DECOYS.get(decoy_name)

# --- CONFIG TÙY CHỈNH (OPTIONAL) ---
DECOY_CONFIGS = {
    'treasure_chest': {
        'animation_speed': 300, 
        'scale': 0.9,
        # Nếu chest không có animation, đặt là True để nó không lặp
        'use_static_frame': True 
    },
    'fake_wall': {
        'scale': 1.0,
        'use_static_frame': True
    },
    'animated_torch': {
        'animation_speed': 120,
        'use_static_frame': False # Cho phép lửa cháy
    }
}

def get_decoy_config(decoy_name):
    """
    Lấy config cho decoy, ưu tiên config thủ công.
    """
    decoy_data = get_decoy_data(decoy_name)
    
    default_config = {
        'scale': 1.0,
        'animation_speed': decoy_data.get('animation_speed', 200) if decoy_data else 200,
        'y_offset': decoy_data.get('auto_y_offset', 0) if decoy_data else 0,
        'use_static_frame': False
    }
    
    manual_config = DECOY_CONFIGS.get(decoy_name, {})
    default_config.update(manual_config)
    
    return default_config