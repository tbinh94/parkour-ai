# run_game.py (UPDATED)
import pygame
import sys

# Thêm 'src' vào sys.path để có thể import các module từ thư mục src
# Điều này hữu ích khi chạy game.py từ thư mục gốc của dự án.
sys.path.append('src') 

# Cập nhật import: Xóa 'load_all_backgrounds'
from src.main import Game
from src.level_manager import LevelManager
from src.level_editor import LevelEditor
from src.config import *
from src.assets_manager import load_assets

def main_app():
    """
    Hàm điều phối chính của ứng dụng.
    Khởi tạo Pygame MỘT LẦN, sau đó chạy các trạng thái con (Menu, Game, Editor).
    """
    pygame.init()


    
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    load_assets()
    
    app_state = "MENU"
    selected_level = None
    
    # Tạo instance của manager một lần để giữ lại tiến trình
    manager = LevelManager(screen)

    while True:
        if app_state == "MENU":
            user_choice = manager.run() # Chạy menu
            
            # SỬA LẠI ĐOẠN NÀY
            if user_choice == 'EDITOR':
                app_state = "EDITOR"  # Chuyển trạng thái sang EDITOR
            elif user_choice is not None:
                app_state = "GAME"
                selected_level = user_choice
            else:
                break # Người dùng thoát khỏi menu
        elif app_state == "GAME":
            game = Game(screen, selected_level)
            game_result = game.run() 

            if game_result == 'COMPLETED' and selected_level != 'ENDLESS_MODE':
                manager.complete_level(selected_level)
            
            app_state = "MENU" # Luôn quay lại menu

        # THÊM ĐOẠN CODE MỚI NÀY VÀO
        elif app_state == "EDITOR":
            editor = LevelEditor(screen) # Tạo một instance của editor
            editor.run()                 # Chạy editor
            app_state = "MENU"           # Sau khi thoát editor, quay lại menu

    print("Exiting application.")
    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main_app()