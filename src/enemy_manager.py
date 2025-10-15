# enemy_manager.py
import pygame
import json
import os
import random
from PIL import Image

# --- GLOBAL ENEMIES ---
LOADED_ENEMIES = {}

def detect_sprite_frames(image_path):
    """
    Tự động phát hiện số frame trong sprite sheet
    Hỗ trợ nhiều loại sprite sheet:
    - Ngang (horizontal): width > height
    - Dọc (vertical): height > width  
    - Grid: width ≈ height
    """
    try:
        img = Image.open(image_path)
        width, height = img.size
        
        # Phát hiện kiểu sprite sheet
        if width > height * 1.5:
            # Sprite sheet ngang
            frame_height = height
            frame_width = height  # Giả định frame vuông
            num_frames = width // frame_width
            sheet_type = "horizontal"
        elif height > width * 1.5:
            # Sprite sheet dọc
            frame_width = width
            frame_height = width  # Giả định frame vuông
            num_frames = height // frame_height
            sheet_type = "vertical"
        else:
            # Grid hoặc single frame
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

def crop_transparent_borders(surface):
    """
    🔥 Tự động crop phần trong suốt xung quanh sprite
    Loại bỏ khoảng trống để sprite không bị "nhảy"
    """
    rect = surface.get_bounding_rect()
    
    # Nếu không có gì để crop
    if rect.width == 0 or rect.height == 0:
        return surface
    
    # Crop chính xác phần có nội dung
    cropped = surface.subsurface(rect).copy()
    return cropped

def auto_detect_ground_position(frame):
    """
    🔥 TỰ ĐỘNG TÌM VỊ TRÍ "CHÂN" CỦA SPRITE
    Quét từ dưới lên để tìm pixel đầu tiên không trong suốt
    Trả về offset cần thiết để sprite đứng đúng mặt đất
    """
    width, height = frame.get_size()
    
    # Quét từ dưới lên, từ trái sang phải
    for y in range(height - 1, -1, -1):
        for x in range(width):
            # Lấy alpha channel
            alpha = frame.get_at((x, y)).a
            if alpha > 10:  # Ngưỡng để bỏ qua pixel gần như trong suốt
                # Tìm thấy pixel đầu tiên, tính offset
                offset = height - y - 1
                return -offset  # Số âm để đẩy sprite xuống
    
    return 0  # Không tìm thấy, không offset

