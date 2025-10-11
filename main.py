import pygame
import sys
import json
import random
import math
import neat
import os
from collections import deque
from config import *
from level_manager import LevelManager
from level_editor import LevelEditor
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
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
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
            maxlen = max([p["platform"].length for p in paths])
            cursor_x = branch_x + maxlen
        else:
            raise ValueError("Unknown section type")
    total_length = cursor_x
    return world, total_length

# -------------------------
# Environment (wrapper)
# -------------------------
class ParkourEnv:
    def __init__(self, level_path, render=False):
        self.world, self.level_length = load_level(level_path)
        self.render = render
        if self.render:
            pygame.init()
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
        self.screen.fill((30, 30, 40))
        pygame.draw.rect(self.screen, (50,50,50), (0, GROUND_Y, SCREEN_W, SCREEN_H - GROUND_Y))
        
        for seg in self.world:
            if seg["type"] == "straight":
                p = seg["platform"]
                x_on_screen = p.x - self.world_x
                if x_on_screen + p.length >= -200 and x_on_screen <= SCREEN_W + 200:
                    pygame.draw.rect(self.screen, (80,80,80), (x_on_screen, p.y, p.length, 6))
                for ob in seg["obstacles"]:
                    ox = ob.x - self.world_x
                    col = (200,40,40) if ob.kind == "real" else (120,120,220)
                    pygame.draw.rect(self.screen, col, (ox, ob.y - ob.h, ob.w, ob.h))
            else:
                for pi, pdef in enumerate(seg["paths"]):
                    p = pdef["platform"]
                    x_on_screen = p.x - self.world_x
                    color = (100,150,100) if pi==0 else (100,100,150)
                    if x_on_screen + p.length >= -200 and x_on_screen <= SCREEN_W + 200:
                        pygame.draw.rect(self.screen, color, (x_on_screen, p.y, p.length, 6))
                    for ob in pdef["obstacles"]:
                        ox = ob.x - self.world_x
                        col = (200,40,40) if ob.kind == "real" else (120,120,220)
                        pygame.draw.rect(self.screen, col, (ox, ob.y - ob.h, ob.w, ob.h))

        pygame.draw.rect(self.screen, (220,220,50), (self.player_x, self.player_y, PLAYER_W, PLAYER_H))
        
        font = pygame.font.SysFont(None, 20)
        txt = font.render(f"WorldX {int(self.world_x)} Score {int(self.score)}", True, (200,200,200))
        self.screen.blit(txt, (8,8))

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

def run_neat(config_file, generations=None, visualize_best=False):
    if generations is None:
        generations = DEFAULT_GENERATIONS
    config = neat.Config(neat.DefaultGenome, neat.DefaultReproduction,
                         neat.DefaultSpeciesSet, neat.DefaultStagnation,
                         config_file)
    p = neat.Population(config)
    p.add_reporter(neat.StdOutReporter(True))
    stats = neat.StatisticsReporter()
    p.add_reporter(stats)

    winner = p.run(eval_genomes, generations)
    print("=== Best genome ===")
    print(winner)
    with open("winner_genome.pkl", "wb") as f:
        import pickle
        pickle.dump(winner, f)
    if visualize_best:
        play_with_genome(winner, config)

def play_with_genome(genome, config):
    net = neat.nn.FeedForwardNetwork.create(genome, config)
    env = ParkourEnv(DEFAULT_LEVEL, render=True)
    obs = env.reset()
    done = False
    while not done:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return
        outputs = net.activate(obs)
        action = int(outputs.index(max(outputs))) if len(outputs) >= 4 else 0
        obs, reward, done, _ = env.step(action)
        env.render_screen()
    pygame.time.wait(1000)
    pygame.quit()

