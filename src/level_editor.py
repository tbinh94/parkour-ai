# level_editor.py
import pygame
import json
import sys
import os
from config import *

# CẢI TIẾN: Thêm hằng số cho editor
GRID_SIZE = 20
RESIZE_HANDLE_WIDTH = 10

class LevelEditor:
    def __init__(self, screen):
        self.screen = screen
        pygame.display.set_caption("Level Editor")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 24)
        
        self.running = True
        self.world_data = []
        self.view_x = 0
        self.tool = 'add_real' # add_real, add_fake, delete, add_straight
        self.current_file = None
        self.status_message = ""
        self.status_timer = 0

        # CẢI TIẾN: Thêm trạng thái cho việc thay đổi kích thước
        self.resizing_info = None # Sẽ lưu trữ { 'section': sec, 'path_index': idx, 'start_x': mouse_x }

    def set_status(self, message, duration=120):
        self.status_message = message
        self.status_timer = duration

    def new_level(self):
        self.world_data = []
        self.current_file = None
        self.view_x = 0
        pygame.display.set_caption("Level Editor - New Level*")
        self.set_status("Started a new level.")

    def screen_to_world(self, screen_pos):
        return (screen_pos[0] + self.view_x, screen_pos[1])

    # CẢI TIẾN: Tìm kiếm cạnh để resize
    def find_resizable_edge_at(self, world_pos):
        cursor_x = 0
        for sec in self.world_data:
            if sec['type'] == 'straight':
                sec_len = sec.get('length', 0)
                plat_y = sec.get('platform_y', GROUND_Y)
                edge_x = cursor_x + sec_len
                if abs(world_pos[0] - edge_x) < RESIZE_HANDLE_WIDTH and abs(world_pos[1] - plat_y) < 20:
                    return sec, None # None for path_index
                cursor_x += sec_len
            elif sec['type'] == 'branch':
                branch_x = sec.get('branch_x', cursor_x)
                sec_len = 0
                for i, path in enumerate(sec.get('paths', [])):
                    path_len = path.get('length', 0)
                    plat_y = GROUND_Y + path.get('offset_y', 0)
                    edge_x = branch_x + path_len
                    if abs(world_pos[0] - edge_x) < RESIZE_HANDLE_WIDTH and abs(world_pos[1] - plat_y) < 20:
                        return sec, i
                    sec_len = max(sec_len, path_len)
                cursor_x = branch_x + sec_len
        return None, None

    def find_section_and_path_at(self, world_x, world_y):
        cursor_x = 0
        for sec in self.world_data:
            if sec['type'] == 'straight':
                sec_len = sec.get('length', 0)
                if cursor_x <= world_x < cursor_x + sec_len:
                    return sec, cursor_x, None
                cursor_x += sec_len
            elif sec['type'] == 'branch':
                branch_start_x = sec.get('branch_x', cursor_x)
                paths = sec.get('paths', [])
                sec_len = max(p.get('length', 0) for p in paths) if paths else 0
                if branch_start_x <= world_x < branch_start_x + sec_len:
                    for i, path in enumerate(paths):
                        path_y = GROUND_Y + path.get('offset_y', 0)
                        if abs(world_y - path_y) < 50:
                            return sec, branch_start_x, i
                cursor_x = branch_start_x + sec_len
        return None, None, None

    def handle_events(self):
        mouse_pos = pygame.mouse.get_pos()
        world_pos = self.screen_to_world(mouse_pos)
        
        # CẢI TIẾN: Thay đổi con trỏ chuột khi hover
        resizable_sec, _ = self.find_resizable_edge_at(world_pos)
        if resizable_sec:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_SIZEWE)
        else:
            pygame.mouse.set_cursor(pygame.SYSTEM_CURSOR_ARROW)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            
            if event.type == pygame.DROPFILE:
                self.load_level(event.file)
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: self.running = False
                if event.key == pygame.K_r: self.tool = 'add_real'
                if event.key == pygame.K_f: self.tool = 'add_fake'
                if event.key == pygame.K_d: self.tool = 'delete'
                if event.key == pygame.K_a: self.tool = 'add_straight' # Thêm section
                if event.key == pygame.K_s and pygame.key.get_mods() & pygame.KMOD_CTRL:
                    self.save_level(save_as=False)
                if event.key == pygame.K_s and pygame.key.get_mods() & pygame.KMOD_SHIFT:
                    self.save_level(save_as=True) # Save As
                if event.key == pygame.K_n and pygame.key.get_mods() & pygame.KMOD_CTRL:
                    self.new_level() # New Level

            # CẢI TIẾN: Logic kéo thả để resize
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    section, path_idx = self.find_resizable_edge_at(world_pos)
                    if section:
                        self.resizing_info = {
                            'section': section, 
                            'path_index': path_idx, 
                            'start_mouse_x': world_pos[0]
                        }
                    elif self.tool in ['add_real', 'add_fake']:
                        self.add_obstacle(world_pos)
                    elif self.tool == 'delete':
                        self.delete_obstacle(world_pos)
                    elif self.tool == 'add_straight':
                        self.add_straight_section()

            if event.type == pygame.MOUSEMOTION:
                if self.resizing_info:
                    dx = world_pos[0] - self.resizing_info['start_mouse_x']
                    target = None
                    if self.resizing_info['section']['type'] == 'straight':
                        target = self.resizing_info['section']
                    elif self.resizing_info['path_index'] is not None:
                        target = self.resizing_info['section']['paths'][self.resizing_info['path_index']]
                    
                    if target:
                        original_length = target.get('length', 0) - dx
                        new_length = original_length + (world_pos[0] - self.resizing_info['start_mouse_x'])
                        target['length'] = max(GRID_SIZE * 2, int(new_length / GRID_SIZE) * GRID_SIZE) # Snap to grid

            if event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    self.resizing_info = None

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]: self.view_x = max(0, self.view_x - 15)
        if keys[pygame.K_RIGHT]: self.view_x += 15
    
    # CẢI TIẾN: Hàm thêm section mới
    def add_straight_section(self):
        new_section = {
            "type": "straight",
            "length": 400,
            "platform_y": 360,
            "obstacles": []
        }
        self.world_data.append(new_section)
        self.set_status("Added a new straight section.")

    def add_obstacle(self, world_pos):
        section, sec_start_x, path_idx = self.find_section_and_path_at(world_pos[0], world_pos[1])
        if not section:
            self.set_status("Cannot add: No platform section here.")
            return

        kind = 'real' if self.tool == 'add_real' else 'fake'
        rel_x = world_pos[0] - sec_start_x
        new_ob = {
            "x": int(rel_x / GRID_SIZE) * GRID_SIZE, # Snap to grid
            "y": "ground",
            "kind": kind
        }
        
        target_list = None
        if section['type'] == 'straight':
            if 'obstacles' not in section: section['obstacles'] = []
            target_list = section['obstacles']
        elif section['type'] == 'branch' and path_idx is not None:
            path = section['paths'][path_idx]
            if 'obstacles' not in path: path['obstacles'] = []
            target_list = path['obstacles']

        if target_list is not None:
            target_list.append(new_ob)
            target_list.sort(key=lambda ob: ob['x'])
            self.set_status(f"Added {kind} obstacle.")

    def delete_obstacle(self, world_pos):
        cursor_x = 0
        for sec in self.world_data:
            sec_start_x = 0
            paths_to_check = []
            if sec['type'] == 'straight':
                sec_start_x = cursor_x
                paths_to_check.append({'obstacles': sec.get('obstacles', []), 'y_offset': sec.get('platform_y', GROUND_Y) - GROUND_Y})
            elif sec['type'] == 'branch':
                sec_start_x = sec.get('branch_x', cursor_x)
                paths_to_check.extend([{'obstacles': p.get('obstacles', []), 'y_offset': p.get('offset_y', 0)} for p in sec.get('paths', [])])
            
            for path_info in paths_to_check:
                obstacles_list = path_info['obstacles']
                path_y = GROUND_Y + path_info['y_offset']
                for ob in reversed(obstacles_list):
                    ob_world_x = sec_start_x + ob['x']
                    ob_rect = pygame.Rect(ob_world_x, path_y - 50, 30, 50)
                    if ob_rect.collidepoint(world_pos):
                        obstacles_list.remove(ob)
                        self.set_status(f"Deleted obstacle at {int(ob_world_x)}.")
                        return

            if sec['type'] == 'straight':
                cursor_x += sec.get('length', 0)
            else:
                sec_len = max(p.get('length', 0) for p in sec.get('paths', [])) if sec.get('paths') else 0
                cursor_x = sec.get('branch_x', cursor_x) + sec_len

    def load_level(self, filepath):
        if not os.path.exists(filepath):
            self.set_status(f"File not found: {filepath}")
            return
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.world_data = data.get('sections', [])
            self.current_file = filepath
            self.view_x = 0
            pygame.display.set_caption(f"Level Editor - {os.path.basename(filepath)}")
            self.set_status(f"Loaded: {os.path.basename(filepath)}")
        except Exception as e:
            self.set_status(f"Error loading level: {e}")

    # CẢI TIẾN: Hỗ trợ "Save As"
    def save_level(self, save_as=False):
        filepath = self.current_file
        if not filepath or save_as:
            # Đây là nơi bạn có thể tích hợp một hộp thoại nhập file phức tạp hơn
            # Tạm thời, chúng ta sẽ lưu với một tên mặc định
            num = 1
            while os.path.exists(f"levels/new_level_{num}.json"):
                num += 1
            filepath = f"levels/new_level_{num}.json"
            self.current_file = filepath
            pygame.display.set_caption(f"Level Editor - {os.path.basename(filepath)}")
            
        try:
            data_to_save = {"sections": self.world_data}
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, indent=2)
            self.set_status(f"Saved to {os.path.basename(filepath)}")
        except Exception as e:
            self.set_status(f"Error saving level: {e}")

    def draw(self):
        self.screen.fill((20, 20, 30))
        
        # Draw grid
        for x in range(0, SCREEN_W, GRID_SIZE):
            pygame.draw.line(self.screen, (30, 30, 40), (x, 0), (x, SCREEN_H))

        cursor_x = 0
        total_length = 0
        for sec in self.world_data:
            if sec['type'] == 'straight':
                plat_y = sec.get('platform_y', GROUND_Y)
                sec_len = sec.get('length', 0)
                pygame.draw.rect(self.screen, (80,80,80), (cursor_x - self.view_x, plat_y, sec_len, 6))
                for ob in sec.get('obstacles', []):
                    color = (200,40,40) if ob['kind'] == 'real' else (120,120,220)
                    pygame.draw.rect(self.screen, color, (cursor_x + ob['x'] - self.view_x, plat_y - 50, 30, 50))
                cursor_x += sec_len
            elif sec['type'] == 'branch':
                branch_x = sec.get('branch_x', cursor_x)
                sec_len = 0
                for i, path in enumerate(sec.get('paths', [])):
                    plat_y = GROUND_Y + path.get('offset_y', 0)
                    path_len = path.get('length', 0)
                    sec_len = max(sec_len, path_len)
                    color = (100,150,100) if i==0 else (100,100,150)
                    pygame.draw.rect(self.screen, color, (branch_x - self.view_x, plat_y, path_len, 6))
                    for ob in path.get('obstacles', []):
                        color = (200,40,40) if ob['kind'] == 'real' else (120,120,220)
                        pygame.draw.rect(self.screen, color, (branch_x + ob['x'] - self.view_x, plat_y - 50, 30, 50))
                cursor_x = branch_x + sec_len
            total_length = cursor_x

        # UI
        controls1 = "R:Real | F:Fake | D:Del | A:Add Straight"
        controls2 = "CTRL+N: New | CTRL+S: Save | SHIFT+S: Save As"
        info_text = self.font.render(f"Tool: {self.tool.upper()} | Level Length: {total_length}px", True, (255, 255, 255))
        controls1_text = self.font.render(controls1, True, (200,200,200))
        controls2_text = self.font.render(controls2, True, (200,200,200))

        self.screen.blit(info_text, (10, 10))
        self.screen.blit(controls1_text, (10, 35))
        self.screen.blit(controls2_text, (10, 60))

        if self.status_timer > 0:
            status_text = self.font.render(self.status_message, True, (255, 255, 0))
            self.screen.blit(status_text, (10, SCREEN_H - 30))
            self.status_timer -= 1

        pygame.display.flip()

    def run(self):
        self.new_level() # Bắt đầu với màn chơi trống
        while self.running:
            self.handle_events()
            self.draw()
            self.clock.tick(FPS)