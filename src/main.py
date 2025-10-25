import pygame
import sys
import json
import random
import math
import neat
import os
from collections import deque
# Giáº£ sá»­ PLAYER_TARGET_X cÃ³ trong config, náº¿u khÃ´ng sáº½ dÃ¹ng giÃ¡ trá»‹ máº·c Ä‘á»‹nh
from config import * 
from assets_manager import LOADED_THEMES, load_assets
from enemy_manager import LOADED_ENEMIES, load_enemies, get_random_enemy, get_enemy_data, get_enemy_config
from decoy_manager import LOADED_DECOYS, load_decoys, get_random_decoy, get_decoy_data, get_decoy_config

# Thiáº¿t láº­p giÃ¡ trá»‹ máº·c Ä‘á»‹nh náº¿u chÆ°a cÃ³ trong config
if 'PLAYER_TARGET_X' not in globals():
    PLAYER_TARGET_X = SCREEN_W // 3
    print(f"â„¹ï¸ PLAYER_TARGET_X not found in config, defaulting to {PLAYER_TARGET_X}")

# -------------------------
# Initialization Helper
# -------------------------
def initialize_pygame_and_assets():
    if not pygame.get_init():
        pygame.init()
        print("âœ“ Pygame initialized")
    
    if not LOADED_THEMES: load_assets()
    else: print("â„¹ï¸ Assets already loaded, skipping...")
    
    if not LOADED_ENEMIES: load_enemies()
    else: print("â„¹ï¸ Enemies already loaded, skipping...")
    
    if not LOADED_DECOYS: load_decoys()
    else: print("â„¹ï¸ Decoys already loaded, skipping...")

# -------------------------
# Multi-Layer Background
# -------------------------
class MultiLayerBackground:
    def __init__(self, layer_configs):
        self.layers = []
        try:
            for config in layer_configs:
                surface = pygame.image.load(config["file"]).convert_alpha()
                scaled_surface = pygame.transform.scale(surface, (SCREEN_W, SCREEN_H))
                self.layers.append({
                    "image": scaled_surface,
                    "speed": config["speed"],
                    "width": scaled_surface.get_width()
                })
            print(f"âœ“ Successfully loaded {len(self.layers)} background layers.")
        except pygame.error as e:
            print(f"âœ— Error loading background file: {e}")
        except Exception as e:
            print(f"âœ— Unknown error loading background: {e}")
            
    def draw(self, screen, world_x_offset, level_length):
        for layer in self.layers:
            if level_length == -1: 
                actual_scroll = world_x_offset * layer["speed"]
            else:
                max_scroll = max(0, level_length - SCREEN_W)
                actual_scroll = min(world_x_offset * layer["speed"], max_scroll * layer["speed"])
            
            x1 = -(actual_scroll % layer["width"])
            screen.blit(layer["image"], (x1, 0))
            if x1 < 0:
                screen.blit(layer["image"], (x1 + layer["width"], 0))

# -------------------------
# Game Entities (Data Structures)
# -------------------------
class Obstacle:
    def __init__(self, x, y, w=30, h=50, kind="real"):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.kind = kind
    def rect(self):
        return pygame.Rect(self.x, self.y - self.h, self.w, self.h)

class Platform:
    def __init__(self, x, y, length):
        self.x = x
        self.y = y
        self.length = length

class Wall:
    def __init__(self, x, y, height):
        self.x = x
        self.y = y
        self.height = height
        self.width = 10

class WallTile:
    def __init__(self, x, y, width=10, tile_height=40):
        self.x = x
        self.y = y
        self.width = width
        self.tile_height = tile_height

    def rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.tile_height)

# -------------------------
# WALL STATE SYSTEM
# -------------------------
class WallState:
    """Quáº£n lÃ½ tráº¡ng thÃ¡i tÆ°Æ¡ng tÃ¡c vá»›i tÆ°á»ng"""
    
    def __init__(self):
        self.is_sliding = False
        self.side = None
        self.time_elapsed = 0.0
        self.can_jump = True
        self.jump_cooldown = 0.0
        self.re_attach_cooldown = 0.0  # <<< THÃŠM DÃ’NG NÃ€Y

    def reset(self):
        """Reset tráº¡ng thÃ¡i tÆ°á»ng"""
        self.is_sliding = False
        self.side = None
        self.time_elapsed = 0.0
        self.can_jump = True
        self.jump_cooldown = 0.0
        self.re_attach_cooldown = 0.0  # <<< THÃŠM DÃ’NG NÃ€Y
    
    def start_slide(self, side):
        """Báº¯t Ä‘áº§u trÆ°á»£t tÆ°á»ng"""
        if (not self.is_sliding or self.side != side) and self.re_attach_cooldown <= 0: # <<< THÃŠM ÄIá»€U KIá»†N
            self.is_sliding = True
            self.side = side
            self.time_elapsed = 0.0
            if self.jump_cooldown <= 0:
                self.can_jump = True
    
    def stop_slide(self):
        """Dá»«ng trÆ°á»£t tÆ°á»ng"""
        self.is_sliding = False
        self.side = None
        self.time_elapsed = 0.0
    
    def execute_jump(self):
        """Thá»±c hiá»‡n wall jump"""
        if self.can_jump and self.is_sliding:
            self.can_jump = False
            self.jump_cooldown = CONSECUTIVE_WALL_JUMP_COOLDOWN
            self.re_attach_cooldown = 0.2  # Báº­t cooldown 0.2 giÃ¢y <<< THÃŠM DÃ’NG NÃ€Y
            return True
        return False
    
    def update(self, delta_time):
        """Cáº­p nháº­t tráº¡ng thÃ¡i má»—i frame"""
        if self.is_sliding:
            self.time_elapsed += delta_time
        
        if self.jump_cooldown > 0:
            self.jump_cooldown -= delta_time
        elif not self.can_jump:
            self.can_jump = True
            
        if self.re_attach_cooldown > 0:  # <<< THÃŠM KHá»I Lá»†NH NÃ€Y
            self.re_attach_cooldown -= delta_time
