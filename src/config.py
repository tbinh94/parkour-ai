# config.py - Game Configuration

# Screen settings
SCREEN_W = 1024
SCREEN_H = 768
FPS = 60

# Player settings - BALANCED PHYSICS (Based on analysis)
PLAYER_W = 22       
PLAYER_H = 36       

# Physics được điều chỉnh dựa trên physics_test.py analysis
JUMP_V = -13      # Giảm từ -13.5 xuống -12 để nhảy thấp hơn (96px max height)
                    # Vẫn đủ để vượt obstacle 50px với 10px clearance
                    
GRAVITY = 0.5      # Giữ nguyên - rơi mượt mà, realistic
                    
RUN_SPEED = 3.5     # Giữ nguyên - tốc độ vừa phải
                    # Total air time: 32 frames (~0.53s)
                    # Jump distance: 112px

# Game settings
GROUND_Y = 360
MAX_STEPS_PER_GENOME = 2000
DEFAULT_GENERATIONS = 40
DEFAULT_LEVEL = "level_tutorial.json"  # Đổi default sang tutorial


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