# level_manager.py - AUTO-DISCOVERY LEVEL SYSTEM
import pygame
import json
import os
import glob
from config import *

class LevelManager:
    def __init__(self, screen):
        self.screen = screen
        self.font_title = pygame.font.SysFont("Arial", 40, bold=True)
        self.font_item = pygame.font.SysFont("Arial", 30)
        self.font_status = pygame.font.SysFont("Arial", 20)
        
        self.progress_file = "progress.json"
        self.completed_levels = self.load_progress()
        
        # 🔥 TỰ ĐỘNG QUÉT VÀ LOAD TẤT CẢ LEVEL
        self.menu_items = self.discover_levels()
        
        # Thêm Level Editor vào cuối
        self.menu_items.append({
            "display_name": "🛠️ Level Editor", 
            "filename": "EDITOR",
            "is_editor": True
        })
        
        self.selected_index = 0
        self.running = True

    def discover_levels(self):
        """
        Tự động tìm và sắp xếp tất cả các level từ thư mục levels/
        Mỗi level file phải có metadata trong JSON
        """
        levels_dir = "levels"
        level_files = glob.glob(os.path.join(levels_dir, "*.json"))
        
        discovered_levels = []
        
        for filepath in level_files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Đọc metadata từ file JSON
                metadata = data.get("metadata", {})
                
                level_info = {
                    "display_name": metadata.get("display_name", os.path.basename(filepath)),
                    "filename": os.path.basename(filepath),
                    "order": metadata.get("order", 999),  # Thứ tự hiển thị
                    "difficulty": metadata.get("difficulty", "Unknown"),
                    "description": metadata.get("description", ""),
                    "is_editor": False
                }
                
                discovered_levels.append(level_info)
                
            except Exception as e:
                print(f"⚠️ Warning: Could not load metadata from {filepath}: {e}")
        
        # Sắp xếp theo thứ tự
        discovered_levels.sort(key=lambda x: x["order"])
        
        print(f"✓ Discovered {len(discovered_levels)} levels:")
        for lvl in discovered_levels:
            print(f"  - {lvl['display_name']} (order: {lvl['order']})")
        
        return discovered_levels

    def load_progress(self):
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    return set(json.load(f))
            except json.JSONDecodeError:
                return set()
        return set()

    def save_progress(self):
        with open(self.progress_file, 'w') as f:
            json.dump(list(self.completed_levels), f)

    def complete_level(self, filename):
        if filename not in self.completed_levels:
            self.completed_levels.add(filename)
            self.save_progress()
            print(f"✓ Progress saved: Completed {filename}")

    def draw(self):
        self.screen.fill((20, 10, 30))
        
        title_surf = self.font_title.render("Select a Level", True, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(SCREEN_W / 2, 60))
        self.screen.blit(title_surf, title_rect)

        # Tính toán scroll nếu có quá nhiều level
        visible_items = 8
        scroll_offset = 0
        if len(self.menu_items) > visible_items:
            if self.selected_index >= visible_items:
                scroll_offset = self.selected_index - visible_items + 1

        for i in range(len(self.menu_items)):
            if i < scroll_offset or i >= scroll_offset + visible_items:
                continue
                
            item = self.menu_items[i]
            y_pos = 150 + (i - scroll_offset) * 60
            
            # Kiểm tra level có bị khóa không
            is_level = not item.get("is_editor", False)
            is_unlocked = True
            if is_level and i > 0:
                prev_item = self.menu_items[i-1]
                if not prev_item.get("is_editor", False):
                    if prev_item["filename"] not in self.completed_levels:
                        is_unlocked = False
            
            rect = pygame.Rect(SCREEN_W / 2 - 300, y_pos, 600, 50)
            
            # Highlight nếu được chọn
            border_color = (255, 215, 0) if i == self.selected_index else (100, 80, 120)
            text_color = (255, 255, 255) if is_unlocked else (100, 100, 100)
            
            pygame.draw.rect(self.screen, border_color, rect, 2)
            
            # Hiển thị tên level
            display_text = item["display_name"]
            if not is_unlocked:
                display_text = "🔒 LOCKED"
            
            item_surf = self.font_item.render(display_text, True, text_color)
            item_rect = item_surf.get_rect(center=rect.center)
            item_rect.left = rect.left + 20
            self.screen.blit(item_surf, item_rect)
            
            # Hiển thị trạng thái completed
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
                    
                    # Nếu là editor, trả về "EDITOR"
                    if selected_item.get("is_editor", False):
                        return "EDITOR"
                    
                    filename = selected_item["filename"]

                    # Kiểm tra level có bị khóa không
                    is_unlocked = True
                    if self.selected_index > 0:
                        prev_item = self.menu_items[self.selected_index - 1]
                        if not prev_item.get("is_editor", False):
                            if prev_item["filename"] not in self.completed_levels:
                                is_unlocked = False

                    if is_unlocked:
                        return filename
                    else:
                        print("⚠️ Level is locked! Complete previous level first.")
                        
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