def load_enemies():
    """
    🚀 TỰ ĐỘNG LOAD TẤT CẢ ENEMY SPRITES
    - Tự động phát hiện số frame
    - Tự động crop phần trong suốt
    - Tự động tìm vị trí chân để đứng đúng mặt đất
    - Không cần config JSON phức tạp!
    """
    print("👾 Auto-discovering enemy sprites...")
    
    enemies_dir = "assets/enemies"
    
    if not os.path.exists(enemies_dir):
        print(f"  ⚠️ Directory '{enemies_dir}' not found. Creating it...")
        os.makedirs(enemies_dir)
        print(f"  ℹ️ Please add enemy sprite sheets to '{enemies_dir}/'")
        return
    
    enemy_files = [f for f in os.listdir(enemies_dir) if f.endswith('.png')]
    
    if not enemy_files:
        print(f"  ℹ️ No enemy sprites found in '{enemies_dir}/'")
        return
    
    # Đảm bảo pygame display đã init
    if not pygame.display.get_surface():
        print("  ⚠️ WARNING: No display surface! Creating dummy surface...")
        pygame.display.set_mode((1, 1))
    
    for filename in enemy_files:
        filepath = os.path.join(enemies_dir, filename)
        enemy_name = os.path.splitext(filename)[0]
        
        print(f"\n  -> Loading enemy: '{enemy_name}' from '{filename}'")
        
        # Tự động phát hiện cấu trúc sprite sheet
        num_frames, frame_width, frame_height, sheet_type = detect_sprite_frames(filepath)
        
        try:
            spritesheet = pygame.image.load(filepath).convert_alpha()
            
            frames = []
            cropped_frames = []
            
            # Cắt frame dựa trên loại sprite sheet
            for i in range(num_frames):
                if sheet_type == "horizontal":
                    x_pos = i * frame_width
                    y_pos = 0
                elif sheet_type == "vertical":
                    x_pos = 0
                    y_pos = i * frame_height
                else:  # single
                    x_pos = 0
                    y_pos = 0
                
                # Check bounds
                if x_pos + frame_width > spritesheet.get_width() or \
                   y_pos + frame_height > spritesheet.get_height():
                    print(f"     ⚠️ Frame {i} out of bounds, stopping")
                    break
                
                rect = pygame.Rect(x_pos, y_pos, frame_width, frame_height)
                frame = spritesheet.subsurface(rect).copy()
                frames.append(frame)
                
                # 🔥 CROP PHẦN TRONG SUỐT
                cropped = crop_transparent_borders(frame)
                cropped_frames.append(cropped)
            
            if not cropped_frames:
                print(f"     ✗ No frames extracted!")
                continue
            
            # 🔥 TỰ ĐỘNG TÌM VỊ TRÍ CHÂN (dùng frame đầu tiên làm reference)
            auto_y_offset = auto_detect_ground_position(cropped_frames[0])
            
            # Lưu vào dictionary
            LOADED_ENEMIES[enemy_name] = {
                'frames': cropped_frames,
                'original_frames': frames,  # Giữ frame gốc nếu cần
                'frame_width': cropped_frames[0].get_width(),
                'frame_height': cropped_frames[0].get_height(),
                'num_frames': len(cropped_frames),
                'animation_speed': 150,  # Default
                'auto_y_offset': auto_y_offset  # 🔥 Offset tự động
            }
            
            print(f"     ✓ Loaded {len(cropped_frames)} frames")
            print(f"       Cropped size: {cropped_frames[0].get_width()}x{cropped_frames[0].get_height()}px")
            print(f"       Auto Y-offset: {auto_y_offset}px")
            
        except pygame.error as e:
            print(f"     ✗ Error loading sprite: {e}")
        except Exception as e:
            print(f"     ✗ Unexpected error: {e}")
    
    print(f"\n✓ Enemy loading complete. Loaded {len(LOADED_ENEMIES)} enemy types.")
    
    if LOADED_ENEMIES:
        print(f"\n📋 Available enemies:")
        for name, data in LOADED_ENEMIES.items():
            print(f"   - {name}: {data['num_frames']} frames, " +
                  f"{data['frame_width']}x{data['frame_height']}px, " +
                  f"offset: {data['auto_y_offset']}px")

def get_random_enemy():
    """Lấy ngẫu nhiên một enemy type"""
    if not LOADED_ENEMIES:
        return None
    return random.choice(list(LOADED_ENEMIES.keys()))

def get_enemy_data(enemy_name):
    """Lấy thông tin của một enemy cụ thể"""
    return LOADED_ENEMIES.get(enemy_name)

# 🔥 CONFIG TÙY CHỈNH (OPTIONAL)
# Chỉ cần thêm vào đây nếu muốn override giá trị tự động
ENEMY_CONFIGS = {
    # Ví dụ: Nếu auto-detect không chính xác cho 'worm'
    # 'worm': {
    #     'scale': 0.6,
    #     'animation_speed': 140,
    #     'y_offset': -20,  # Override auto_y_offset
    #     'use_static_frame': False
    # },
    
    # Hoặc nếu muốn wizard đứng yên
    # 'wizard': {
    #     'use_static_frame': True
    # }
}

def get_enemy_config(enemy_name):
    """
    Lấy config cho enemy, ưu tiên:
    1. Config thủ công trong ENEMY_CONFIGS
    2. Config tự động từ phát hiện sprite
    """
    # Lấy data tự động
    enemy_data = get_enemy_data(enemy_name)
    
    # Config mặc định từ auto-detect
    default_config = {
        'scale': 1.0,
        'animation_speed': enemy_data.get('animation_speed', 150) if enemy_data else 150,
        'y_offset': enemy_data.get('auto_y_offset', 0) if enemy_data else 0,
        'use_static_frame': False
    }
    
    # Override bằng config thủ công nếu có
    manual_config = ENEMY_CONFIGS.get(enemy_name, {})
    default_config.update(manual_config)
    
    return default_config