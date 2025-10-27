"""
RESPONSIVE CONFIGURATION
Auto-scales game elements based on screen resolution
"""
import pygame

# ============================================
# BASE RESOLUTION (Reference resolution)
# ============================================
BASE_WIDTH = 1024
BASE_HEIGHT = 768

# ============================================
# CURRENT RESOLUTION (Auto-detect or set manually)
# ============================================
def get_screen_resolution():
    """Tự động lấy resolution màn hình hoặc sử dụng giá trị mặc định"""
    info = pygame.display.Info()
    # Sử dụng 90% màn hình để tránh fullscreen
    return int(info.current_w * 0.9), int(info.current_h * 0.9)

# Có thể override bằng cách set trực tiếp
SCREEN_W = 1280
SCREEN_H = 720
FPS = 60

# ============================================
# SCALE FACTORS (Tự động tính)
# ============================================
SCALE_X = SCREEN_W / BASE_WIDTH
SCALE_Y = SCREEN_H / BASE_HEIGHT
SCALE_UNIFORM = min(SCALE_X, SCALE_Y)  # Giữ tỷ lệ đồng nhất

# ============================================
# GROUND POSITION (Sát đáy màn hình)
# ============================================
# Thay vì cố định ở giữa, giờ sẽ tính từ đáy lên
GROUND_MARGIN_FROM_BOTTOM = 150  # Khoảng cách từ đáy màn hình
GROUND_Y = SCREEN_H - GROUND_MARGIN_FROM_BOTTOM

# ============================================
# PLAYER SETTINGS (Scaled)
# ============================================
PLAYER_W = int(22 * SCALE_UNIFORM)
PLAYER_H = int(36 * SCALE_UNIFORM)
JUMP_V = -13 * SCALE_UNIFORM
GRAVITY = 0.5 * SCALE_UNIFORM
RUN_SPEED = 3.5 * SCALE_UNIFORM

# ============================================
# ENDLESS MODE (Scaled)
# ============================================
SPEED_INCREASE_RATE = 0.2 * SCALE_UNIFORM
MAX_RUN_SPEED = 15 * SCALE_UNIFORM
SAFE_ZONE_DISTANCE = int(200 * SCALE_X)

# ============================================
# WALL JUMP PHYSICS (Scaled)
# ============================================
WALL_CLIMB_TIME_LIMIT = 3.0
WALL_CLIMB_WARNING_TIME = 1.5
WALL_PUSH_BACK_SPEED = 150 * SCALE_UNIFORM
CONSECUTIVE_WALL_JUMP_COOLDOWN = 0.1
PLAYER_DRAG_COEFFICIENT = 0.85
MAX_WALL_SLIDE_SPEED = 2.5 * SCALE_UNIFORM
WALL_COUNTER_SCROLL_SPEED = RUN_SPEED

# ============================================
# CAMERA SETTINGS (Scaled)
# ============================================
PLAYER_TARGET_X = int(300 * SCALE_X)
CAMERA_CATCH_UP_SPEED_MULTIPLIER = 1.0

# ============================================
# GAME SETTINGS
# ============================================
MAX_STEPS_PER_GENOME = 2000
DEFAULT_GENERATIONS = 40
DEFAULT_LEVEL = "level_tutorial.json"

# ============================================
# TILESET SETTINGS (Scaled)
# ============================================
TILE_SIZE = int(16 * SCALE_UNIFORM)
TILE_SCALE = SCALE_UNIFORM

# Tile presets
TILE_PRESETS = {
    'grass_top': [(0, 7), (1, 7), (2, 7)],
    'solid_middle': [(0, 8), (1, 8), (2, 8)],
    'bottom_platform': [(0, 19), (1, 19), (2, 19)],
    'dark_ground': [(0, 9), (1, 9), (2, 9)],
    'stone_platform': [(3, 7), (4, 7), (5, 7)],
}

ACTIVE_TILE_PRESET = 'bottom_platform'

# ============================================
# BACKGROUND PARALLAX (Responsive)
# ============================================
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

# ============================================
# ANIMATION CONFIG (Scaled)
# ============================================
ANIMATION_CONFIG = {
    'run': {
        'file': 'assets/player/_Run.png',
        'frames': 10,
        'frame_width': 120,
        'frame_height': 80,
        'scale': 0.7 * SCALE_UNIFORM,
        'speed': 75
    },
    'jump': {
        'file': 'assets/player/_Jump.png',
        'frames': 3,
        'frame_width': 120,
        'frame_height': 80,
        'scale': 0.7 * SCALE_UNIFORM,
        'speed': 100
    },
    'fall': {
        'file': 'assets/player/_JumpFallInbetween.png',
        'frames': 2,
        'frame_width': 120,
        'frame_height': 80,
        'scale': 0.7 * SCALE_UNIFORM,
        'speed': 120
    }
}

# ============================================
# HELPER FUNCTIONS
# ============================================
def scale_pos(x, y):
    """Scale position from base resolution to current resolution"""
    return int(x * SCALE_X), int(y * SCALE_Y)

def scale_size(width, height):
    """Scale size from base resolution to current resolution"""
    return int(width * SCALE_X), int(height * SCALE_Y)

def scale_value(value):
    """Scale a single value uniformly"""
    return value * SCALE_UNIFORM

# ============================================
# DEBUG INFO
# ============================================
def print_resolution_info():
    """In thông tin resolution để debug"""
    print("\n" + "="*50)
    print("🖥️  RESPONSIVE CONFIGURATION")
    print("="*50)
    print(f"Base Resolution: {BASE_WIDTH}x{BASE_HEIGHT}")
    print(f"Current Resolution: {SCREEN_W}x{SCREEN_H}")
    print(f"Scale Factor X: {SCALE_X:.2f}")
    print(f"Scale Factor Y: {SCALE_Y:.2f}")
    print(f"Uniform Scale: {SCALE_UNIFORM:.2f}")
    print(f"Ground Y: {GROUND_Y} (from bottom: {SCREEN_H - GROUND_Y})")
    print(f"Player Size: {PLAYER_W}x{PLAYER_H}")
    print(f"Tile Size: {TILE_SIZE}")
    print("="*50 + "\n")

if __name__ == "__main__":
    pygame.init()
    print_resolution_info()