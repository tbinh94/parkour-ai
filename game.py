# game.py (FIXED - Proper pygame and assets initialization)
import pygame
import sys

# Thêm 'src' vào sys.path để có thể import các module từ thư mục src
sys.path.append('src') 

from src.main import Game
from src.level_manager import LevelManager
from src.level_editor import LevelEditor
from src.config import *
from src.assets_manager import load_assets
from src.enemy_manager import load_enemies  # 🔥 Import enemy loader

def main_app():
    """
    Hàm điều phối chính của ứng dụng.
    Khởi tạo Pygame MỘT LẦN, sau đó load assets, rồi chạy các trạng thái.
    """
    # ✅ 1. Khởi tạo pygame TRƯỚC
    pygame.init()
    print("✓ Pygame initialized in game.py")
    
    # ✅ 2. Tạo screen
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    
    # ✅ 3. SAU ĐÓ MỚI load assets (vì pygame đã init)
    load_assets()
    
    # ✅ 4. Bắt đầu vòng lặp chính
    app_state = "MENU"
    selected_level = None
    
    # Tạo instance của manager một lần để giữ lại tiến trình
    manager = LevelManager(screen)

    while True:
        if app_state == "MENU":
            user_choice = manager.run()  # Chạy menu
            
            if user_choice == 'EDITOR':
                app_state = "EDITOR"  # Chuyển trạng thái sang EDITOR
            elif user_choice is not None:
                app_state = "GAME"
                selected_level = user_choice
            else:
                break  # Người dùng thoát khỏi menu
                
        elif app_state == "GAME":
            game = Game(screen, selected_level)
            game_result = game.run() 

            if game_result == 'COMPLETED' and selected_level != 'ENDLESS_MODE':
                manager.complete_level(selected_level)
            
            app_state = "MENU"  # Luôn quay lại menu

        elif app_state == "EDITOR":
            editor = LevelEditor(screen)  # Tạo một instance của editor
            editor.run()                  # Chạy editor
            app_state = "MENU"            # Sau khi thoát editor, quay lại menu

    print("Exiting application.")
    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main_app()