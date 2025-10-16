# src/assets_manager.py
import pygame
import json
import os

# --- GLOBAL ASSETS ---
LOADED_THEMES = {}

def load_assets():
    """
    Tải tất cả các theme từ file themes.json bằng đường dẫn an toàn.
    """
    print("🎨 Loading all themes from themes.json...")

    try:
        current_file_path = os.path.abspath(__file__)
        src_dir = os.path.dirname(current_file_path)
        project_root = os.path.dirname(src_dir)
        themes_filepath = os.path.join(project_root, "assets/themes.json")

        print(f"  -> Looking for themes config at: {themes_filepath}")

        with open(themes_filepath, 'r', encoding='utf-8') as f:
            themes_data = json.load(f)
            
    except FileNotFoundError:
        print(f"  ❌ FATAL: themes.json not found at '{themes_filepath}'!")
        return
    except json.JSONDecodeError:
        print("  ❌ FATAL: Could not parse themes.json. Check for syntax errors.")
        return

    for theme in themes_data.get("themes", []):
        theme_name = theme.get("name", "").strip()
        filepath_relative = theme.get("file")
        tile_size = theme.get("tile_size")
        mapping = theme.get("mapping")

        if not all([theme_name, filepath_relative, tile_size, mapping]):
            print(f"  ⚠️ Skipping theme due to missing data: {theme}")
            continue

        filepath_full = os.path.join(project_root, filepath_relative)
        print(f"  -> Loading theme: '{theme_name}' from '{filepath_full}'")
        LOADED_THEMES[theme_name] = {}
        
        try:
            spritesheet = pygame.image.load(filepath_full).convert_alpha()
            sheet_width = spritesheet.get_width()
            sheet_height = spritesheet.get_height()
            
            all_tiles = []
            for y in range(0, sheet_height, tile_size):
                for x in range(0, sheet_width, tile_size):
                    if (x + tile_size <= sheet_width) and (y + tile_size <= sheet_height):
                        rect = pygame.Rect(x, y, tile_size, tile_size)
                        all_tiles.append(spritesheet.subsurface(rect))

            cols = sheet_width // tile_size
            print(f"     - Tileset dimensions: {sheet_width}x{sheet_height} pixels")
            print(f"     - Mapping {len(mapping)} entries...")

            # --- SỬA LỖI TẠI ĐÂY ---
            for tile_name, pos in mapping.items():
                # Bỏ qua các mục không phải là tọa độ hợp lệ (ví dụ: "comment")
                if not isinstance(pos, list) or len(pos) != 2:
                    print(f"     - Skipping non-coordinate entry: '{tile_name}'")
                    continue

                col, row = pos
                if col < cols:
                    tile_index = row * cols + col
                    print(f"     - Mapping '{tile_name}' [{col}, {row}] → index {tile_index}", end="")
                    if tile_index < len(all_tiles):
                        LOADED_THEMES[theme_name][tile_name] = all_tiles[tile_index]
                        print(" ✓ OK")
                    else:
                        print(f" ❌ OUT OF BOUNDS! (max index: {len(all_tiles)-1})")
                else:
                    print(f" ❌ Column {col} >= {cols}")

        except pygame.error as e:
            print(f"     - ❌ Error loading spritesheet for theme '{theme_name}': {e}")
            placeholder = pygame.Surface((tile_size, tile_size))
            placeholder.fill((255, 0, 255))
            LOADED_THEMES[theme_name] = {name: placeholder for name, val in mapping.items() if isinstance(val, list)}

    print(f"✓ Asset loading complete. Loaded {len(LOADED_THEMES)} themes.")