# -------------------------
# Player Class - FIXED ANIMATION
# -------------------------
class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        
        self.vy = 0
        self.on_ground = True

        self.state = 'run'
        self.current_frame = 0
        self.last_update_time = pygame.time.get_ticks()

        # Load animations từ config
        self.animations = {}
        for anim_name, anim_cfg in ANIMATION_CONFIG.items():
            self.animations[anim_name] = self.load_spritesheet(
                anim_cfg['file'],
                anim_cfg['frames'],
                anim_cfg['frame_width'],
                anim_cfg['frame_height'],
                anim_cfg['scale'],
                anim_cfg['speed']
            )
        
        self.image = self.animations[self.state]['frames'][self.current_frame]
        self.rect = self.image.get_rect()
        self.rect.topleft = (x, y)
        
        # Tạo hitbox nhỏ hơn sprite để collision chính xác hơn
        # Hitbox sẽ ở giữa sprite, không tính phần trong suốt
        self.hitbox = pygame.Rect(0, 0, PLAYER_W, PLAYER_H)
        self.update_hitbox()

    def load_spritesheet(self, path, num_frames, frame_w, frame_h, scale, anim_speed):
        frames = []
        try:
            spritesheet = pygame.image.load(path).convert_alpha()
            sheet_width = spritesheet.get_width()
            
            # Tự động tính frame width nếu không khớp
            actual_frame_w = sheet_width // num_frames
            
            for i in range(num_frames):
                rect = pygame.Rect(i * actual_frame_w, 0, actual_frame_w, frame_h)
                frame = spritesheet.subsurface(rect)
                new_width = int(actual_frame_w * scale)
                new_height = int(frame_h * scale)
                frame = pygame.transform.scale(frame, (new_width, new_height))
                frames.append(frame)
        except pygame.error as e:
            print(f"Lỗi: Không thể nạp file ảnh tại '{path}': {e}")
            # Tạo placeholder frame
            placeholder = pygame.Surface((int(frame_w*scale), int(frame_h*scale)), pygame.SRCALPHA)
            placeholder.fill((255, 0, 255, 128))  # Màu magenta để dễ nhận biết
            frames.append(placeholder)

        return {'frames': frames, 'speed': anim_speed}

    def jump(self):
        if self.on_ground:
            self.vy = JUMP_V
            self.on_ground = False
            self.state = 'jump'
            self.current_frame = 0  # Reset về frame đầu khi nhảy

    def update_hitbox(self):
        # Căn hitbox vào giữa sprite (horizontally) và bottom (vertically)
        self.hitbox.centerx = self.rect.centerx
        self.hitbox.bottom = self.rect.bottom

    def update(self):
        # Vật lý
        self.vy += GRAVITY
        self.rect.y += self.vy
        
        if self.rect.bottom >= GROUND_Y:
            self.rect.bottom = GROUND_Y
            self.vy = 0
            self.on_ground = True

        # Cập nhật trạng thái animation
        previous_state = self.state
        if not self.on_ground:
            if self.vy < 0:
                self.state = 'jump'
            else:
                self.state = 'fall'
        else:
            self.state = 'run'
        
        # Reset frame khi đổi trạng thái
        if self.state != previous_state:
            self.current_frame = 0

        # Cập nhật frame
        now = pygame.time.get_ticks()
        current_anim = self.animations[self.state]
        
        if now - self.last_update_time > current_anim['speed']:
            self.last_update_time = now
            
            if self.state == 'jump':
                # Jump animation chỉ chạy 1 lần
                if self.current_frame < len(current_anim['frames']) - 1:
                    self.current_frame += 1
            else:
                # Run và Fall lặp lại
                self.current_frame = (self.current_frame + 1) % len(current_anim['frames'])
            
            self.image = current_anim['frames'][self.current_frame]
        
        # Cập nhật hitbox theo vị trí mới
        self.update_hitbox()

    def draw(self, screen):
        screen.blit(self.image, self.rect)
        # DEBUG: Vẽ hitbox để kiểm tra (xóa dòng này sau khi test xong)
        pygame.draw.rect(screen, (0, 255, 0), self.hitbox, 2)

# -------------------------
# Game State Management (REFACTORED STRUCTURE)
# -------------------------

class GameState:
    """Lớp cơ sở cho tất cả các trạng thái game."""
    def __init__(self, game):
        self.game = game
    def handle_events(self, events): pass
    def update(self): pass
    def draw(self, screen): pass
    def enter_state(self): pass
    def exit_state(self): pass

