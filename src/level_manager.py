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
        
        # (MODIFIED) Tách riêng các loại item trong menu
        regular_levels, special_modes = self.discover_levels()
        
        # (NEW) Tạo item cho Level Editor
        editor_item = {
            "display_name": "🛠️ Level Editor", 
            "filename": "EDITOR",
            "is_editor": True
        }
        
        # (MODIFIED) Ghép các phần lại theo đúng thứ tự mong muốn:
        # 1. Các level thông thường (đã sắp xếp)
        # 2. Các chế độ đặc biệt (Endless Mode)
        # 3. Level Editor
        self.menu_items = regular_levels + special_modes + [editor_item]
        
        self.selected_index = 0
        self.running = True

    def discover_levels(self):
        """
        (MODIFIED) Tự động tìm, phân loại và sắp xếp các level.
        - Phân biệt giữa level thường và các mode đặc biệt (như endless).
        - Trả về 2 danh sách: (regular_levels, special_modes)
        """
        levels_dir = "levels"
        level_files = glob.glob(os.path.join(levels_dir, "*.json"))
        
        discovered_levels = []
        special_modes = [] # (NEW) Danh sách riêng cho các mode đặc biệt
        
        for filepath in level_files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                metadata = data.get("metadata", {})
                
                # (NEW) Kiểm tra xem đây có phải là một mode đặc biệt không
                is_special_mode = data.get("mode") == "endless"

                level_info = {
                    "display_name": metadata.get("display_name", os.path.basename(filepath)),
                    "filename": os.path.basename(filepath),
                    "difficulty": metadata.get("difficulty", "Unknown"),
                    "description": metadata.get("description", ""),
                    "is_editor": False,
                    "is_special_mode": is_special_mode # (NEW) Thêm cờ nhận diện
                }

                # (MODIFIED) Phân loại vào đúng danh sách
                if is_special_mode:
                    special_modes.append(level_info)
                else:
                    # Level thường vẫn cần 'order' để sắp xếp
                    level_info["order"] = metadata.get("order", 999)
                    discovered_levels.append(level_info)
                
            except Exception as e:
                print(f"⚠️ Warning: Could not load metadata from {filepath}: {e}")
        
        # Chỉ sắp xếp danh sách các level thông thường
        discovered_levels.sort(key=lambda x: x["order"])
        
        print(f"✓ Discovered {len(discovered_levels)} regular levels and {len(special_modes)} special modes.")
        for lvl in discovered_levels:
            print(f"  - Level: {lvl['display_name']} (order: {lvl['order']})")
        for mode in special_modes:
            print(f"  - Mode: {mode['display_name']}")
            
        return discovered_levels, special_modes

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
        # Chế độ endless không thể "hoàn thành"
        item_data = next((item for item in self.menu_items if item["filename"] == filename), None)
        if item_data and item_data.get("is_special_mode"):
            print(f"ℹ️ Endless mode run ended. No progress saved.")
            return

        if filename not in self.completed_levels:
            self.completed_levels.add(filename)
            self.save_progress()
            print(f"✓ Progress saved: Completed {filename}")

    def draw(self):
        self.screen.fill((20, 10, 30))
        
        title_surf = self.font_title.render("Select a Level", True, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(SCREEN_W / 2, 60))
        self.screen.blit(title_surf, title_rect)

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
            
            # (MODIFIED) Logic kiểm tra khóa level được cải tiến
            is_level = not item.get("is_editor", False)
            is_unlocked = True
            # Level chỉ bị khóa nếu nó là level thường (không phải special mode) và level trước đó chưa hoàn thành
            if is_level and not item.get("is_special_mode", False) and i > 0:
                prev_item = self.menu_items[i-1]
                # Chỉ xét level trước đó nếu nó cũng là level thường
                if not prev_item.get("is_editor", False) and not prev_item.get("is_special_mode", False):
                    if prev_item["filename"] not in self.completed_levels:
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
            
            # Chỉ hiển thị trạng thái "COMPLETED" cho các level thường
            if is_level and not item.get("is_special_mode", False) and item["filename"] in self.completed_levels:
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
                    
                    if selected_item.get("is_editor", False):
                        return "EDITOR"
                    
                    filename = selected_item["filename"]

                    # (MODIFIED) Logic kiểm tra khóa level được cải tiến
                    is_unlocked = True
                    # Level chỉ bị khóa nếu nó là level thường
                    if not selected_item.get("is_special_mode", False) and self.selected_index > 0:
                        prev_item = self.menu_items[self.selected_index - 1]
                        # Chỉ xét level trước đó nếu nó cũng là level thường
                        if not prev_item.get("is_editor", False) and not prev_item.get("is_special_mode", False):
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