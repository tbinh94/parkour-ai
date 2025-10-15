# main.py
import pygame
import sys
import json
import random
import math
import neat
import os
from collections import deque
from config import *
from assets_manager import LOADED_THEMES, load_assets
from enemy_manager import LOADED_ENEMIES, load_enemies, get_random_enemy, get_enemy_data, get_enemy_config
# Import trình quản lý decoy mới
from decoy_manager import LOADED_DECOYS, load_decoys, get_random_decoy, get_decoy_data, get_decoy_config

# -------------------------
# Initialization Helper
# -------------------------
def initialize_pygame_and_assets():
    """Khởi tạo pygame trước, sau đó mới load assets"""
    if not pygame.get_init():
        pygame.init()
        print("✓ Pygame initialized")
    
    if not LOADED_THEMES: load_assets()
    else: print("ℹ️ Assets already loaded, skipping...")
    
    if not LOADED_ENEMIES: load_enemies()
    else: print("ℹ️ Enemies already loaded, skipping...")
    
    if not LOADED_DECOYS: load_decoys()
    else: print("ℹ️ Decoys already loaded, skipping...")

# -------------------------
# Lớp Background Đa Lớp
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
            print(f"✓ Successfully loaded {len(self.layers)} background layers.")
        except pygame.error as e:
            print(f"✗ Error loading background file: {e}")
        except Exception as e:
            print(f"✗ Unknown error loading background: {e}")
            
    def draw(self, screen, world_x_offset, level_length):
        """
        Vẽ các lớp background với hiệu ứng parallax.
        Nếu level_length là -1 (endless), nó sẽ cuộn vô tận.
        """
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