# -------------------------
# Terrain Type Handlers
# -------------------------
class TerrainGenerator:
    @staticmethod
    def straight(cursor_x, config):
        plat_y = config.get("platform_y", GROUND_Y)
        length = config.get("length", 500)
        platform = Platform(cursor_x, plat_y, length)
        obstacles = []
        for ob in config.get("obstacles", []):
            ox = cursor_x + ob["x"]
            oy = plat_y if ob["y"] == "ground" else plat_y + ob["y"]
            kind = ob.get("kind", "real")
            obstacles.append(Obstacle(ox, oy, kind=kind))
        return {"type": "straight", "platform": platform, "obstacles": obstacles, "length": length}

    @staticmethod
    def stairs_up(cursor_x, config):
        start_y = config.get("start_y", GROUND_Y)
        step_height = config.get("step_height", 40)
        step_width = config.get("step_width", 120)
        num_steps = config.get("step_count", 5)
        total_length = step_width * num_steps
        platforms = []
        obstacles = []
        for i in range(num_steps):
            step_x = cursor_x + i * step_width
            step_y = start_y - (i * step_height)
            platforms.append(Platform(step_x, step_y, step_width))
        for ob_config in config.get("obstacles", []):
            step_index = ob_config.get("step_index")
            if step_index is not None and 0 <= step_index < len(platforms):
                target_platform = platforms[step_index]
                ox = target_platform.x + ob_config.get("x_offset", step_width / 2)
                oy = target_platform.y
                kind = ob_config.get("kind", "real")
                obstacles.append(Obstacle(ox, oy, kind=kind))
        return {"type": "stairs_up", "platforms": platforms, "obstacles": obstacles, "length": total_length}

    @staticmethod
    def stairs_down(cursor_x, config):
        start_y = config.get("start_y", GROUND_Y)
        step_height = config.get("step_height", 40)
        step_width = config.get("step_width", 100)
        num_steps = config.get("step_count", 5)
        total_length = step_width * num_steps
        platforms = []
        obstacles = []
        for i in range(num_steps):
            step_x = cursor_x + i * step_width
            step_y = start_y + (i * step_height)
            platforms.append(Platform(step_x, step_y, step_width))
        for ob_config in config.get("obstacles", []):
            step_index = ob_config.get("step_index")
            if step_index is not None and 0 <= step_index < len(platforms):
                target_platform = platforms[step_index]
                ox = target_platform.x + ob_config.get("x_offset", step_width / 2)
                oy = target_platform.y
                kind = ob_config.get("kind", "real")
                obstacles.append(Obstacle(ox, oy, kind=kind))
        return {"type": "stairs_down", "platforms": platforms, "obstacles": obstacles, "length": total_length}

    @staticmethod
    def gap(cursor_x, config):
        length = config.get("length", 500)
        base_y = config.get("base_y", GROUND_Y)
        platforms_data = config.get("platforms", [])
        platforms = []
        for p_data in platforms_data:
            p_x = cursor_x + p_data["x"]
            p_y = base_y + p_data.get("y_offset", 0)
            p_width = p_data["width"]
            platforms.append(Platform(p_x, p_y, p_width))
        obstacles = []
        for ob_config in config.get("obstacles", []):
            platform_index = ob_config.get("platform_index")
            if platform_index is not None and 0 <= platform_index < len(platforms):
                target_platform = platforms[platform_index]
                ox = target_platform.x + ob_config.get("x", target_platform.length / 2)
                oy = target_platform.y
                kind = ob_config.get("kind", "real")
                obstacles.append(Obstacle(ox, oy, kind=kind))
            elif "x" in ob_config and "y" in ob_config:
                y_val = ob_config["y"]
                oy = None
                if isinstance(y_val, (int, float)): oy = base_y - y_val
                elif y_val == "midair": oy = base_y - 150
                if oy is not None:
                    ox = cursor_x + ob_config["x"]
                    kind = ob_config.get("kind", "real")
                    obstacles.append(Obstacle(ox, oy, kind=kind))
        return {"type": "gap", "platforms": platforms, "obstacles": obstacles, "length": length}
    
    @staticmethod
    def wall_jump(cursor_x, config):
        wall_height = config.get("height", 250)
        shaft_width = config.get("shaft_width", 150)
        entry_y = config.get("entry_y", GROUND_Y)
        
        entry_platform_len = 100
        exit_platform_len = 150
        wall_tile_width = 10
        wall_tile_height = 40
        
        platforms = []
        wall_tiles = []
        obstacles = []

        platforms.append(Platform(cursor_x, entry_y, entry_platform_len))

        wall_left_x = cursor_x + entry_platform_len
        wall_right_x = wall_left_x + shaft_width
        wall_top_y = entry_y - wall_height
        
        for i in range(0, wall_height, wall_tile_height):
            wall_tiles.append(WallTile(wall_left_x, entry_y - i, wall_tile_width, wall_tile_height))
        
        for i in range(0, wall_height, wall_tile_height):
            wall_tiles.append(WallTile(wall_right_x, entry_y - i, wall_tile_width, wall_tile_height))

        exit_platform_x = wall_right_x + wall_tile_width
        exit_platform_y = wall_top_y
        platforms.append(Platform(exit_platform_x, exit_platform_y, exit_platform_len))

        total_length = (exit_platform_x + exit_platform_len) - cursor_x

        return {
            "type": "wall_jump",
            "platforms": platforms,
            "wall_tiles": wall_tiles,
            "obstacles": obstacles,
            "length": total_length
        }

