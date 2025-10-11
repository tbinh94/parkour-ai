import pygame
import json
import os
from config import *

class LevelManager:
    """Quản lý và hiển thị menu chọn level"""
    
    def __init__(self, screen):
        #pygame.init()
        
        self.screen = screen
        pygame.display.set_caption("Dark Fantasy Parkour - Level Select")
        self.clock = pygame.time.Clock()
        
        # Fonts
        self.title_font = pygame.font.SysFont(None, 72)
        self.level_font = pygame.font.SysFont(None, 48)
        self.info_font = pygame.font.SysFont(None, 24)
        
        # Colors - Dark Fantasy Theme
        self.colors = {
            'bg': (15, 10, 25),
            'bg_gradient_top': (20, 15, 35),
            'bg_gradient_bottom': (10, 5, 20),
            'title': (220, 180, 80),
            'level_normal': (180, 160, 140),
            'level_hover': (255, 220, 100),
            'level_locked': (80, 70, 90),
            'difficulty_easy': (100, 200, 100),
            'difficulty_medium': (200, 200, 100),
            'difficulty_hard': (200, 100, 100),
            'border': (100, 80, 120),
            'text_info': (200, 190, 180)
        }
        
        # Level data
        self.levels = self.scan_levels()
        self.selected_level = 0
        self.running = True
        
        # Load progress
        self.progress = self.load_progress()
    
    def scan_levels(self):
        """Tìm tất cả file level*.json"""
        levels = []
        
        # Predefined order
        level_order = [
            'level_tutorial.json',
            'level1.json', 
            'level2.json', 
            'level3.json', 
            'level4.json'
        ]
        
        for filename in level_order:
            if os.path.exists(filename):
                info = self.get_level_info(filename)
                levels.append({
                    'filename': filename,
                    'name': info['name'],
                    'difficulty': info['difficulty'],
                    'length': info['length'],
                    'monsters': info['monsters']
                })
        
        # Add any other level*.json files not in order
        for filename in os.listdir('.'):
            if filename.startswith('level') and filename.endswith('.json'):
                if filename not in level_order:
                    info = self.get_level_info(filename)
                    levels.append({
                        'filename': filename,
                        'name': info['name'],
                        'difficulty': info['difficulty'],
                        'length': info['length'],
                        'monsters': info['monsters']
                    })
        
        return levels
    
    def get_level_info(self, filename):
        """Phân tích level file để lấy thông tin"""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            sections = data.get('sections', [])
            total_length = 0
            real_monsters = 0
            fake_monsters = 0
            
            for sec in sections:
                if sec['type'] == 'straight':
                    total_length += sec['length']
                    for ob in sec.get('obstacles', []):
                        if ob['kind'] == 'real':
                            real_monsters += 1
                        else:
                            fake_monsters += 1
                else:  # branch
                    max_len = max([p['length'] for p in sec['paths']])
                    total_length += max_len
                    for path in sec['paths']:
                        for ob in path.get('obstacles', []):
                            if ob['kind'] == 'real':
                                real_monsters += 1
                            else:
                                fake_monsters += 1
            
            # Determine difficulty
            monster_density = (real_monsters + fake_monsters) / (total_length / 100)
            if monster_density < 2:
                difficulty = 1
            elif monster_density < 3:
                difficulty = 2
            elif monster_density < 4:
                difficulty = 3
            elif monster_density < 5:
                difficulty = 4
            else:
                difficulty = 5
            
            # Name mapping
            name_map = {
                'level_tutorial.json': 'Tutorial',
                'level1.json': 'The Dark Path',
                'level2.json': 'Haunted Bridge',
                'level3.json': 'Shadow Realm',
                'level4.json': 'Castle Ruins'
            }
            
            name = name_map.get(filename, filename.replace('.json', '').replace('_', ' ').title())
            
            return {
                'name': name,
                'difficulty': difficulty,
                'length': total_length,
                'monsters': {'real': real_monsters, 'fake': fake_monsters}
            }
        except Exception as e:
            print(f"Error reading {filename}: {e}")
            return {
                'name': filename,
                'difficulty': 1,
                'length': 0,
                'monsters': {'real': 0, 'fake': 0}
            }
    
    def load_progress(self):
        """Load player progress"""
        try:
            with open('progress.json', 'r') as f:
                return json.load(f)
        except:
            return {'completed': [], 'high_scores': {}}
    
    def save_progress(self):
        """Save player progress"""
        with open('progress.json', 'w') as f:
            json.dump(self.progress, f, indent=2)
    
    def is_level_unlocked(self, level_idx):
        """Check if level is unlocked"""
        if level_idx == 0:
            return True  # Tutorial always unlocked
        
        # Level unlocked if previous level completed
        if level_idx > 0 and level_idx < len(self.levels):
            prev_level = self.levels[level_idx - 1]['filename']
            return prev_level in self.progress['completed']
        
        return False
    
    def draw_gradient_bg(self):
        """Vẽ background gradient"""
        for y in range(SCREEN_H):
            ratio = y / SCREEN_H
            r = int(self.colors['bg_gradient_top'][0] * (1 - ratio) + self.colors['bg_gradient_bottom'][0] * ratio)
            g = int(self.colors['bg_gradient_top'][1] * (1 - ratio) + self.colors['bg_gradient_bottom'][1] * ratio)
            b = int(self.colors['bg_gradient_top'][2] * (1 - ratio) + self.colors['bg_gradient_bottom'][2] * ratio)
            pygame.draw.line(self.screen, (r, g, b), (0, y), (SCREEN_W, y))
    
    def render(self):
        """Render level selection screen"""
        self.draw_gradient_bg()
        
        # Title
        title = self.title_font.render("DARK FANTASY PARKOUR", True, self.colors['title'])
        title_rect = title.get_rect(center=(SCREEN_W // 2, 60))
        self.screen.blit(title, title_rect)
        
        # Subtitle
        subtitle = self.info_font.render("Select Your Quest", True, self.colors['text_info'])
        subtitle_rect = subtitle.get_rect(center=(SCREEN_W // 2, 110))
        self.screen.blit(subtitle, subtitle_rect)
        
        # Level list
        start_y = 160
        level_height = 80
        
        for i, level in enumerate(self.levels):
            y = start_y + i * level_height
            
            # Check if unlocked
            unlocked = self.is_level_unlocked(i)
            
            # Level box
            box_rect = pygame.Rect(100, y, SCREEN_W - 200, level_height - 10)
            
            # Border color
            if i == self.selected_level and unlocked:
                border_color = self.colors['level_hover']
                border_width = 3
            else:
                border_color = self.colors['border']
                border_width = 2
            
            # Draw box
            pygame.draw.rect(self.screen, (30, 25, 40), box_rect)
            pygame.draw.rect(self.screen, border_color, box_rect, border_width)
            
            if unlocked:
                # Level name
                name_color = self.colors['level_hover'] if i == self.selected_level else self.colors['level_normal']
                name_text = self.level_font.render(level['name'], True, name_color)
                self.screen.blit(name_text, (120, y + 10))
                
                # Difficulty stars
                diff_color = self.colors['difficulty_easy']
                if level['difficulty'] >= 3:
                    diff_color = self.colors['difficulty_medium']
                if level['difficulty'] >= 4:
                    diff_color = self.colors['difficulty_hard']
                
                star_text = "★" * level['difficulty'] + "☆" * (5 - level['difficulty'])
                star_surf = self.info_font.render(star_text, True, diff_color)
                self.screen.blit(star_surf, (120, y + 45))
                
                # Info
                info_text = f"Length: {level['length']}px | Monsters: {level['monsters']['real']} Real, {level['monsters']['fake']} Fake"
                info_surf = self.info_font.render(info_text, True, self.colors['text_info'])
                self.screen.blit(info_surf, (300, y + 45))
                
                # Completed badge
                if level['filename'] in self.progress['completed']:
                    badge = self.info_font.render("✓ COMPLETED", True, (100, 255, 100))
                    self.screen.blit(badge, (SCREEN_W - 200, y + 25))
            else:
                # Locked level
                lock_text = self.level_font.render("🔒 LOCKED", True, self.colors['level_locked'])
                lock_rect = lock_text.get_rect(center=box_rect.center)
                self.screen.blit(lock_text, lock_rect)
        
        # Instructions
        instr_y = SCREEN_H - 60
        instructions = [
            "↑↓ Select Level | ENTER Play | E Level Editor | ESC Quit"
        ]
        
        for i, text in enumerate(instructions):
            surf = self.info_font.render(text, True, self.colors['text_info'])
            rect = surf.get_rect(center=(SCREEN_W // 2, instr_y + i * 25))
            self.screen.blit(surf, rect)
        
        pygame.display.flip()
    
    def handle_input(self):
        """Handle user input"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                return None
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                    return None
                
                elif event.key == pygame.K_UP:
                    self.selected_level = max(0, self.selected_level - 1)
                
                elif event.key == pygame.K_DOWN:
                    self.selected_level = min(len(self.levels) - 1, self.selected_level + 1)
                
                elif event.key == pygame.K_RETURN:
                    if self.is_level_unlocked(self.selected_level):
                        return self.levels[self.selected_level]['filename']
                
                elif event.key == pygame.K_e:
                    # Open level editor
                    return 'EDITOR'
        
        return 'MENU'
    
    def run(self):
        """Main loop"""
        self.running = True
        while self.running:
            result = self.handle_input()
            
            # Nếu người dùng chọn gì đó (level, editor) hoặc thoát (None)
            if result != 'MENU':
                return result # Trả về lựa chọn và kết thúc vòng lặp
            
            self.render()
            self.clock.tick(FPS)
        
        return None # Trả về None nếu vòng lặp kết thúc (do self.running = False)

def run_level_manager():
    """Run the level selection screen"""
    manager = LevelManager()
    selected = manager.run()
    pygame.quit()
    return selected

if __name__ == "__main__":
    result = run_level_manager()
    
    if result == 'EDITOR':
        print("Opening level editor...")
        import level_editor
        level_editor.LevelEditor().run()
    elif result:
        print(f"Selected level: {result}")
        # Ở đây bạn có thể chạy game với level đã chọn
        # from main import play_manually
        # play_manually(result)
    else:
        print("Exiting...")
        import sys
        sys.exit()