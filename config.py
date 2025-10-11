# Game Configuration File
# Tách riêng để dễ chỉnh sửa các thông số game

"""
# Menu chính (khuyến nghị)
python main.py --menu

# Chơi level cụ thể
python main.py --play --level level2.json

# Mở editor
python main.py --editor

# Generate random levels
python utils.py batch 5

# Analyze level
python utils.py analyze level2.json

# Train AI
python main.py --train --gen 50
"""

# -------------------------
# Screen Settings
# -------------------------
SCREEN_W = 1024
SCREEN_H = 600
FPS = 60

# -------------------------
# Player Physics
# -------------------------
PLAYER_W = 25
PLAYER_H = 40
GRAVITY = 0.9
JUMP_V = -18
RUN_SPEED = 2  # pixels per frame

# -------------------------
# Animation Settings
# -------------------------
# Dựa vào sprite sheets thực tế:
# _Run.png: 10 frames
# _Jump.png: 3 frames (không phải 4)
# _JumpFallInbetween.png: 2 frames

ANIMATION_CONFIG = {
    'run': {
        'file': 'assets/player/_Run.png',
        'frames': 10,
        'frame_width': 120,    # Width thực tế từ sprite
        'frame_height': 80,    # Height thực tế từ sprite
        'scale': 0.7,          # Scale để vừa với game
        'speed': 75            # ms per frame
    },
    'jump': {
        'file': 'assets/player/_Jump.png',
        'frames': 3,           # FIXED: 3 frames không phải 4
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

# -------------------------
# NEAT Training Settings
# -------------------------
MAX_STEPS_PER_GENOME = 2000
DEFAULT_GENERATIONS = 40

# -------------------------
# Level Settings
# -------------------------
DEFAULT_LEVEL = "level1.json"
GROUND_Y = 360