# -------------------------
# Endless Manager
# -------------------------
class EndlessManager:
    def __init__(self, patterns_data, spawn_logic):
        self.patterns = patterns_data
        self.spawn_logic = spawn_logic
        self.last_pattern_id = None
        print(f"âœ“ EndlessManager initialized with {len(self.patterns)} patterns.")
        if not self.patterns:
            raise ValueError("Endless mode requires at least one pattern.")
    def get_next_pattern(self):
        if self.spawn_logic.get("order") == "random":
            if self.spawn_logic.get("avoid_consecutive_same") and len(self.patterns) > 1:
                available_patterns = [p for p in self.patterns if p.get("id") != self.last_pattern_id]
                chosen_pattern = random.choice(available_patterns)
            else:
                chosen_pattern = random.choice(self.patterns)
            self.last_pattern_id = chosen_pattern.get("id")
            return chosen_pattern
        else:
            return random.choice(self.patterns)

# -------------------------
# Level Loader (JSON)
# -------------------------
def load_level(path):
    full_path = os.path.join('levels', path)
    with open(full_path, "r", encoding="utf-8") as f: data = json.load(f)
    theme_name = data.get("theme", "dungeon").strip()
    is_endless = data.get("mode") == "endless"
    if is_endless:
        patterns = data.get("patterns", [])
        spawn_logic = data.get("spawn_logic", {})
        return {"patterns": patterns, "spawn_logic": spawn_logic, "theme": theme_name, "is_endless": True}
    else:
        world = []
        print(f"ðŸ’¡ Injecting a {SAFE_ZONE_DISTANCE}px safe zone at the start of the level.")
        safe_zone_config = {"type": "straight", "platform_y": GROUND_Y, "length": SAFE_ZONE_DISTANCE, "obstacles": []}
        safe_segment = TerrainGenerator.straight(0, safe_zone_config)
        world.append(safe_segment)
        cursor_x = SAFE_ZONE_DISTANCE
        for sec in data.get("sections", []):
            terrain_type = sec.get("type", "straight")
            terrain_func = getattr(TerrainGenerator, terrain_type, TerrainGenerator.straight)
            if 'start_y' in sec: sec['start_y'] = GROUND_Y 
            segment = terrain_func(cursor_x, sec)
            world.append(segment)
            cursor_x += segment["length"]
        total_length = cursor_x
        return {"world": world, "length": total_length, "theme": theme_name, "is_endless": False}

# -------------------------
# Game Sprites
# -------------------------
def collide_player_hitbox(player, obstacle_sprite):
    player_hitbox = player.hitbox
    obstacle_rect = obstacle_sprite.image.get_rect(midbottom=obstacle_sprite.rect.midbottom)
    return player_hitbox.colliderect(obstacle_rect)

