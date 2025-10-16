
SCREEN_W = 1024
SCREEN_H = 700
FPS = 60

# Player settings
PLAYER_W = 22       
PLAYER_H = 36       
JUMP_V = -13      # độ cao nhảy, càng nhỏ càng cao       
GRAVITY = 0.5      # độ rơi             
RUN_SPEED = 3.5

# Cấu hình Endless Mode
SPEED_INCREASE_RATE = 0.2  # Tốc độ sẽ tăng thêm bao nhiêu mỗi giây
MAX_RUN_SPEED = 15         # Tốc độ tối đa có thể đạt được
SAFE_ZONE_DISTANCE = 200

# --- WALL JUMP PHYSICS ---
WALL_CLIMB_TIME_LIMIT = 3.0          # Thời gian tối đa bám tường (giây)
WALL_CLIMB_WARNING_TIME = 1.5        # Thời điểm bắt đầu cảnh báo (giây)
WALL_PUSH_BACK_SPEED = 150           # Tốc độ đẩy lùi tường
CONSECUTIVE_WALL_JUMP_COOLDOWN = 0.1 # Cooldown giữa các lần nhảy liên tiếp
PLAYER_DRAG_COEFFICIENT = 0.85      # Lực cản khi di chuyển ngang
MAX_WALL_SLIDE_SPEED = 2.5        # Tốc độ tối đa khi trượt tường
WALL_COUNTER_SCROLL_SPEED = RUN_SPEED

PLAYER_TARGET_X = 300  # Vị trí X lý tưởng của player trên màn hình (tính từ trái)
CAMERA_CATCH_UP_SPEED_MULTIPLIER = 1.0  # Camera sẽ bắt kịp player nhanh đến mức nào

# Game settings
GROUND_Y = 360
MAX_STEPS_PER_GENOME = 2000
DEFAULT_GENERATIONS = 40
DEFAULT_LEVEL = "level_tutorial.json" 

# --- TILESET SETTINGS ---
TILE_SIZE = 16
TILE_SCALE = 1

# Các preset vị trí tiles trong dungeon_tileset.png
TILE_PRESETS = {
    'grass_top': [(0, 7), (1, 7), (2, 7)],      
    'solid_middle': [(0, 8), (1, 8), (2, 8)],   
    'bottom_platform': [(0, 19), (1, 19), (2, 19)],
    'dark_ground': [(0, 9), (1, 9), (2, 9)],    
    'stone_platform': [(3, 7), (4, 7), (5, 7)],
}

ACTIVE_TILE_PRESET = 'bottom_platform'

# ---------------------------------------------
# CẤU HÌNH BACKGROUND PARALLAX ĐA LỚP
# ---------------------------------------------
PARALLAX_BACKGROUND_CONFIG = [
    {
        "file": "assets/backgrounds/background_layer_1.png",
        "speed": 0.2
    },
    {
        "file": "assets/backgrounds/background_layer_2.png",
        "speed": 0.5
    },
    {
        "file": "assets/backgrounds/background_layer_3.png",
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