class PlayingState(GameState):
    """Trạng thái khi người chơi đang trong màn chơi."""
    def __init__(self, game, level_file):
        super().__init__(game)
        self.level_file = level_file
        try:
            self.world, self.level_length = load_level(self.level_file)
        except Exception as e:
            print(f"Error loading {level_file}: {e}. Loading default level.")
            self.world, self.level_length = load_level(DEFAULT_LEVEL)
        
        self.player = None
        self.world_x_offset = 0

    def enter_state(self):
        """Reset lại màn chơi mỗi khi bắt đầu."""
        print(f"Entering Playing State for level: {self.level_file}")
        self.player = Player(50, GROUND_Y - 56)
        self.world_x_offset = 0

    def handle_events(self, events):
        for event in events:
            if event.type == pygame.QUIT:
                self.game.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    self.player.jump()
                if event.key == pygame.K_ESCAPE: # Thêm: Quay lại menu
                    self.game.running = False

    def update(self):
        self.player.update()
        self.world_x_offset += RUN_SPEED

        # Kiểm tra va chạm
        for seg in self.world:
            # ... (logic va chạm giữ nguyên y hệt như phiên bản trước)
            obstacles_to_check = []
            if seg["type"] == "straight": obstacles_to_check = seg["obstacles"]
            else: 
                for pdef in seg["paths"]: obstacles_to_check.extend(pdef["obstacles"])
            
            for ob in obstacles_to_check:
                ox_on_screen = ob.x - self.world_x_offset
                ob_rect_on_screen = pygame.Rect(ox_on_screen, ob.y - ob.h, ob.w, ob.h)
                if self.player.hitbox.colliderect(ob_rect_on_screen) and ob.kind == 'real':
                    self.game.flip_state("game_over")
                    return

    def draw(self, screen):
        # ... (logic vẽ giữ nguyên y hệt như phiên bản trước)
        screen.fill((30, 30, 40))
        for seg in self.world:
            if seg["type"] == "straight":
                p = seg["platform"]
                x_on_screen = p.x - self.world_x_offset
                pygame.draw.rect(screen, (80,80,80), (x_on_screen, p.y, p.length, 6))
                for ob in seg["obstacles"]:
                    ox = ob.x - self.world_x_offset
                    ob_rect = pygame.Rect(ox, ob.y - ob.h, ob.w, ob.h)
                    col = (200,40,40) if ob.kind == "real" else (120,120,220)
                    pygame.draw.rect(screen, col, ob_rect)
            else: # branch
                for pi, pdef in enumerate(seg["paths"]):
                    p = pdef["platform"]
                    x_on_screen = p.x - self.world_x_offset
                    color = (100,150,100) if pi==0 else (100,100,150)
                    pygame.draw.rect(screen, color, (x_on_screen, p.y, p.length, 6))
                    for ob in pdef["obstacles"]:
                        ox = ob.x - self.world_x_offset
                        ob_rect = pygame.Rect(ox, ob.y - ob.h, ob.w, ob.h)
                        col = (200,40,40) if ob.kind == "real" else (120,120,220)
                        pygame.draw.rect(screen, col, ob_rect)
        self.player.draw(screen)

class GameOverState(GameState):
    """Trạng thái màn hình Game Over."""
    def __init__(self, game):
        super().__init__(game)
        # ... (logic GameOverState giữ nguyên y hệt như phiên bản trước)
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
        # ... (logic vẽ GameOverState giữ nguyên y hệt như phiên bản trước)
        screen.fill((10, 10, 10))
        screen.blit(self.text_game_over, self.text_rect)
        screen.blit(self.instr_text, self.instr_rect)