class ObstacleSprite(pygame.sprite.Sprite):
    def __init__(self, world_x, y, kind='real', sprite_type=None):
        super().__init__()
        self._layer = 1
        self.kind = kind
        self.sprite_type = sprite_type
        self.current_frame = 0
        self.anim_timer = 0.0
        self.scaled_frames = []
        self.is_animated = True
        self.world_pos = pygame.math.Vector2(world_x, y)
        sprite_data, sprite_config = (None, None)
        if self.sprite_type:
            if self.kind == 'real':
                sprite_data = get_enemy_data(self.sprite_type)
                sprite_config = get_enemy_config(self.sprite_type)
            elif self.kind == 'fake':
                sprite_data = get_decoy_data(self.sprite_type)
                sprite_config = get_decoy_config(self.sprite_type)
        if sprite_data and sprite_config:
            self.frames = sprite_data['frames']
            self.animation_speed = sprite_config['animation_speed']
            self.scale = sprite_config['scale']
            y_offset = sprite_config['y_offset']
            self.is_animated = not sprite_config['use_static_frame']
            self.world_pos.y += y_offset
            self.world_pos.x += 15 
            for frame in self.frames:
                original_w, original_h = frame.get_size()
                new_w, new_h = int(original_w * self.scale), int(original_h * self.scale)
                self.scaled_frames.append(pygame.transform.scale(frame, (new_w, new_h)))
            self.image = self.scaled_frames[0]
            self.rect = self.image.get_rect()
        else:
            width, height = (30, 50)
            color = (200, 40, 40) if kind == 'real' else (120, 120, 220)
            self.image = pygame.Surface([width, height]); self.image.fill(color)
            self.rect = self.image.get_rect(); self.world_pos.x += width / 2
            self.is_animated = False
            
    def update(self, world_x_offset, delta_time):
        if self.is_animated and self.scaled_frames:
            self.anim_timer += delta_time * 1000
            if self.anim_timer > self.animation_speed:
                self.anim_timer %= self.animation_speed
                self.current_frame = (self.current_frame + 1) % len(self.scaled_frames)
                self.image = self.scaled_frames[self.current_frame]
        screen_x = self.world_pos.x - world_x_offset
        self.rect.midbottom = (screen_x, self.world_pos.y)

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self._layer = 2
        self.vx = 0
        self.vy = 0
        self.on_ground = True
        self.state = 'run'
        self.current_frame = 0
        self.anim_timer = 0.0
        self.animations = {}
        
        self.wall_state = WallState()
        
        for anim_name, anim_cfg in ANIMATION_CONFIG.items():
            self.animations[anim_name] = self.load_spritesheet(
                anim_cfg['file'], anim_cfg['frames'], anim_cfg['frame_width'],
                anim_cfg['frame_height'], anim_cfg['scale'], anim_cfg['speed']
            )
        self.image = self.animations[self.state]['frames'][self.current_frame]
        self.rect = self.image.get_rect(topleft=(x, y))
        self.hitbox = pygame.Rect(0, 0, PLAYER_W, PLAYER_H)
        self.update_hitbox()

    def load_spritesheet(self, path, num_frames, frame_w, frame_h, scale, anim_speed):
        frames = []
        try:
            spritesheet = pygame.image.load(path).convert_alpha()
            for i in range(num_frames):
                rect = pygame.Rect(i * (spritesheet.get_width() // num_frames), 0, (spritesheet.get_width() // num_frames), frame_h)
                frame = spritesheet.subsurface(rect)
                new_w, new_h = int((spritesheet.get_width() // num_frames) * scale), int(frame_h * scale)
                frame = pygame.transform.scale(frame, (new_w, new_h))
                frames.append(frame)
        except pygame.error as e:
            print(f"Error loading spritesheet '{path}': {e}")
            placeholder = pygame.Surface((int(frame_w*scale), int(frame_h*scale)), pygame.SRCALPHA)
            placeholder.fill((255, 0, 255, 128))
            frames.append(placeholder)
        return {'frames': frames, 'speed': anim_speed}

    # DÃ¡n Ä‘oáº¡n code nÃ y Ä‘á»ƒ thay tháº¿ cho hÃ m jump() cÅ© trong class Player
    def jump(self):
        if self.on_ground:
            self.vy = JUMP_V
            self.on_ground = False
        elif self.wall_state.is_sliding and self.wall_state.execute_jump():
            # --- Sá»¬A Lá»–I LOG ---
            # Láº¥y thÃ´ng tin phÃ­a tÆ°á»ng (side) TRÆ¯á»šC KHI reset tráº¡ng thÃ¡i.
            # Äiá»u nÃ y sáº½ Ä‘áº£m báº£o log hiá»ƒn thá»‹ 'left' hoáº·c 'right' thay vÃ¬ 'None'.
            wall_side = self.wall_state.side
            print(f"ðŸš€ WALL CLIMB JUMP from {wall_side} wall!")

            # --- TÃNH TOÃN Láº I Lá»°C NHáº¢Y ---
            # Giá»¯ nguyÃªn lá»±c nháº£y lÃªn (vy) Ä‘á»ƒ Ä‘áº£m báº£o Ä‘á»™ cao.
            # Báº¡n cÃ³ thá»ƒ giáº£m má»™t chÃºt (vÃ­ dá»¥ * 0.95) Ä‘á»ƒ cáº£m giÃ¡c bÃ¡m tÆ°á»ng "náº·ng" hÆ¡n.
            jump_vy = -abs(JUMP_V)

            # Äáº·t lá»±c Ä‘áº©y ngang (vx) vá» 0.
            # ÄÃ¢y lÃ  thay Ä‘á»•i quan trá»ng nháº¥t: nÃ³ khiáº¿n ngÆ°á»i chÆ¡i nháº£y THáº²NG LÃŠN
            # dá»c theo bá»©c tÆ°á»ng, thay vÃ¬ bá»‹ Ä‘áº©y ra xa khá»i nÃ³.
            jump_vx = 0

            self.vy = jump_vy
            self.vx = jump_vx
            
            # Dá»«ng tráº¡ng thÃ¡i trÆ°á»£t tÆ°á»ng SAU KHI Ä‘Ã£ nháº£y.
            # Cooldown "re_attach_cooldown" sáº½ ngÄƒn nhÃ¢n váº­t bÃ¡m láº¡i tÆ°á»ng ngay láº­p tá»©c.
            self.wall_state.stop_slide()

    def update_hitbox(self):
        self.hitbox.centerx = self.rect.centerx
        self.hitbox.bottom = self.rect.bottom

    def _check_wall_collision(self, test_rect, wall_tiles, world_x_offset):
        """Check collision with wall and return side ('left', 'right') or None"""
        for wall_tile in wall_tiles:
            wall_screen_rect = pygame.Rect(
                wall_tile.x - world_x_offset,
                wall_tile.y,
                wall_tile.width,
                wall_tile.tile_height
            )
            
            if not test_rect.colliderect(wall_screen_rect):
                continue
            
            # Determine which side is colliding based on penetration depth
            overlap_left = test_rect.right - wall_screen_rect.left
            overlap_right = wall_screen_rect.right - test_rect.left
            overlap_top = test_rect.bottom - wall_screen_rect.top
            overlap_bottom = wall_screen_rect.bottom - test_rect.top
            
            min_overlap = min(overlap_left, overlap_right, overlap_top, overlap_bottom)
            
            # If horizontal overlap is smaller, it's a side collision
            if min_overlap == overlap_left:
                return ('right', wall_screen_rect, overlap_left)  # Player's right side hit
            elif min_overlap == overlap_right:
                return ('left', wall_screen_rect, overlap_right)   # Player's left side hit
            else:
                 # Vertical collision, not a wall slide
                return (None, None, 0)
        
        return (None, None, 0)

    def update(self, platforms, world_x_offset, delta_time, wall_tiles=None, current_run_speed=RUN_SPEED):
        old_hitbox = self.hitbox.copy()
        
        self.wall_state.update(delta_time)
        
        # === HORIZONTAL MOVEMENT (Screen Space) ===
        self.rect.x += self.vx
        self.vx *= PLAYER_DRAG_COEFFICIENT
        if abs(self.vx) < 0.1:
            self.vx = 0
        self.update_hitbox()
        
        # === WALL COLLISION (Horizontal) ===
        # Logic nÃ y giá» sáº½ tÃ´n trá»ng re_attach_cooldown trong wall_state
        if wall_tiles:
            side, wall_rect, overlap = self._check_wall_collision(self.hitbox, wall_tiles, world_x_offset)
            
            if side:
                if side == 'right' and self.vx >= 0:
                    self.hitbox.right = wall_rect.left
                    self.rect.centerx = self.hitbox.centerx
                    self.vx = 0
                    self.wall_state.start_slide('right')
                elif side == 'left' and self.vx <= 0:
                    self.hitbox.left = wall_rect.right
                    self.rect.centerx = self.hitbox.centerx
                    self.vx = 0
                    self.wall_state.start_slide('left')
                else:
                    self.wall_state.stop_slide()
            else:
                self.wall_state.stop_slide()
            
            self.update_hitbox()
        
        # === VERTICAL MOVEMENT ===
        self.vy += GRAVITY
        
        if self.wall_state.is_sliding and not self.on_ground:
            self.vy = min(self.vy, MAX_WALL_SLIDE_SPEED)
        
        self.rect.y += self.vy
        self.update_hitbox()
        
        # === PLATFORM COLLISION (Vertical) ===
        self.on_ground = False
        for p in platforms:
            platform_screen_rect = pygame.Rect(p.x - world_x_offset, p.y, p.length, 10)
            if self.hitbox.colliderect(platform_screen_rect):
                if self.vy >= 0 and old_hitbox.bottom <= platform_screen_rect.top:
                    self.on_ground = True
                    self.vy = 0
                    self.rect.bottom = platform_screen_rect.top
                    self.wall_state.reset()
                    break
        self.update_hitbox()
        
        # === CHECK WALL TIME LIMIT ===
        if self.wall_state.is_sliding and not self.on_ground:
            if self.wall_state.time_elapsed > WALL_CLIMB_TIME_LIMIT:
                return "WALL_TIME_EXCEEDED"
        
        # === UPDATE STATE & ANIMATION ===
        previous_state = self.state
        
        if self.wall_state.is_sliding and not self.on_ground:
            self.state = 'wall_slide'
        elif not self.on_ground:
            self.state = 'jump' if self.vy < 0 else 'fall'
        else:
            self.state = 'run'
        
        if self.state != previous_state:
            self.current_frame = 0
        
        anim_to_play = 'jump' if self.state == 'wall_slide' else self.state
        current_anim = self.animations[anim_to_play]
        self.anim_timer += delta_time * 1000
        
        if self.anim_timer > current_anim['speed']:
            self.anim_timer %= current_anim['speed']
            if anim_to_play == 'jump' and self.current_frame < len(current_anim['frames']) - 1:
                self.current_frame += 1
            else:
                self.current_frame = (self.current_frame + 1) % len(current_anim['frames'])
        
        self.image = current_anim['frames'][self.current_frame]
        
        if self.wall_state.side == 'right':
            self.image = pygame.transform.flip(self.image, True, False)
        
        return None
# -------------------------
# Game State Management
# -------------------------
class GameState:
    def __init__(self, game): self.game = game
    def handle_events(self, events): pass
    def update(self, delta_time): pass
    def draw(self, screen): pass
    def enter_state(self): pass
    def exit_state(self): pass

class PlayingState(GameState):
    def __init__(self, game, level_file):
        super().__init__(game)
        self.level_file = level_file
        try: level_data = load_level(self.level_file)
        except Exception as e:
            print(f"âœ— Error loading {self.level_file}, falling back to default: {e}")
            level_data = load_level(DEFAULT_LEVEL)
        self.is_endless = level_data["is_endless"]
        theme_name = level_data["theme"]
        self.active_segments = deque()
        self.cursor_x = 0
        if self.is_endless:
            self.endless_manager = EndlessManager(level_data["patterns"], level_data["spawn_logic"])
            self.world_data = None; self.level_length = -1
            self.current_run_speed = RUN_SPEED 
        else:
            self.endless_manager = None
            self.world_data = level_data["world"]; self.level_length = level_data["length"]
            self.current_run_speed = RUN_SPEED
        self.background = MultiLayerBackground(PARALLAX_BACKGROUND_CONFIG)
        self.active_theme_tiles = LOADED_THEMES.get(theme_name)
        if not self.active_theme_tiles:
            print(f"âš ï¸ Theme '{theme_name}' not found! Falling back.")
            self.active_theme_tiles = next(iter(LOADED_THEMES.values())) if LOADED_THEMES else None
        self.all_sprites = pygame.sprite.LayeredUpdates()
        self.real_obstacles = pygame.sprite.Group(); self.fake_obstacles = pygame.sprite.Group()
        
        # --- THAY Äá»”I: Khá»Ÿi táº¡o player táº¡i PLAYER_TARGET_X ---
        self.player = Player(PLAYER_TARGET_X, GROUND_Y - 56)
        
        self.world_x_offset = 0
        self.visible_platforms = [] 
        self.visible_walls = []
        self.visible_wall_tiles = []

    def enter_state(self):
        # Reset all sprites and groups
        self.all_sprites.empty(); self.real_obstacles.empty(); self.fake_obstacles.empty()
        
        # Reset player state completely
        # --- THAY Äá»”I: Äáº·t láº¡i vá»‹ trÃ­ vá» PLAYER_TARGET_X ---
        self.player.rect.x = PLAYER_TARGET_X
        self.player.rect.bottom = GROUND_Y
        self.player.vy = 0; self.player.vx = 0; self.player.on_ground = True; self.player.state = 'run'
        self.player.current_frame = 0
        self.player.anim_timer = 0.0
        self.player.wall_state.reset()
        
        self.player.update_hitbox()
        
        self.all_sprites.add(self.player)
        
        # Reset world state
        self.world_x_offset = 0; self.current_run_speed = RUN_SPEED
        self.visible_platforms.clear(); self.active_segments.clear(); self.cursor_x = 0
        self.visible_wall_tiles.clear()
        self.visible_walls.clear()

        # Generate the starting area of the level
        if self.is_endless:
            print(f"ðŸ’¡ Creating a {SAFE_ZONE_DISTANCE}px safe zone for endless mode.")
            safe_zone_config = {"type": "straight", "platform_y": GROUND_Y, "length": SAFE_ZONE_DISTANCE, "obstacles": []}
            safe_segment = TerrainGenerator.straight(self.cursor_x, safe_zone_config)
            self.active_segments.append(safe_segment)
            self.cursor_x += SAFE_ZONE_DISTANCE
            while self.cursor_x < self.world_x_offset + SCREEN_W * 1.5:
                self._spawn_next_segment()
        else:
            self._create_fixed_level()
            
        print(" priming initial platforms for collision...")
        initial_segments = self.active_segments if self.is_endless else self.world_data
        for seg in initial_segments:
            platforms = seg.get("platforms", [seg.get("platform")])
            for p in platforms:
                if p: self.visible_platforms.append(p)
        print(f"  -> Primed with {len(self.visible_platforms)} platforms.")

    def _create_fixed_level(self):
        print("\nðŸŽ® CREATING FIXED LEVEL")
        for seg in self.world_data:
            for ob_data in seg.get("obstacles", []): self._create_obstacle_sprite(ob_data)
        print("="*40 + "\n")

    def _spawn_next_segment(self):
        pattern = self.endless_manager.get_next_pattern()
        if not pattern: return
        terrain_type = pattern.get("type", "straight")
        terrain_func = getattr(TerrainGenerator, terrain_type, TerrainGenerator.straight)
        segment = terrain_func(self.cursor_x, pattern)
        for ob_data in segment.get("obstacles", []): self._create_obstacle_sprite(ob_data)
        self.active_segments.append(segment)
        self.cursor_x += segment["length"]
        
    def _create_obstacle_sprite(self, ob_data):
        sprite_type = None
        if ob_data.kind == 'real' and LOADED_ENEMIES: sprite_type = get_random_enemy()
        elif ob_data.kind == 'fake' and LOADED_DECOYS: sprite_type = get_random_decoy()
        obstacle_sprite = ObstacleSprite(ob_data.x, ob_data.y, ob_data.kind, sprite_type=sprite_type)
        if ob_data.kind == 'real': self.real_obstacles.add(obstacle_sprite)
        else: self.fake_obstacles.add(obstacle_sprite)
        self.all_sprites.add(obstacle_sprite)
        
    def handle_events(self, events):
        for event in events:
            if event.type == pygame.QUIT: self.game.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE: self.player.jump()
                if event.key == pygame.K_ESCAPE: self.game.running = False

    def update(self, delta_time):
        if self.is_endless:
            if self.current_run_speed < MAX_RUN_SPEED:
                self.current_run_speed += SPEED_INCREASE_RATE * delta_time
            self.current_run_speed = min(self.current_run_speed, MAX_RUN_SPEED)

        # 1. Cuá»™n mÃ n hÃ¬nh theo tá»‘c Ä‘á»™ cÆ¡ báº£n
        base_scroll = self.current_run_speed * delta_time * 60
        self.world_x_offset += base_scroll
        
        # --- THAY Äá»”I: ÄÃ£ loáº¡i bá» kiá»ƒm tra "Player was left behind" ---
        # VÃ¬ ngÆ°á»i chÆ¡i Ä‘Æ°á»£c khÃ³a vÃ o PLAYER_TARGET_X, há» khÃ´ng thá»ƒ bá»‹ bá» láº¡i.

        # Clear physics lists for the current frame
        self.visible_platforms.clear()
        self.visible_walls.clear()
        self.visible_wall_tiles.clear()
        
        DYNAMIC_WALL_WIDTH = 10
        WALL_TILE_HEIGHT = 40
        segments_to_draw = self.active_segments if self.is_endless else self.world_data
        # DEBUG
        print(f"\n=== FRAME DEBUG ===")
        print(f"Total segments: {len(segments_to_draw)}")
        for i, seg in enumerate(segments_to_draw):
            wall_tiles = seg.get("wall_tiles", [])
            if wall_tiles:
                print(f"  Segment {i}: type={seg.get('type')}, wall_tiles={len(wall_tiles)}")
                for j, tile in enumerate(wall_tiles[:2]):  # Print first 2 tiles
                    print(f"    Tile {j}: x={tile.x}, y={tile.y}, w={tile.width}, h={tile.tile_height}")        

        # Collect visible platforms and wall tiles from segments
        for seg in segments_to_draw:
            # Add wall tiles from segment (from wall_jump sections)
            for tile in seg.get("wall_tiles", []):
                self.visible_wall_tiles.append(tile)
            
            # Add platforms
            platforms = seg.get("platforms", [seg.get("platform")])
            for p in platforms:
                if p is None: 
                    continue
                
                x_on_screen = p.x - self.world_x_offset
                if x_on_screen + p.length < -200 or x_on_screen > SCREEN_W + 200:
                    continue
                
                self.visible_platforms.append(p)
                
                
        
        # 2. Cáº­p nháº­t Player (di chuyá»ƒn rect dá»±a trÃªn vx, xá»­ lÃ½ va cháº¡m)
        wall_check = self.player.update(
            self.visible_platforms, 
            self.world_x_offset, 
            delta_time, 
            wall_tiles=self.visible_wall_tiles,
            current_run_speed=self.current_run_speed
        )
        
        # --- THAY Äá»”I: LOGIC CAMERA LOCK ---
        # Chá»‰ Ã¡p dá»¥ng khÃ³a camera khi ngÆ°á»i chÆ¡i khÃ´ng trÆ°á»£t tÆ°á»ng.
        # Khi trÆ°á»£t tÆ°á»ng, vá»‹ trÃ­ ngang cá»§a ngÆ°á»i chÆ¡i Ä‘Æ°á»£c quyáº¿t Ä‘á»‹nh bá»Ÿi va cháº¡m vá»›i tÆ°á»ng,
        # khÃ´ng pháº£i bá»Ÿi vá»‹ trÃ­ má»¥c tiÃªu, giÃºp loáº¡i bá» hiá»‡n tÆ°á»£ng giáº­t lag.
       # Tính toán sự khác biệt giữa vị trí hiện tại và vị trí mục tiêu
        current_screen_x = self.player.rect.x
        diff = current_screen_x - PLAYER_TARGET_X

        # Điều chỉnh offset thế giới để bù đắp sự di chuyển của người chơi
        self.world_x_offset += diff

        # Khóa cứng vị trí hiển thị của người chơi tại mục tiêu
        self.player.rect.x = PLAYER_TARGET_X
        self.player.update_hitbox()

        if wall_check == "WALL_TIME_EXCEEDED":
            print("Game Over: Wall time exceeded!")
            self.game.flip_state("game_over")
            return
        
        # Cáº­p nháº­t vá»‹ trÃ­ mÃ n hÃ¬nh cá»§a cÃ¡c sprite khÃ¡c dá»±a trÃªn world_x_offset Má»šI
        for sprite in self.all_sprites:
            if sprite != self.player:
                sprite.update(self.world_x_offset, delta_time)
        
        # Kiá»ƒm tra va cháº¡m vá»›i chÆ°á»›ng ngáº¡i váº­t (sá»­ dá»¥ng vá»‹ trÃ­ mÃ n hÃ¬nh Ä‘Ã£ cáº­p nháº­t)
        collisions = pygame.sprite.spritecollide(self.player, self.real_obstacles, False, collided=collide_player_hitbox)
        if collisions:
            print("Player collided with an obstacle! Game Over.")
            self.game.flip_state("game_over")
            return

        if self.player.rect.top > SCREEN_H:
            print("Player fell into the abyss! Game Over.")
            self.game.flip_state("game_over")
            return

        if self.is_endless:
            if self.cursor_x < self.world_x_offset + SCREEN_W * 1.5:
                self._spawn_next_segment()
            if self.active_segments:
                first_seg = self.active_segments[0]
                platforms = first_seg.get("platforms", [first_seg.get("platform")])
                if platforms and platforms[-1] and platforms[-1].x + platforms[-1].length < self.world_x_offset - 200:
                    self.active_segments.popleft()
            for sprite in list(self.all_sprites):
                if not isinstance(sprite, Player) and sprite.world_pos.x < self.world_x_offset - 200:
                    sprite.kill()
        else:
            if self.world_x_offset >= self.level_length - PLAYER_W:
                self.game.game_status = 'COMPLETED'
                self.game.running = False
                return
                    
    def draw(self, screen):
        screen.fill((30, 30, 40))
        if self.background:
            self.background.draw(screen, self.world_x_offset, self.level_length)

        if not self.active_theme_tiles:
            self.draw_platforms_fallback(screen)
            self.all_sprites.draw(screen)
            return

        tile_top_left = self.active_theme_tiles.get('wall_top_left')
        tile_top_middle = self.active_theme_tiles.get('wall_top_middle')
        tile_top_right = self.active_theme_tiles.get('wall_top_right')
        tile_middle_left = self.active_theme_tiles.get('wall_middle_left')
        tile_middle_right = self.active_theme_tiles.get('wall_middle_right')
        tile_fill = self.active_theme_tiles.get('wall_fill') 
        
        essential_tiles = [tile_top_left, tile_top_middle, tile_top_right, tile_middle_left, tile_middle_right]
        if not all(essential_tiles):
            print("⚠️ Theme is missing essential wall tiles. Using fallback rendering.")
            self.draw_platforms_fallback(screen)
            self.all_sprites.draw(screen)
            return

        tile_size = tile_top_middle.get_width()
        if tile_size == 0: 
            return

        # === DRAW PLATFORMS ===
        for p in self.visible_platforms:
            x_on_screen = p.x - self.world_x_offset
            num_tiles_x = max(1, round(p.length / tile_size))
            start_row = max(0, int(-p.y / tile_size))
            end_row = start_row + math.ceil(SCREEN_H / tile_size) + 1
            
            for j in range(start_row, end_row):
                current_y = p.y + j * tile_size
                if current_y > SCREEN_H: 
                    break
                
                if j == 0:
                    for i in range(num_tiles_x):
                        tile_to_draw = tile_top_middle
                        if num_tiles_x > 1:
                            if i == 0: 
                                tile_to_draw = tile_top_left
                            elif i == num_tiles_x - 1: 
                                tile_to_draw = tile_top_right
                        if tile_to_draw:
                            screen.blit(tile_to_draw, (x_on_screen + i * tile_size, p.y))
                else:
                    if num_tiles_x > 1:
                        screen.blit(tile_middle_left, (x_on_screen, current_y))
                        if tile_fill:
                            for i in range(1, num_tiles_x - 1):
                                screen.blit(tile_fill, (x_on_screen + i * tile_size, current_y))
                        screen.blit(tile_middle_right, (x_on_screen + (num_tiles_x - 1) * tile_size, current_y))
                    else:
                        screen.blit(tile_middle_left, (x_on_screen, current_y))

        # === DRAW WALL TILES (WITH DEBUG) ===
        print(f"\n=== DRAW DEBUG ===")
        print(f"Drawing {len(self.visible_wall_tiles)} wall tiles")
        print(f"world_x_offset={self.world_x_offset}")
        print(f"SCREEN_W={SCREEN_W}, SCREEN_H={SCREEN_H}")
        print(f"GROUND_Y={GROUND_Y}")
        
        drawn_count = 0
        for i, wall_tile in enumerate(self.visible_wall_tiles):
            if wall_tile.width != 10: 
                continue

            # Convert world position to screen position
            wall_screen_x = wall_tile.x - self.world_x_offset
            wall_screen_y = wall_tile.y
            
            wall_rect = pygame.Rect(
                wall_screen_x,
                wall_screen_y,
                wall_tile.width,
                wall_tile.tile_height
            )
            
            # DEBUG: Print detailed info for each tile
            is_visible = (wall_rect.right >= 0 and wall_rect.left <= SCREEN_W and 
                         wall_rect.bottom >= 0 and wall_rect.top <= SCREEN_H)
            
            if i < 5:
                print(f"  Tile {i}:")
                print(f"    World pos: ({wall_tile.x}, {wall_tile.y})")
                print(f"    Screen pos: ({wall_screen_x}, {wall_screen_y})")
                print(f"    Rect: left={wall_rect.left}, right={wall_rect.right}, top={wall_rect.top}, bottom={wall_rect.bottom}")
                print(f"    Visible: {is_visible}")
            
            # Only draw if visible on screen
            if wall_rect.right < 0 or wall_rect.left > SCREEN_W:
                continue
            if wall_rect.bottom < 0 or wall_rect.top > SCREEN_H:
                continue
            
            drawn_count += 1
            
            # Get the tile image to use
            tile_to_use = self.active_theme_tiles.get('wall_middle_left')
            if tile_to_use:
                # Scale tile to match wall_tile dimensions
                scaled_tile = pygame.transform.scale(tile_to_use, (wall_tile.width, wall_tile.tile_height))
                screen.blit(scaled_tile, (int(wall_rect.x), int(wall_rect.y)))
            else:
                # Fallback: draw colored rectangle
                pygame.draw.rect(screen, (100, 100, 80), wall_rect)
        
        print(f"Total drawn: {drawn_count} wall tiles")
        print("=" * 40)

        # === DRAW SPRITES ===
        self.all_sprites.draw(screen)

        # === DRAW WALL CLIMB TIMER ===
        if self.player.wall_state.is_sliding:
            wall_time_ratio = self.player.wall_state.time_elapsed / WALL_CLIMB_TIME_LIMIT
            bar_width, bar_height = 200, 20
            bar_x, bar_y = SCREEN_W // 2 - bar_width // 2, 30
            
            pygame.draw.rect(screen, (50, 50, 50), (bar_x, bar_y, bar_width, bar_height))
            
            color = (0, 200, 0)
            if wall_time_ratio >= WALL_CLIMB_WARNING_TIME / WALL_CLIMB_TIME_LIMIT:
                color = (255, 100, 0) if wall_time_ratio < 0.8 else (255, 0, 0)
            
            current_bar_width = min(bar_width, bar_width * wall_time_ratio)
            pygame.draw.rect(screen, color, (bar_x, bar_y, current_bar_width, bar_height))
            pygame.draw.rect(screen, (200, 200, 200), (bar_x, bar_y, bar_width, bar_height), 2)
            
            font = pygame.font.SysFont(None, 16)
            text = font.render(f"Wall Time: {self.player.wall_state.time_elapsed:.1f}s", True, (200, 200, 200))
            screen.blit(text, (bar_x, bar_y - 25))

    def draw_platforms_fallback(self, screen):
        segments_to_draw = self.active_segments if self.is_endless else self.world_data
        for seg in segments_to_draw:
            platforms = seg.get("platforms", [seg.get("platform")])
            for p in platforms:
                if p is None: continue
                pygame.draw.rect(screen, (80,80,80), (p.x - self.world_x_offset, p.y, p.length, 6))

class GameOverState(GameState):
    def __init__(self, game):
        super().__init__(game)
        self.font_large = pygame.font.SysFont(None, 60)
        self.text_game_over = self.font_large.render("GAME OVER", True, (255, 60, 60))
        self.text_rect = self.text_game_over.get_rect(center=(SCREEN_W/2, SCREEN_H/2 - 40))
        self.font_small = pygame.font.SysFont(None, 30)
        self.instr_text = self.font_small.render("Press ENTER to Restart | ESC for Menu", True, (200, 200, 200))
        self.instr_rect = self.instr_text.get_rect(center=(SCREEN_W/2, SCREEN_H/2 + 20))

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.QUIT: self.game.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN: self.game.flip_state("playing")
                if event.key == pygame.K_ESCAPE: self.game.running = False

    def draw(self, screen):
        screen.fill((10, 10, 10)); screen.blit(self.text_game_over, self.text_rect); screen.blit(self.instr_text, self.instr_rect)

class Game:
    def __init__(self, screen, level_file):
        initialize_pygame_and_assets()
        self.screen = screen
        pygame.display.set_caption(f"Parkour Game - {level_file}")
        self.clock = pygame.time.Clock()
        self.running = True; self.game_status = 'QUIT'
        self.states = {"playing": PlayingState(self, level_file), "game_over": GameOverState(self)}
        self.current_state_name = "playing"
        self.current_state = self.states[self.current_state_name]
        self.current_state.enter_state()

    def flip_state(self, new_state_name):
        self.current_state.exit_state()
        self.current_state_name = new_state_name
        self.current_state = self.states[self.current_state_name]
        self.current_state.enter_state()

    def run(self):
        last_time = pygame.time.get_ticks()
        while self.running:
            current_time = pygame.time.get_ticks()
            delta_time = (current_time - last_time) / 1000.0
            last_time = current_time
            events = pygame.event.get()
            self.current_state.handle_events(events)
            self.current_state.update(delta_time)
            self.current_state.draw(self.screen)
            pygame.display.flip()
            self.clock.tick(FPS)
        return self.game_status

if __name__ == "__main__":
    print("This file is a module. Run 'game.py' to play.")