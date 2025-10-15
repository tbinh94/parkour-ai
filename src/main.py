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

# ❌ KHÔNG gọi load_assets() ở đây vì pygame chưa init!
# load_assets() sẽ được gọi trong game.py sau khi pygame.init()

# -------------------------
# Initialization Helper
# -------------------------
def initialize_pygame_and_assets():
    """Khởi tạo pygame trước, sau đó mới load assets"""
    if not pygame.get_init():
        pygame.init()
        print("✓ Pygame initialized")
    
    # Chỉ load assets một lần duy nhất
    if not LOADED_THEMES:
        load_assets()
    else:
        print("ℹ️ Assets already loaded, skipping...")
    
    # Load enemies
    if not LOADED_ENEMIES:
        load_enemies()
    else:
        print("ℹ️ Enemies already loaded, skipping...")

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
        ✅ Fix 1: Background dừng lại khi hết level.
        """
        for layer in self.layers:
            # Tính toán điểm scroll tối đa để background dừng lại ở cuối level
            max_scroll = max(0, level_length - SCREEN_W)
            # Giới hạn scroll thực tế của layer theo max_scroll
            actual_scroll = min(world_x_offset * layer["speed"], max_scroll * layer["speed"])
            
            x1 = -(actual_scroll % layer["width"])
            screen.blit(layer["image"], (x1, 0))
            # Vẽ thêm một bản sao để tạo hiệu ứng lặp liền mạch
            if x1 < 0:
                screen.blit(layer["image"], (x1 + layer["width"], 0))

# -------------------------
# Game Entities
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
# Level loader (JSON)
# -------------------------
def load_level(path):
    full_path = os.path.join('levels', path)
    with open(full_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    theme_name = data.get("theme", "dungeon").strip()
    
    world = []
    cursor_x = 0
    for sec in data["sections"]:
        if sec["type"] == "straight":
            plat_y = sec.get("platform_y", GROUND_Y)
            p = Platform(cursor_x, plat_y, sec["length"])
            obstacles = []
            for ob in sec.get("obstacles", []):
                ox = cursor_x + ob["x"]
                oy = plat_y if ob["y"] == "ground" else plat_y + ob["y"]
                obstacles.append(Obstacle(ox, oy, kind=ob.get("kind", "real")))
            world.append({"type": "straight", "platform": p, "obstacles": obstacles})
            cursor_x += sec["length"]
        elif sec["type"] == "branch":
            branch_x = sec.get("branch_x", cursor_x + 20)
            paths = []
            for pdef in sec["paths"]:
                offset_y = pdef.get("offset_y", 0)
                length = pdef.get("length", 300)
                plat_y = GROUND_Y + offset_y
                p = Platform(branch_x, plat_y, length)
                obstacles = []
                for ob in pdef.get("obstacles", []):
                    ox = branch_x + ob["x"]
                    oy = plat_y if ob["y"] == "ground" else plat_y + ob["y"]
                    obstacles.append(Obstacle(ox, oy, kind=ob.get("kind", "real")))
                paths.append({"platform": p, "obstacles": obstacles})
            world.append({"type": "branch", "branch_x": branch_x, "paths": paths})
            maxlen = max([p["platform"].length for p in paths]) if paths else 0
            cursor_x = branch_x + maxlen
        else:
            raise ValueError("Unknown section type")
    total_length = cursor_x
    return world, total_length, theme_name

# -------------------------
# Environment (wrapper for NEAT)
# -------------------------
class ParkourEnv:
    def __init__(self, level_path, render=False):
        # ParkourEnv không cần theme, chỉ cần cấu trúc level
        self.world, self.level_length, _ = load_level(level_path)
        self.render = render
        if self.render:
            initialize_pygame_and_assets()  # ✅ Init pygame trước khi dùng
            self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
            pygame.display.set_caption("Parkour NEAT")
            self.clock = pygame.time.Clock()
        self.reset()

    def reset(self):
        self.player_x = 50
        self.world_x = 0
        self.player_y = GROUND_Y - PLAYER_H
        self.vy = 0
        self.on_ground = True
        self.alive = True
        self.steps = 0
        self.score = 0.0
        self.current_platform = None
        self.chosen_paths = {}
        return self.get_state()

    def get_state(self):
        next_obs_dist = 9999
        next_obs_kind = 0
        dist_to_branch = 9999
        branch_upper = 0
        upper_offset = 0

        for seg in self.world:
            if seg["type"] == "straight":
                for ob in seg["obstacles"]:
                    if ob.x - self.world_x > 0:
                        d = ob.x - self.world_x - self.player_x
                        if d >= 0 and d < next_obs_dist:
                            next_obs_dist = d
                            next_obs_kind = 1 if ob.kind == "real" else 0
            else:
                bx = seg["branch_x"]
                if bx - self.world_x - self.player_x >= 0 and (bx - self.world_x - self.player_x) < dist_to_branch:
                    dist_to_branch = bx - self.world_x - self.player_x
                    has_upper = any([p["platform"].y < GROUND_Y for p in seg["paths"]])
                    branch_upper = 1 if has_upper else 0
                    upper_paths = [p for p in seg["paths"] if p["platform"].y < GROUND_Y]
                    upper_offset = GROUND_Y - upper_paths[0]["platform"].y if upper_paths else 0

        norm_py = self.player_y / SCREEN_H
        norm_vy = self.vy / 20.0
        norm_obs_dist = min(next_obs_dist / 500.0, 1.0)
        norm_branch_dist = min(dist_to_branch / 800.0, 1.0)
        norm_upper_offset = min(upper_offset / 400.0, 1.0)

        return [norm_py, norm_vy, norm_obs_dist, next_obs_kind, norm_branch_dist, branch_upper, norm_upper_offset]

    def step(self, action):
        reward = 0.0
        done = False
        self.steps += 1

        for seg in self.world:
            if seg["type"] == "branch":
                bx = seg["branch_x"]
                rel = bx - self.world_x - self.player_x
                if 0 <= rel <= 80:
                    if action == 2:
                        self.chosen_paths[bx] = 0
                    elif action == 3:
                        self.chosen_paths[bx] = 1
        
        if action == 1 and self.on_ground:
            self.vy = JUMP_V
            self.on_ground = False

        self.vy += GRAVITY
        self.player_y += self.vy

        self.world_x += RUN_SPEED
        self.score += RUN_SPEED / 10.0
        
        if self.player_y >= GROUND_Y - PLAYER_H:
            self.player_y = GROUND_Y - PLAYER_H
            self.vy = 0
            self.on_ground = True

        player_world_rect = pygame.Rect(self.player_x + self.world_x, self.player_y, PLAYER_W, PLAYER_H)

        for seg in self.world:
            if seg["type"] == "branch":
                bx = seg["branch_x"]
                if self.world_x >= bx and "applied_" + str(bx) not in seg:
                    idx = self.chosen_paths.get(bx, 0)
                    idx = max(0, min(idx, len(seg["paths"]) - 1))
                    seg["applied_" + str(bx)] = idx

        for seg in self.world:
            obs_list = seg["obstacles"] if seg["type"] == "straight" else []
            if seg["type"] == "branch":
                bx = seg["branch_x"]
                applied = seg.get("applied_" + str(bx), None)
                if applied is not None:
                    obs_list = seg["paths"][applied]["obstacles"]
                else:
                    obs_list = []
                    for p in seg["paths"]:
                        obs_list += p["obstacles"]
            for ob in obs_list:
                ob_rect = pygame.Rect(ob.x, ob.y - ob.h, ob.w, ob.h)
                if player_world_rect.colliderect(ob_rect):
                    if ob.kind == "real":
                        reward -= 50.0
                        self.alive = False
                        done = True
                    else:
                        reward -= 5.0
                        self.world_x -= 20

        if self.world_x >= self.level_length - 50:
            reward += 200.0
            done = True
        if self.steps >= MAX_STEPS_PER_GENOME:
            done = True

        reward += 0.1
        obs = self.get_state()
        return obs, reward, done, {}

    def render_screen(self):
        if not self.render:
            return
        # Phần render cho NEAT không cần tileset, giữ nguyên để test AI
        self.screen.fill((30, 30, 40))
        pygame.draw.rect(self.screen, (50,50,50), (0, GROUND_Y, SCREEN_W, SCREEN_H - GROUND_Y))
        for seg in self.world:
            if seg["type"] == "straight":
                p = seg["platform"]
                x_on_screen = p.x - self.world_x
                pygame.draw.rect(self.screen, (80,80,80), (x_on_screen, p.y, p.length, 6))
            else:
                for pi, pdef in enumerate(seg["paths"]):
                    p = pdef["platform"]
                    x_on_screen = p.x - self.world_x
                    pygame.draw.rect(self.screen, (100,100,150), (x_on_screen, p.y, p.length, 6))

        pygame.draw.rect(self.screen, (220,220,50), (self.player_x, self.player_y, PLAYER_W, PLAYER_H))
        pygame.display.flip()
        self.clock.tick(FPS)

# -------------------------
# NEAT integration
# -------------------------
def eval_genomes(genomes, config):
    for genome_id, genome in genomes:
        genome.fitness = 0.0
        net = neat.nn.FeedForwardNetwork.create(genome, config)
        env = ParkourEnv(DEFAULT_LEVEL, render=False)
        obs = env.reset()
        done = False
        steps = 0
        while not done:
            outputs = net.activate(obs)
            action = int(outputs.index(max(outputs))) if len(outputs) >= 4 else 0
            obs, reward, done, _ = env.step(action)
            genome.fitness += reward
            steps += 1
            if steps > MAX_STEPS_PER_GENOME:
                break
        if math.isnan(genome.fitness):
            genome.fitness = -1.0

# -------------------------
# Player and Game Entities
# -------------------------
def collide_player_hitbox(player, obstacle):
    return player.hitbox.colliderect(obstacle.rect)

class ObstacleSprite(pygame.sprite.Sprite):
    def __init__(self, world_x, y, kind='real', enemy_type=None):
        super().__init__()
        self._layer = 1
        self.kind = kind
        
        self.enemy_type = enemy_type
        self.current_frame = 0
        self.anim_timer = 0.0 # ✅ Fix 2: Timer cho animation dựa trên delta_time
        self.frames = None
        self.scaled_frames = []
        self.is_animated = True

        # self.world_pos lưu vị trí của điểm NEO (midbottom) trong thế giới
        self.world_pos = pygame.math.Vector2(world_x, y)

        if enemy_type and enemy_type in LOADED_ENEMIES:
            enemy_data = get_enemy_data(enemy_type)
            enemy_config = get_enemy_config(enemy_type)
            
            self.frames = enemy_data['frames']
            self.animation_speed = enemy_config['animation_speed']
            self.scale = enemy_config['scale']
            y_offset = enemy_config['y_offset']
            use_static_frame = enemy_config['use_static_frame']

            if use_static_frame:
                self.is_animated = False

            # Cập nhật vị trí y của điểm neo với offset
            self.world_pos.y += y_offset
            # Chỉnh lại world_pos.x để nó là tâm dưới thay vì cạnh trái
            self.world_pos.x += 15 

            for frame in self.frames:
                original_w, original_h = frame.get_size()
                new_w = int(original_w * self.scale)
                new_h = int(original_h * self.scale)
                scaled = pygame.transform.scale(frame, (new_w, new_h))
                self.scaled_frames.append(scaled)
            
            self.image = self.scaled_frames[0]
            self.rect = self.image.get_rect()
            
        else:
            # Fallback hình chữ nhật
            width, height = (30, 50)
            color = (200, 40, 40) if kind == 'real' else (120, 120, 220)
            self.image = pygame.Surface([width, height])
            self.image.fill(color)
            self.rect = self.image.get_rect()
            # Căn chỉnh vị trí logic cho hình chữ nhật
            self.world_pos.x += width / 2
            
    def update(self, world_x_offset, delta_time):
        """
        Cập nhật sprite.
        ✅ Fix 2: Sử dụng delta_time cho animation mượt mà.
        """
        # CẬP NHẬT ANIMATION TRƯỚC
        if self.scaled_frames and self.is_animated:
            self.anim_timer += delta_time * 1000 # Cộng dồn mili giây
            if self.anim_timer > self.animation_speed:
                self.anim_timer -= self.animation_speed # Giữ lại phần dư để chính xác hơn
                self.current_frame = (self.current_frame + 1) % len(self.scaled_frames)
                self.image = self.scaled_frames[self.current_frame]
        
        # LUÔN LUÔN TÍNH TOÁN LẠI VỊ TRÍ HIỂN THỊ DỰA TRÊN VỊ TRÍ LOGIC
        # Lấy rect mới của ảnh hiện tại để có kích thước đúng
        self.rect = self.image.get_rect()
        
        # Tính toán vị trí x trên màn hình
        screen_x = self.world_pos.x - world_x_offset
        
        # Đặt vị trí hiển thị bằng cách gán vị trí neo (midbottom)
        self.rect.midbottom = (screen_x, self.world_pos.y)

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self._layer = 2
        self.vy = 0
        self.on_ground = True
        self.state = 'run'
        self.current_frame = 0
        self.anim_timer = 0.0 # ✅ Fix 2: Timer cho animation dựa trên delta_time
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
            sheet_width = spritesheet.get_width()
            actual_frame_w = sheet_width // num_frames
            for i in range(num_frames):
                rect = pygame.Rect(i * actual_frame_w, 0, actual_frame_w, frame_h)
                frame = spritesheet.subsurface(rect)
                new_width, new_height = int(actual_frame_w * scale), int(frame_h * scale)
                frame = pygame.transform.scale(frame, (new_width, new_height))
                frames.append(frame)
        except pygame.error as e:
            print(f"Error loading spritesheet at '{path}': {e}")
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
        """
        Cập nhật Player.
        ✅ Fix 2: Sử dụng delta_time cho animation mượt mà.
        Tham số world_x_offset được nhận từ group.update() nhưng không dùng đến.
        """
        # --- Physics (vẫn dựa trên frame để giữ nguyên gameplay cho NEAT) ---
        self.vy += GRAVITY
        self.rect.y += self.vy
        if self.rect.bottom >= GROUND_Y: 
            self.rect.bottom = GROUND_Y
            self.vy = 0
            self.on_ground = True
        
        # --- State Management ---
        previous_state = self.state
        if not self.on_ground: 
            self.state = 'jump' if self.vy < 0 else 'fall'
        else: 
            self.state = 'run'
        
        if self.state != previous_state: 
            self.current_frame = 0
        
        # --- Animation (dựa trên delta_time) ---
        current_anim = self.animations[self.state]
        self.anim_timer += delta_time * 1000 # Cộng dồn mili giây
        if self.anim_timer > current_anim['speed']:
            self.anim_timer -= current_anim['speed'] # Giữ lại phần dư
            if self.state == 'jump' and self.current_frame < len(current_anim['frames']) - 1: 
                # Đảm bảo animation jump chạy hết 1 lần rồi dừng ở frame cuối
                self.current_frame += 1
            else: 
                # Các animation khác lặp lại
                self.current_frame = (self.current_frame + 1) % len(current_anim['frames'])
            self.image = current_anim['frames'][self.current_frame]
            
        self.update_hitbox()

# -------------------------
# Game State Management
# -------------------------
class GameState:
    def __init__(self, game):
        self.game = game
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
            self.world_data, self.level_length, theme_name = load_level(self.level_file)
        except Exception as e:
            print(f"❌ Error loading {self.level_file}, falling back to default: {e}")
            self.world_data, self.level_length, theme_name = load_level(DEFAULT_LEVEL)
        
        self.background = MultiLayerBackground(PARALLAX_BACKGROUND_CONFIG)
        
        # DEBUG: Kiểm tra theme có load không
        print(f"🎨 Level requires theme: '{theme_name}'")
        print(f"🗂️ Available themes in LOADED_THEMES: {list(LOADED_THEMES.keys())}")
        
        # SỬA LỖI TẠI ĐÂY: Lấy theme từ dictionary LOADED_THEMES
        self.active_theme_tiles = LOADED_THEMES.get(theme_name)
        if not self.active_theme_tiles:
            print(f"⚠️ Theme '{theme_name}' not found! Falling back to the first available theme.")
            if LOADED_THEMES:
                self.active_theme_tiles = next(iter(LOADED_THEMES.values()))
                print(f"✓ Using fallback theme with tiles: {list(self.active_theme_tiles.keys())}")
            else:
                print("❌ CRITICAL: No themes loaded at all!")
                self.active_theme_tiles = None
        else:
            print(f"✓ Theme '{theme_name}' loaded successfully!")
            print(f"  Available tiles: {list(self.active_theme_tiles.keys())}")
        
        self.all_sprites = pygame.sprite.LayeredUpdates()
        self.real_obstacles = pygame.sprite.Group()
        self.fake_obstacles = pygame.sprite.Group()
        self.player = Player(50, GROUND_Y - 56)
        self.world_x_offset = 0

    def enter_state(self):
        self.all_sprites.empty()
        self.real_obstacles.empty()
        self.fake_obstacles.empty()
        
        self.player.rect.x = 50
        self.player.rect.bottom = GROUND_Y
        self.player.vy = 0
        self.player.on_ground = True
        self.player.state = 'run'

        self.all_sprites.add(self.player)

        # 🔥 TẠO OBSTACLES VỚI RANDOM ENEMIES
        print("\n" + "="*60)
        print("🎮 CREATING OBSTACLES WITH ENEMIES")
        print("="*60)
        print(f"📋 Available enemies in LOADED_ENEMIES: {list(LOADED_ENEMIES.keys())}")
        print(f"📊 Number of enemies loaded: {len(LOADED_ENEMIES)}")
        
        if not LOADED_ENEMIES:
            print("⚠️ WARNING: No enemies loaded! Obstacles will use fallback rectangles.")
        
        obstacle_count = 0
        enemy_count = 0
        
        for seg in self.world_data:
            obstacles_in_segment = []
            if seg["type"] == "straight":
                obstacles_in_segment = seg.get("obstacles", [])
            elif seg["type"] == "branch":
                for path in seg.get("paths", []):
                    obstacles_in_segment.extend(path.get("obstacles", []))
            
            for ob_data in obstacles_in_segment:
                obstacle_count += 1
                
                # Random enemy nếu là real obstacle và có enemies available
                enemy_type = None
                if ob_data.kind == 'real' and LOADED_ENEMIES:
                    enemy_type = get_random_enemy()
                    enemy_count += 1
                    print(f"\n  Obstacle #{obstacle_count}:")
                    print(f"    Position: x={ob_data.x}, y={ob_data.y}")
                    print(f"    Kind: {ob_data.kind}")
                    print(f"    🎲 Selected enemy: {enemy_type}")
                
                obstacle_sprite = ObstacleSprite(
                    ob_data.x, 
                    ob_data.y, 
                    ob_data.kind,
                    enemy_type=enemy_type  # 🔥 Pass enemy type
                )
                
                if ob_data.kind == 'real':
                    self.real_obstacles.add(obstacle_sprite)
                else:
                    self.fake_obstacles.add(obstacle_sprite)
                self.all_sprites.add(obstacle_sprite)
        
        print("\n" + "-"*60)
        print(f"✓ Created {obstacle_count} obstacles total")
        print(f"✓ Applied enemies to {enemy_count} real obstacles")
        print("="*60 + "\n")
        
        self.world_x_offset = 0

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                self.game.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.player.jump()
                if event.key == pygame.K_ESCAPE:
                    self.game.running = False

    def update(self, delta_time):
        self.world_x_offset += RUN_SPEED
        # Cập nhật tất cả các sprite trong group, truyền cả offset và delta_time
        # Player cũng nằm trong group này và sẽ được cập nhật một lần duy nhất
        self.all_sprites.update(self.world_x_offset, delta_time)
        
        if self.world_x_offset >= self.level_length - PLAYER_W:
            self.game.game_status = 'COMPLETED'
            self.game.running = False
            return
        
        if pygame.sprite.spritecollide(self.player, self.real_obstacles, False, collide_player_hitbox):
            self.game.flip_state("game_over")
            return
    
    def draw(self, screen):
        screen.fill((30, 30, 40))
        if self.background:
            # ✅ Fix 1: Truyền level_length để background dừng lại đúng lúc
            self.background.draw(screen, self.world_x_offset, self.level_length)

        # SỬA LỖI LỚN TẠI ĐÂY: Logic vẽ platform hoàn toàn mới
        if not self.active_theme_tiles:
            print("⚠️ WARNING: No tiles available, using fallback rendering")
            self.draw_platforms_fallback(screen)
            self.all_sprites.draw(screen)
            return

        tile_left = self.active_theme_tiles.get('ground_left')
        tile_middle = self.active_theme_tiles.get('ground_middle')
        tile_right = self.active_theme_tiles.get('ground_right')
        
        # DEBUG: Kiểm tra tile có tồn tại không
        if not all([tile_left, tile_middle, tile_right]):
            print("⚠️ WARNING: Missing ground tiles (left/middle/right)")
            print(f"  tile_left: {tile_left is not None}")
            print(f"  tile_middle: {tile_middle is not None}")
            print(f"  tile_right: {tile_right is not None}")
            self.draw_platforms_fallback(screen)
            self.all_sprites.draw(screen)
            return

        # Lấy kích thước tile từ tile đã load
        tile_size = tile_middle.get_width() if tile_middle else 16

        for seg in self.world_data:
            if seg["type"] == "straight":
                p = seg["platform"]
                x_on_screen = p.x - self.world_x_offset
                
                # Chỉ vẽ nếu platform nằm trong màn hình
                if x_on_screen + p.length < 0 or x_on_screen > SCREEN_W:
                    continue
                
                num_tiles = max(3, int(p.length / tile_size))  # Tối thiểu 3 tiles
                for i in range(num_tiles):
                    tile_to_draw = tile_middle
                    if i == 0:
                        tile_to_draw = tile_left
                    elif i == num_tiles - 1:
                        tile_to_draw = tile_right
                    
                    tile_x = x_on_screen + i * tile_size
                    screen.blit(tile_to_draw, (tile_x, p.y))
                    
            elif seg["type"] == "branch":
                for pdef in seg["paths"]:
                    p = pdef["platform"]
                    x_on_screen = p.x - self.world_x_offset
                    
                    if x_on_screen + p.length < 0 or x_on_screen > SCREEN_W:
                        continue
                    
                    num_tiles = max(3, int(p.length / tile_size))
                    for i in range(num_tiles):
                        tile_to_draw = tile_middle
                        if i == 0:
                            tile_to_draw = tile_left
                        elif i == num_tiles - 1:
                            tile_to_draw = tile_right
                        
                        tile_x = x_on_screen + i * tile_size
                        screen.blit(tile_to_draw, (tile_x, p.y))

        self.all_sprites.draw(screen)

    def draw_platforms_fallback(self, screen):
        print("⚠️ Warning: Drawing fallback platforms. Check themes.json or level files.")
        for seg in self.world_data:
            if seg["type"] == "straight":
                p = seg["platform"]
                pygame.draw.rect(screen, (80,80,80), (p.x - self.world_x_offset, p.y, p.length, 6))
            else:
                for pi, pdef in enumerate(seg["paths"]):
                    p = pdef["platform"]
                    color = (100,150,100) if pi==0 else (100,100,150)
                    pygame.draw.rect(screen, color, (p.x - self.world_x_offset, p.y, p.length, 6))

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
            if event.type == pygame.QUIT: 
                self.game.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN: 
                    self.game.flip_state("playing")
                if event.key == pygame.K_ESCAPE: 
                    self.game.running = False

    def draw(self, screen):
        screen.fill((10, 10, 10))
        screen.blit(self.text_game_over, self.text_rect)
        screen.blit(self.instr_text, self.instr_rect)

class Game:
    def __init__(self, screen, level_file):
        initialize_pygame_and_assets()  # ✅ Đảm bảo pygame và assets đã sẵn sàng
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
        """
        Vòng lặp game chính.
        ✅ Fix 2: Tính toán delta_time ở đây và truyền nó xuống.
        """
        last_time = pygame.time.get_ticks()
        while self.running:
            # Tính toán delta_time (thời gian giữa các frame, tính bằng giây)
            current_time = pygame.time.get_ticks()
            delta_time = (current_time - last_time) / 1000.0
            last_time = current_time
            
            # Xử lý các sự kiện
            events = pygame.event.get()
            self.current_state.handle_events(events)
            
            # Cập nhật trạng thái game với delta_time
            self.current_state.update(delta_time)
            
            # Vẽ lên màn hình
            self.current_state.draw(self.screen)
            
            pygame.display.flip()
            self.clock.tick(FPS)
            
        return self.game_status

# -------------------------
# Entry point
# -------------------------
if __name__ == "__main__":
    print("This file is a module. Run 'game.py' to play.")