class Game:
    """Lớp chính quản lý game và các trạng thái của nó."""
    def __init__(self, screen, level_file):
        # pygame.init() -> XÓA DÒNG NÀY
        self.screen = screen # Sử dụng screen được truyền vào
        pygame.display.set_caption(f"Parkour Game - {level_file}")
        self.clock = pygame.time.Clock()
        self.running = True
        
        self.states = {
            "playing": PlayingState(self, level_file),
            "game_over": GameOverState(self)
        }
        self.current_state_name = "playing"
        self.current_state = self.states[self.current_state_name]
        self.current_state.enter_state()

        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption(f"Parkour Game - {level_file}")
        self.clock = pygame.time.Clock()
        self.running = True
        
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
        while self.running:
            events = pygame.event.get()
            self.current_state.handle_events(events)
            self.current_state.update()
            self.current_state.draw(self.screen)
            pygame.display.flip()
            self.clock.tick(FPS)
        #pygame.quit()
        print("Exiting game screen, returning to menu...")

# -------------------------
# Entry point for playing manually
# -------------------------
def play_manually(level_file=DEFAULT_LEVEL):
    """Khởi tạo và chạy game với một level cụ thể."""
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    game = Game(screen, level_file)
    game.run()
    pygame.quit()


def main_app():
    """
    Hàm điều phối chính của ứng dụng.
    Khởi tạo Pygame MỘT LẦN, sau đó chạy các trạng thái con (Menu, Game, Editor).
    """
    # --- Khởi tạo Pygame một lần duy nhất ở đây ---
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    
    # Trạng thái hiện tại của ứng dụng
    app_state = "MENU"
    selected_level = None

    while True:
        if app_state == "MENU":
            print("Entering Level Manager...")
            manager = LevelManager(screen)
            user_choice = manager.run()
            
            if user_choice == 'EDITOR':
                app_state = "EDITOR"
            elif user_choice is not None: # Player chose a level
                app_state = "GAME"
                selected_level = user_choice
            else: # Player quit from menu
                break # Thoát khỏi vòng lặp chính

        elif app_state == "GAME":
            print(f"Starting game with level: {selected_level}")
            game = Game(screen, selected_level)
            game.run() # Vòng lặp game sẽ chạy cho đến khi kết thúc (hoặc ESC)
            app_state = "MENU" # Sau khi game kết thúc, quay lại menu

        elif app_state == "EDITOR":
            print("Launching Level Editor...")
            editor = LevelEditor(screen)
            editor.run() # Vòng lặp editor chạy cho đến khi kết thúc
            app_state = "MENU" # Sau khi editor thoát, quay lại menu

    # --- Đóng Pygame một lần duy nhất khi ứng dụng thực sự kết thúc ---
    print("Exiting application.")
    pygame.quit()
    sys.exit()
# -------------------------
# Entry point for NEAT training (không thay đổi)
# -------------------------
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", action="store_true", help="Train NEAT")
    parser.add_argument("--play", action="store_true", help="Play the game manually")
    parser.add_argument("--gen", type=int, default=DEFAULT_GENERATIONS, help="Generations for training")
    parser.add_argument("--render", action="store_true", help="Render the best genome after training")
    args = parser.parse_args()

    if args.play:
        main_app()
    elif args.train:
        local_dir = os.path.dirname(__file__)
        config_path = os.path.join(local_dir, "config-neat.txt")
        run_neat(config_path, generations=args.gen, visualize_best=args.render)
    else:
        print("This file is for training AI.")
        print("To play the game, run 'python run_game.py'")

    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--train", action="store_true", help="Train NEAT")
    parser.add_argument("--play", action="store_true", help="Play the game manually")
    parser.add_argument("--gen", type=int, default=DEFAULT_GENERATIONS, help="Generations for training")
    parser.add_argument("--render", action="store_true", help="Render the best genome after training")
    args = parser.parse_args()

    if args.play:
        play_manually()
    elif args.train:
        local_dir = os.path.dirname(__file__)
        config_path = os.path.join(local_dir, "config-neat.txt")
        run_neat(config_path, generations=args.gen, visualize_best=args.render)
    else:
        print("Vui lòng chọn một chế độ:")
        print("  python main.py --play    (Để tự chơi game)")
        print("  python main.py --train   (Để huấn luyện AI)")