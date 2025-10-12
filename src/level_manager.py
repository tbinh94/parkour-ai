# level_manager.py
import pygame
import json
import os
from config import *

# --- CẤU HÌNH MENU MÀN CHƠI ---
LEVEL_CONFIG = [
    {"display_name": "1. Tutorial", "filename": "level_tutorial.json"},
    {"display_name": "2. The Dark Path", "filename": "level1.json"},
    {"display_name": "3. Haunted Bridge", "filename": "level2.json"},
    {"display_name": "4. Crimson Keep", "filename": "level3.json"},
    {"display_name": "5. The Gauntlet", "filename": "level4.json"},
    {"display_name": "6. Road to The Shrine", "filename": "level5.json"}
]

class LevelManager:
    def __init__(self, screen):
        self.screen = screen
        self.font_title = pygame.font.SysFont("Arial", 40, bold=True)
        self.font_item = pygame.font.SysFont("Arial", 30)
        self.font_status = pygame.font.SysFont("Arial", 20)
        
        self.progress_file = "progress.json"
        self.completed_levels = self.load_progress()
        
        self.menu_items = []
        self.menu_items.extend(LEVEL_CONFIG)
        
        self.menu_items.append({"display_name": "Level Editor", "filename": "EDITOR"})
        
        self.selected_index = 0
        self.running = True

    def load_progress(self):
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    # SỬA LỖI TẠI ĐÂY: Thêm (f) vào hàm json.load
                    return set(json.load(f))
            except json.JSONDecodeError:
                # Nếu file progress bị lỗi hoặc trống, trả về set rỗng
                return set()
        return set()

    def save_progress(self):
        with open(self.progress_file, 'w') as f:
            json.dump(list(self.completed_levels), f)

    def complete_level(self, filename):
        if filename not in self.completed_levels:
            self.completed_levels.add(filename)
            self.save_progress()
            print(f"Progress saved: Completed {filename}")

    def draw(self):
        self.screen.fill((20, 10, 30))
        
        title_surf = self.font_title.render("Select a Level", True, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(SCREEN_W / 2, 60))
        self.screen.blit(title_surf, title_rect)

        for i, item in enumerate(self.menu_items):
            y_pos = 150 + i * 60
            
            is_level = item["filename"].endswith(".json")
            is_unlocked = True
            if is_level:
                if i > 0:
                    prev_level_file = self.menu_items[i-1]["filename"]
                    if prev_level_file.endswith(".json") and prev_level_file not in self.completed_levels:
                        is_unlocked = False
            
            rect = pygame.Rect(SCREEN_W / 2 - 300, y_pos, 600, 50)
            
            border_color = (255, 215, 0) if i == self.selected_index else (100, 80, 120)
            text_color = (255, 255, 255) if is_unlocked else (100, 100, 100)
            
            pygame.draw.rect(self.screen, border_color, rect, 2)
            
            display_text = item["display_name"]
            if not is_unlocked:
                display_text = "🔒 LOCKED"
            
            item_surf = self.font_item.render(display_text, True, text_color)
            item_rect = item_surf.get_rect(center=rect.center)
            item_rect.left = rect.left + 20
            self.screen.blit(item_surf, item_rect)
            
            if is_level and item["filename"] in self.completed_levels:
                status_surf = self.font_status.render("✓ COMPLETED", True, (120, 255, 120))
                status_rect = status_surf.get_rect(center=rect.center)
                status_rect.right = rect.right - 20
                self.screen.blit(status_surf, status_rect)

        pygame.display.flip()

    def handle_input(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    self.selected_index = (self.selected_index - 1) % len(self.menu_items)
                elif event.key == pygame.K_DOWN:
                    self.selected_index = (self.selected_index + 1) % len(self.menu_items)
                elif event.key == pygame.K_RETURN:
                    selected_item = self.menu_items[self.selected_index]
                    filename = selected_item["filename"]

                    is_level = filename.endswith(".json")
                    is_unlocked = True
                    if is_level and self.selected_index > 0:
                        prev_level_file = self.menu_items[self.selected_index-1]["filename"]
                        if prev_level_file.endswith(".json") and prev_level_file not in self.completed_levels:
                            is_unlocked = False

                    if is_unlocked:
                        return filename
                elif event.key == pygame.K_ESCAPE:
                    return None
        return "CONTINUE"

    def run(self):
        while self.running:
            result = self.handle_input()
            if result != "CONTINUE":
                return result
            self.draw()
            pygame.time.Clock().tick(FPS)