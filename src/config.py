# config.py - Background Configuration

# Screen settings
SCREEN_W = 1024
SCREEN_H = 768
FPS = 60

# Player settings
PLAYER_W = 22       # Giảm từ 25 -> 22 để người chơi lách dễ hơn
PLAYER_H = 36       # Giảm từ 40 -> 36 để dễ nhảy qua vật cản
JUMP_V = -20.5      # Tăng từ -18 -> -20.5 để nhảy cao hơn đáng kể
GRAVITY = 0.9       # Giữ nguyên để cảm giác rơi không thay đổi
RUN_SPEED = 3

# Game settings
GROUND_Y = 360
MAX_STEPS_PER_GENOME = 2000
DEFAULT_GENERATIONS = 40
DEFAULT_LEVEL = "level1.json"


# --- TILESET SETTINGS ---
# Tile rendering options

# Tile rendering options
TILE_SIZE = 16
TILE_SCALE = 1 # Thử giảm xuống 1.5 hoặc 2 xem sao

# Các preset vị trí tiles trong dungeon_tileset.png
TILE_PRESETS = {
    'grass_top': [(0, 7), (1, 7), (2, 7)],      # Platform có cỏ trên (đẹp hơn!)
    'solid_middle': [(0, 8), (1, 8), (2, 8)],   # Đất/tường giữa
    'bottom_platform': [(0, 19), (1, 19), (2, 19)], # Platform bottom
    'dark_ground': [(0, 9), (1, 9), (2, 9)],    # Ground tối màu
    'stone_platform': [(3, 7), (4, 7), (5, 7)], # Nền đá (nếu có)
}

# Chọn preset muốn dùng - THỬ 'grass_top' xem có đẹp hơn không
ACTIVE_TILE_PRESET = 'bottom_platform'  # Đổi sang grass_top để thử!

# ---------------------------------------------
# CẤU HÌNH BACKGROUND PARALLAX ĐA LỚP
# ---------------------------------------------
# Cấu hình này sẽ được áp dụng cho tất cả các màn chơi.
# Mỗi mục là một lớp của background.
# - "file": Đường dẫn đến file ảnh của lớp.
# - "speed": Tốc độ di chuyển (parallax).
#   + speed nhỏ hơn -> lớp ở xa hơn và di chuyển chậm hơn.
#   + speed lớn hơn -> lớp ở gần hơn và di chuyển nhanh hơn.
# Thứ tự trong danh sách này là thứ tự vẽ, từ lớp xa nhất đến gần nhất.
PARALLAX_BACKGROUND_CONFIG = [
    {
        "file": "assets/backgrounds/background_layer_1.png", # Lớp xa nhất (nền sương mù)
        "speed": 0.2
    },
    {
        "file": "assets/backgrounds/background_layer_2.png", # Lớp giữa (cây tím)
        "speed": 0.5
    },
    {
        "file": "assets/backgrounds/background_layer_3.png", # Lớp gần nhất (cây cam)
        "speed": 0.8
    }
]


# Animation configuration for player
ANIMATION_CONFIG = {
    'run': {
        'file': 'assets/player/_Run.png',
        'frames': 10,
        'frame_width': 120,
        'frame_height': 80,
        'scale': 0.7,
        'speed': 75
    },
    'jump': {
        'file': 'assets/player/_Jump.png',
        'frames': 3,
        'frame_width': 120,
        'frame_height': 80,
        'scale': 0.7,
        'speed': 100
    },
    'fall': {
        'file': 'assets/player/_JumpFallInbetween.png',
        'frames': 2,
        'frame_width': 120,
        'frame_height': 80,
        'scale': 0.7,
        'speed': 120
    }
}