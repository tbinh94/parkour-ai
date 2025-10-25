# level_manager.py - AUTO-DISCOVERY LEVEL SYSTEM WITH MODERN UI
import pygame
import json
import os
import glob
import math
from config import *

class LevelManager:
    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()
        
        # Fonts
        self.font_title = pygame.font.SysFont("Arial", 50, bold=True)
        self.font_subtitle = pygame.font.SysFont("Arial", 24)
        self.font_item = pygame.font.SysFont("Arial", 28, bold=True)
        self.font_meta = pygame.font.SysFont("Arial", 18)
        self.font_status = pygame.font.SysFont("Arial", 20, bold=True)
        
        self.progress_file = "progress.json"
        self.completed_levels = self.load_progress()
        
        regular_levels, special_modes = self.discover_levels()
        
        editor_item = {
            "display_name": "🛠️ Level Editor",
            "filename": "EDITOR",
            "is_editor": True,
            "difficulty": "",
            "description": "Create and design your own levels"
        }
        
        self.menu_items = regular_levels + special_modes + [editor_item]
        
        self.selected_index = 0
        self.running = True
        self.animation_progress = 0
        self.hover_progress = [0] * len(self.menu_items)
        self.scroll_offset = 0
        self.visible_items = 6

    def discover_levels(self):
        levels_dir = "levels"
        level_files = glob.glob(os.path.join(levels_dir, "*.json"))
        
        discovered_levels = []
        special_modes = []
        
        for filepath in level_files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                metadata = data.get("metadata", {})
                is_special_mode = data.get("mode") == "endless"

                level_info = {
                    "display_name": metadata.get("display_name", os.path.basename(filepath)),
                    "filename": os.path.basename(filepath),
                    "difficulty": metadata.get("difficulty", "Normal"),
                    "description": metadata.get("description", ""),
                    "is_editor": False,
                    "is_special_mode": is_special_mode
                }

                if is_special_mode:
                    special_modes.append(level_info)
                else:
                    level_info["order"] = metadata.get("order", 999)
                    discovered_levels.append(level_info)
                
            except Exception as e:
                print(f"⚠️ Warning: Could not load {filepath}: {e}")
        
        discovered_levels.sort(key=lambda x: x["order"])
        
        print(f"✓ Discovered {len(discovered_levels)} regular levels and {len(special_modes)} special modes.")
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
        item_data = next((item for item in self.menu_items if item["filename"] == filename), None)
        if item_data and item_data.get("is_special_mode"):
            print(f"ℹ️ Endless mode run ended. No progress saved.")
            return

        if filename not in self.completed_levels:
            self.completed_levels.add(filename)
            self.save_progress()
            print(f"✓ Progress saved: {filename}")

    def get_difficulty_color(self, difficulty):
        """Trả về màu dựa trên độ khó"""
        colors = {
            "Easy": (100, 200, 100),
            "Normal": (100, 150, 255),
            "Hard": (255, 150, 100),
            "Expert": (255, 100, 150),
        }
        return colors.get(difficulty, (150, 150, 150))

    def draw_gradient_rect(self, x, y, w, h, color1, color2):
        """Vẽ hình chữ nhật với gradient"""
        for i in range(h):
            ratio = i / h
            r = int(color1[0] * (1 - ratio) + color2[0] * ratio)
            g = int(color1[1] * (1 - ratio) + color2[1] * ratio)
            b = int(color1[2] * (1 - ratio) + color2[2] * ratio)
            pygame.draw.line(self.screen, (r, g, b), (x, y + i), (x + w, y + i))

    def draw(self):
        # Background with gradient
        self.draw_gradient_rect(0, 0, SCREEN_W, SCREEN_H, (15, 8, 25), (25, 15, 35))
        
        # Title section with glow effect
        title_surf = self.font_title.render("SELECT LEVEL", True, (255, 255, 255))
        title_rect = title_surf.get_rect(center=(SCREEN_W / 2, 50))
        
        # Glow shadow
        glow_surf = self.font_title.render("SELECT LEVEL", True, (150, 100, 200))
        for offset in range(4, 0, -1):
            alpha_surf = glow_surf.copy()
            alpha_surf.set_alpha(50)
            self.screen.blit(alpha_surf, (title_rect.x - offset, title_rect.y - offset))
        
        self.screen.blit(title_surf, title_rect)
        
        # Subtitle
        subtitle_surf = self.font_subtitle.render("Choose your adventure", True, (200, 180, 220))
        self.screen.blit(subtitle_surf, (30, 110))
        
        # Update animation
        self.animation_progress = (self.animation_progress + 1) % 60
        
        # Calculate scroll offset
        if len(self.menu_items) > self.visible_items:
            if self.selected_index >= self.visible_items:
                self.scroll_offset = self.selected_index - self.visible_items + 1
            else:
                self.scroll_offset = 0
        
        # Draw items
        for i in range(len(self.menu_items)):
            if i < self.scroll_offset or i >= self.scroll_offset + self.visible_items:
                continue
            
            display_i = i - self.scroll_offset
            y_pos = 170 + display_i * 90
            x_pos = SCREEN_W / 2
            
            item = self.menu_items[i]
            is_selected = i == self.selected_index
            
            # Update hover animation
            target_hover = 1.0 if is_selected else 0.0
            self.hover_progress[i] += (target_hover - self.hover_progress[i]) * 0.15
            
            # Draw item card
            self._draw_item_card(x_pos, y_pos, item, i, self.hover_progress[i])
        
        # Update display ONCE at the end
        pygame.display.flip()
    
    def _draw_item_card(self, x, y, item, index, hover):
        """Vẽ card item với hiệu ứng hover"""
        w, h = 650, 70
        
        # Check if locked
        is_level = not item.get("is_editor", False)
        is_unlocked = True
        
        if is_level and not item.get("is_special_mode", False) and index > 0:
            prev_item = self.menu_items[index - 1]
            if not prev_item.get("is_editor", False) and not prev_item.get("is_special_mode", False):
                if prev_item["filename"] not in self.completed_levels:
                    is_unlocked = False
        
        # Lerp card position for hover effect
        offset_y = -8 * hover
        card_rect = pygame.Rect(x - w/2, y + offset_y, w, h)
        
        # Draw background with gradient based on state
        if not is_unlocked:
            color1, color2 = (60, 60, 80), (50, 50, 70)
        elif index == self.selected_index:
            color1 = (80, 60, 150)
            color2 = (100, 80, 180)
        else:
            color1 = (50, 40, 80)
            color2 = (60, 50, 90)
        
        self.draw_gradient_rect(int(card_rect.x), int(card_rect.y), int(w), int(h), color1, color2)
        
        # Draw border
        border_color = (200, 150, 255) if index == self.selected_index else (120, 100, 150)
        border_width = 3 if index == self.selected_index else 2
        pygame.draw.rect(self.screen, border_color, card_rect, border_width)
        
        # Draw inner glow on hover
        if hover > 0.3:
            inner_rect = card_rect.inflate(-4, -4)
            pygame.draw.rect(self.screen, (150, 100, 200), inner_rect, 1)
        
        # Draw content
        text_color = (255, 255, 255) if is_unlocked else (120, 120, 140)
        
        # Level name
        name_surf = self.font_item.render(item["display_name"], True, text_color)
        name_rect = name_surf.get_rect(topleft=(card_rect.left + 25, card_rect.top + 12))
        self.screen.blit(name_surf, name_rect)
        
        # Difficulty and description (for non-editor items)
        if item.get("difficulty"):
            diff_color = self.get_difficulty_color(item["difficulty"]) if is_unlocked else (100, 100, 120)
            diff_surf = self.font_meta.render(f"⭐ {item['difficulty']}", True, diff_color)
            self.screen.blit(diff_surf, (card_rect.left + 25, card_rect.top + 40))
        
        # Completed status
        if is_level and not item.get("is_special_mode", False) and item["filename"] in self.completed_levels:
            status_surf = self.font_status.render("✓ COMPLETED", True, (100, 255, 100))
            status_rect = status_surf.get_rect(topright=(card_rect.right - 25, card_rect.top + 12))
            self.screen.blit(status_surf, status_rect)
        
        # Locked indicator
        if not is_unlocked:
            lock_surf = self.font_status.render("🔒 LOCKED", True, (255, 150, 100))
            lock_rect = lock_surf.get_rect(center=card_rect.center)
            self.screen.blit(lock_surf, lock_rect)
        
        # Selection indicator
        if index == self.selected_index:
            # Animated arrow
            arrow_x = card_rect.left - 25
            arrow_y = card_rect.centery
            pulse = math.sin(self.animation_progress * 0.1) * 5
            pygame.draw.polygon(self.screen, (200, 150, 255), [
                (arrow_x + pulse, arrow_y),
                (arrow_x - 10 + pulse, arrow_y - 8),
                (arrow_x - 10 + pulse, arrow_y + 8)
            ])

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
                    is_unlocked = True
                    
                    if not selected_item.get("is_special_mode", False) and self.selected_index > 0:
                        prev_item = self.menu_items[self.selected_index - 1]
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
            self.clock.tick(FPS)