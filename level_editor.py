# level_editor.py
import pygame
import json
import sys
import os
from config import *

class LevelEditor:
    def __init__(self, screen):
        #pygame.init()
        self.screen = screen
        pygame.display.set_caption("Level Editor")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 24)
        
        # Editor state
        self.running = True
        self.world_data = []
        self.view_x = 0
        self.tool = 'add_real' # add_real, add_fake, delete
        self.current_file = None

    def screen_to_world(self, screen_pos):
        """Chuyển tọa độ màn hình sang tọa độ thế giới."""
        return (screen_pos[0] + self.view_x, screen_pos[1])

    def find_section_at(self, world_x):
        """Tìm section (đoạn platform) tại một tọa độ x của thế giới."""
        cursor_x = 0
        for sec in self.world_data:
            sec_len = 0
            if sec['type'] == 'straight':
                sec_len = sec['length']
            elif sec['type'] == 'branch':
                sec_len = max(p['length'] for p in sec['paths'])
            
            if cursor_x <= world_x < cursor_x + sec_len:
                return sec, cursor_x
            cursor_x += sec_len
        return None, None

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            # Kéo thả file để load
            if event.type == pygame.DROPFILE:
                self.load_level(event.file)
            
            # Bàn phím
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                # Chuyển tool
                if event.key == pygame.K_r: self.tool = 'add_real'
                if event.key == pygame.K_f: self.tool = 'add_fake'
                if event.key == pygame.K_d: self.tool = 'delete'
                # Lưu file
                if event.key == pygame.K_s and pygame.key.get_mods() & pygame.KMOD_CTRL:
                    self.save_level()

            # Click chuột
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: # Chuột trái
                    mouse_world_pos = self.screen_to_world(pygame.mouse.get_pos())
                    
                    if self.tool in ['add_real', 'add_fake']:
                        self.add_obstacle(mouse_world_pos)
                    elif self.tool == 'delete':
                        self.delete_obstacle(mouse_world_pos)

        # Giữ phím để cuộn
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]: self.view_x -= 10
        if keys[pygame.K_RIGHT]: self.view_x += 10

    def add_obstacle(self, world_pos):
        section, sec_start_x = self.find_section_at(world_pos[0])
        if not section:
            print("Cannot add obstacle: No platform section here.")
            return

        kind = 'real' if self.tool == 'add_real' else 'fake'
        
        new_ob = {
            "x": world_pos[0] - sec_start_x, # Tọa độ x tương đối với section
            "y": "ground", # Mặc định là ground
            "kind": kind
        }
        
        # Hiện tại chỉ hỗ trợ thêm vào section straight đơn giản
        if section['type'] == 'straight':
            if 'obstacles' not in section:
                section['obstacles'] = []
            section['obstacles'].append(new_ob)
            print(f"Added {kind} obstacle at {world_pos[0]}")
        else:
            # Tạm thời chỉ thêm vào path đầu tiên của branch
            section['paths'][0]['obstacles'].append(new_ob)
            print(f"Added {kind} obstacle to first path of branch at {world_pos[0]}")


    def delete_obstacle(self, world_pos):
        # Duyệt qua tất cả các chướng ngại vật để tìm cái nào bị click
        for sec in self.world_data:
            cursor_x = sec.get('platform', {}).x if sec['type'] == 'straight' else sec.get('branch_x', 0)
            
            all_obstacles = []
            if sec['type'] == 'straight':
                all_obstacles = sec.get('obstacles', [])
            else:
                for path in sec['paths']:
                    all_obstacles.extend(path.get('obstacles', []))

            for ob in all_obstacles:
                ob_world_x = cursor_x + ob['x']
                ob_rect = pygame.Rect(ob_world_x, GROUND_Y - 50, 30, 50) # Giả sử h=50, w=30
                if ob_rect.collidepoint(world_pos):
                    print(f"Deleting obstacle at {ob_world_x}")
                    all_obstacles.remove(ob)
                    return


    def load_level(self, filepath):
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            return
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            self.world_data = data['sections']
            self.current_file = filepath
            self.view_x = 0
            pygame.display.set_caption(f"Level Editor - {os.path.basename(filepath)}")
            print(f"Loaded level: {filepath}")
        except Exception as e:
            print(f"Error loading level: {e}")

    def save_level(self):
        if not self.current_file:
            print("No level loaded to save.")
            return
        try:
            data_to_save = {"sections": self.world_data}
            with open(self.current_file, 'w') as f:
                json.dump(data_to_save, f, indent=2)
            print(f"Successfully saved to {self.current_file}")
        except Exception as e:
            print(f"Error saving level: {e}")

    def draw(self):
        self.screen.fill((20, 20, 30)) # Nền tối
        
        # Vẽ nền đất
        pygame.draw.rect(self.screen, (50,50,50), (0, GROUND_Y, SCREEN_W, SCREEN_H - GROUND_Y))

        # Vẽ các platform và obstacles
        cursor_x = 0
        for sec in self.world_data:
            if sec['type'] == 'straight':
                plat = sec['platform']
                plat_y = sec.get('platform_y', GROUND_Y)
                pygame.draw.rect(self.screen, (80,80,80), (cursor_x - self.view_x, plat_y, sec['length'], 6))
                for ob in sec.get('obstacles', []):
                    color = (200,40,40) if ob['kind'] == 'real' else (120,120,220)
                    pygame.draw.rect(self.screen, color, (cursor_x + ob['x'] - self.view_x, plat_y - 50, 30, 50))
                cursor_x += sec['length']
            elif sec['type'] == 'branch':
                branch_x = sec['branch_x']
                for i, path in enumerate(sec['paths']):
                    plat_y = GROUND_Y + path['offset_y']
                    color = (100,150,100) if i==0 else (100,100,150)
                    pygame.draw.rect(self.screen, color, (branch_x - self.view_x, plat_y, path['length'], 6))
                    for ob in path.get('obstacles', []):
                        color = (200,40,40) if ob['kind'] == 'real' else (120,120,220)
                        pygame.draw.rect(self.screen, color, (branch_x + ob['x'] - self.view_x, plat_y - 50, 30, 50))
                cursor_x = branch_x + max(p['length'] for p in sec['paths'])

        # Vẽ UI
        tool_text = self.font.render(f"Tool: {self.tool.upper()}", True, (255, 255, 255))
        controls_text = self.font.render("R: Add Real | F: Add Fake | D: Delete | CTRL+S: Save | Drag&Drop: Load", True, (200,200,200))
        self.screen.blit(tool_text, (10, 10))
        self.screen.blit(controls_text, (10, 40))

        pygame.display.flip()

    def run(self):
        self.load_level(DEFAULT_LEVEL) # Load level mặc định khi bắt đầu
        while self.running:
            self.handle_events()
            self.draw()
            self.clock.tick(FPS)
        #pygame.quit()