# -------------------------
# Trình quản lý chế độ Endless
# -------------------------
class EndlessManager:
    def __init__(self, patterns_data, spawn_logic):
        self.patterns = [p for p in patterns_data if p.get("type") == "straight"]
        self.spawn_logic = spawn_logic
        self.last_pattern_id = None
        print(f"✓ EndlessManager initialized with {len(self.patterns)} valid 'straight' patterns.")
        if not self.patterns:
            raise ValueError("Endless mode requires at least one pattern of type 'straight'.")

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
# Level loader (JSON)
# -------------------------
def load_level(path):
    full_path = os.path.join('levels', path)
    with open(full_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    theme_name = data.get("theme", "dungeon").strip()
    is_endless = data.get("mode") == "endless"

    if is_endless:
        patterns = data.get("patterns", [])
        spawn_logic = data.get("spawn_logic", {})
        return {
            "patterns": patterns, "spawn_logic": spawn_logic,
            "theme": theme_name, "is_endless": True
        }
    else:
        world = []
        cursor_x = 0
        for sec in data.get("sections", []):
            if sec["type"] == "straight":
                plat_y = sec.get("platform_y", GROUND_Y)
                p = Platform(cursor_x, plat_y, sec["length"])
                obstacles = []
                for ob in sec.get("obstacles", []):
                    ox = cursor_x + ob["x"]
                    oy = plat_y if ob["y"] == "ground" else plat_y + ob["y"]
                    kind = ob.get("kind", "real")
                    obstacles.append(Obstacle(ox, oy, kind=kind))
                world.append({"type": "straight", "platform": p, "obstacles": obstacles})
                cursor_x += sec["length"]
        total_length = cursor_x
        return {
            "world": world, "length": total_length, 
            "theme": theme_name, "is_endless": False
        }

# -------------------------
# Environment & NEAT (Not part of main game loop)
# -------------------------
class ParkourEnv: # (implementation not relevant to game logic)
    def __init__(self, level_path, render=False):
        pass
def eval_genomes(genomes, config): # (implementation not relevant to game logic)
    pass
    
# -------------------------
# Game Sprites
# -------------------------
def collide_player_hitbox(player, obstacle_sprite):
    """Callback for precise sprite collision detection."""
    # Lấy hitbox của người chơi
    player_hitbox = player.hitbox
    
    # Tạo một rect cho obstacle sprite dựa trên vị trí thế giới của nó
    # Điều này quan trọng vì obstacle.rect() của Obstacle data structure không tồn tại.
    # Chúng ta cần dùng rect của ObstacleSprite.
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
        self.frames = None
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
            self.image = pygame.Surface([width, height])
            self.image.fill(color)
            self.rect = self.image.get_rect()
            self.world_pos.x += width / 2
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
        self.vy = 0
        self.on_ground = True
        self.state = 'run'
        self.current_frame = 0
        self.anim_timer = 0.0
        self.animations = {}
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

    def jump(self):
        if self.on_ground:
            self.vy = JUMP_V
            self.on_ground = False
            self.state = 'jump'
            self.current_frame = 0

    def update_hitbox(self):
        self.hitbox.centerx = self.rect.centerx
        self.hitbox.bottom = self.rect.bottom

    def update(self, world_x_offset, delta_time):
        self.vy += GRAVITY
        self.rect.y += self.vy
        if self.rect.bottom >= GROUND_Y: 
            self.rect.bottom = GROUND_Y
            self.vy = 0
            self.on_ground = True
        
        previous_state = self.state
        if not self.on_ground: self.state = 'jump' if self.vy < 0 else 'fall'
        else: self.state = 'run'
        
        if self.state != previous_state: self.current_frame = 0
        
        current_anim = self.animations[self.state]
        self.anim_timer += delta_time * 1000
        if self.anim_timer > current_anim['speed']:
            self.anim_timer -= current_anim['speed']
            if self.state == 'jump' and self.current_frame < len(current_anim['frames']) - 1: 
                self.current_frame += 1
            else: 
                self.current_frame = (self.current_frame + 1) % len(current_anim['frames'])
            self.image = current_anim['frames'][self.current_frame]
            
        self.update_hitbox()

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
        try:
            level_data = load_level(self.level_file)
        except Exception as e:
            print(f"❌ Error loading {self.level_file}, falling back to default: {e}")
            level_data = load_level(DEFAULT_LEVEL)
        
        self.is_endless = level_data["is_endless"]
        theme_name = level_data["theme"]
        
        if self.is_endless:
            self.endless_manager = EndlessManager(level_data["patterns"], level_data["spawn_logic"])
            self.world_data = None
            self.level_length = -1
            self.cursor_x = 0
            self.active_segments = deque()
            # THAY ĐỔI: Khởi tạo biến tốc độ động
            self.current_run_speed = RUN_SPEED 
        else:
            self.endless_manager = None
            self.world_data = level_data["world"]
            self.level_length = level_data["length"]
            # Chế độ thường vẫn dùng tốc độ gốc
            self.current_run_speed = RUN_SPEED
        
        self.background = MultiLayerBackground(PARALLAX_BACKGROUND_CONFIG)
        self.active_theme_tiles = LOADED_THEMES.get(theme_name)
        if not self.active_theme_tiles:
            print(f"⚠️ Theme '{theme_name}' not found! Falling back.")
            self.active_theme_tiles = next(iter(LOADED_THEMES.values())) if LOADED_THEMES else None
        
        self.all_sprites = pygame.sprite.LayeredUpdates()
        self.real_obstacles = pygame.sprite.Group()
        self.fake_obstacles = pygame.sprite.Group()
        self.player = Player(50, GROUND_Y - 56)
        self.world_x_offset = 0


    def enter_state(self):
        self.all_sprites.empty(); self.real_obstacles.empty(); self.fake_obstacles.empty()
        
        self.player.rect.x = 50; self.player.rect.bottom = GROUND_Y
        self.player.vy = 0; self.player.on_ground = True; self.player.state = 'run'
        self.all_sprites.add(self.player)
        self.world_x_offset = 0
        
        # THAY ĐỔI: Reset tốc độ mỗi khi bắt đầu lại màn chơi
        self.current_run_speed = RUN_SPEED

        if self.is_endless:
            self.cursor_x = 0
            self.active_segments.clear()
            while self.cursor_x < SCREEN_W * 1.5: self._spawn_next_segment()
        else:
            self._create_fixed_level()

    def _create_fixed_level(self):
        print("\n🎮 CREATING FIXED LEVEL OBSTACLES")
        for seg in self.world_data:
            for ob_data in seg.get("obstacles", []):
                self._create_obstacle_sprite(ob_data, 0)
        print("="*40 + "\n")

    def _spawn_next_segment(self):
        pattern = self.endless_manager.get_next_pattern()
        if not pattern: return
        
        plat_y = pattern.get("platform_y", GROUND_Y)
        length = pattern.get("length", 500)
        platform = Platform(self.cursor_x, plat_y, length)
        
        obstacles_in_segment = []
        
        # ✅ THAY ĐỔI: Thêm logic vùng an toàn
        # Chỉ tạo obstacles nếu vị trí hiện tại đã vượt qua vùng an toàn.
        # self.cursor_x là vị trí bắt đầu của segment sắp được tạo.
        if self.cursor_x > SAFE_ZONE_DISTANCE:
            for ob_data_raw in pattern.get("obstacles", []):
                kind = "real"
                if "kind" in ob_data_raw:
                    if ob_data_raw["kind"] == "enemy": kind = "real"
                    elif ob_data_raw["kind"] == "illusion": kind = "fake"
                
                ob = Obstacle(
                    x=ob_data_raw["x"],
                    y=plat_y if ob_data_raw["y"] == "ground" else plat_y + ob_data_raw.get("y", 0),
                    kind=kind
                )
                self._create_obstacle_sprite(ob, self.cursor_x)
                obstacles_in_segment.append(ob)

        self.active_segments.append({"type": "straight", "platform": platform, "obstacles": obstacles_in_segment})
        self.cursor_x += length
        
    def _create_obstacle_sprite(self, ob_data, base_offset_x):
        sprite_type = None
        if ob_data.kind == 'real' and LOADED_ENEMIES: sprite_type = get_random_enemy()
        elif ob_data.kind == 'fake' and LOADED_DECOYS: sprite_type = get_random_decoy()
        
        world_x = base_offset_x + ob_data.x
        obstacle_sprite = ObstacleSprite(world_x, ob_data.y, ob_data.kind, sprite_type=sprite_type)
        
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
        # THAY ĐỔI: Logic tăng tốc độ
        if self.is_endless:
            # Chỉ tăng tốc nếu chưa đạt tốc độ tối đa
            if self.current_run_speed < MAX_RUN_SPEED:
                # delta_time là thời gian giữa các frame, giúp tốc độ tăng mượt mà
                self.current_run_speed += SPEED_INCREASE_RATE * delta_time
            # Giới hạn tốc độ không vượt quá MAX_RUN_SPEED
            self.current_run_speed = min(self.current_run_speed, MAX_RUN_SPEED)

        # THAY ĐỔI: Sử dụng tốc độ động thay vì hằng số RUN_SPEED
        self.world_x_offset += self.current_run_speed
        
        self.all_sprites.update(self.world_x_offset, delta_time)

        collisions = pygame.sprite.spritecollide(
            self.player, self.real_obstacles, False, collided=collide_player_hitbox
        )
        if collisions:
            self.game.flip_state("game_over")
            return

        if self.is_endless:
            if self.cursor_x < self.world_x_offset + SCREEN_W * 1.5:
                self._spawn_next_segment()
            
            if self.active_segments:
                first_seg_plat = self.active_segments[0]["platform"]
                if first_seg_plat.x + first_seg_plat.length < self.world_x_offset - 200:
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

        tile_left = self.active_theme_tiles.get('ground_left')
        tile_middle = self.active_theme_tiles.get('ground_middle')
        tile_right = self.active_theme_tiles.get('ground_right')
        
        if not all([tile_left, tile_middle, tile_right]):
            self.draw_platforms_fallback(screen)
            self.all_sprites.draw(screen)
            return

        tile_size = tile_middle.get_width() if tile_middle else 16
        segments_to_draw = self.active_segments if self.is_endless else self.world_data

        for seg in segments_to_draw:
            if seg["type"] == "straight":
                p = seg["platform"]
                x_on_screen = p.x - self.world_x_offset
                if x_on_screen + p.length < -100 or x_on_screen > SCREEN_W + 100: continue
                
                num_tiles = max(3, int(p.length / tile_size))
                for i in range(num_tiles):
                    tile = tile_middle
                    if i == 0: tile = tile_left
                    elif i == num_tiles - 1: tile = tile_right
                    screen.blit(tile, (x_on_screen + i * tile_size, p.y))

        self.all_sprites.draw(screen)

    def draw_platforms_fallback(self, screen):
        segments_to_draw = self.active_segments if self.is_endless else self.world_data
        for seg in segments_to_draw:
            if seg["type"] == "straight":
                p = seg["platform"]
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
        screen.fill((10, 10, 10))
        screen.blit(self.text_game_over, self.text_rect)
        screen.blit(self.instr_text, self.instr_rect)

class Game:
    def __init__(self, screen, level_file):
        initialize_pygame_and_assets()
        self.screen = screen
        pygame.display.set_caption(f"Parkour Game - {level_file}")
        self.clock = pygame.time.Clock()
        self.running = True
        self.game_status = 'QUIT'
        self.states = {
            "playing": PlayingState(self, level_file),
            "game_over": GameOverState(self)
        }
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

# -------------------------
# Entry point
# -------------------------
if __name__ == "__main__":
    print("This file is a module. Run 'game.py' to play.")