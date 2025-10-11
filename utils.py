"""
Utility functions for Parkour Game
- Random level generator
- Level validator
- Difficulty analyzer
"""

import json
import random
from config import *

def generate_random_level(difficulty=2, sections=5, seed=None):
    """
    Generate random level with specified difficulty
    
    Args:
        difficulty (int): 1-5, higher = harder
        sections (int): Number of sections
        seed (int): Random seed for reproducibility
    
    Returns:
        dict: Level data structure
    """
    if seed:
        random.seed(seed)
    
    # Obstacle density based on difficulty
    obstacle_density = {
        1: (150, 250, 0.3),  # (min_gap, max_gap, real_ratio)
        2: (120, 200, 0.5),
        3: (100, 150, 0.6),
        4: (80, 130, 0.7),
        5: (70, 100, 0.8)
    }
    
    min_gap, max_gap, real_ratio = obstacle_density.get(difficulty, (100, 150, 0.5))
    
    level = {"sections": []}
    
    for i in range(sections):
        # 40% chance for branch, 60% for straight
        if random.random() > 0.6 and i > 0:  # No branch at start
            # Branch section
            cursor_x = sum([
                s.get("length", max([p["length"] for p in s.get("paths", [{"length": 300}])]))
                for s in level["sections"]
            ])
            
            paths = []
            for path_idx in range(2):
                offset = 0 if path_idx == 0 else random.randint(-170, -110)
                length = random.randint(350, 500)
                obstacles = []
                
                x = random.randint(80, 150)
                while x < length - 100:
                    kind = "real" if random.random() < real_ratio else "fake"
                    obstacles.append({
                        "x": x,
                        "y": "ground",
                        "kind": kind
                    })
                    x += random.randint(min_gap + 20, max_gap + 30)
                
                paths.append({
                    "offset_y": offset,
                    "length": length,
                    "obstacles": obstacles
                })
            
            level["sections"].append({
                "type": "branch",
                "branch_x": cursor_x + 50,
                "paths": paths
            })
        else:
            # Straight section
            length = random.randint(400, 700)
            obstacles = []
            
            x = random.randint(80, 150)
            while x < length - 100:
                kind = "real" if random.random() < real_ratio else "fake"
                obstacles.append({
                    "x": x,
                    "y": "ground",
                    "kind": kind
                })
                x += random.randint(min_gap, max_gap)
            
            level["sections"].append({
                "type": "straight",
                "length": length,
                "platform_y": GROUND_Y,
                "obstacles": obstacles
            })
    
    return level

def save_level(level_data, filename):
    """Save level to JSON file"""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(level_data, f, indent=2)
    print(f"✓ Saved level to {filename}")

def load_level_json(filename):
    """Load level from JSON file"""
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)

def analyze_level_difficulty(level_data):
    """
    Analyze level and return difficulty metrics
    
    Returns:
        dict: Difficulty metrics
    """
    sections = level_data.get("sections", [])
    total_length = 0
    real_monsters = 0
    fake_monsters = 0
    branches = 0
    
    for sec in sections:
        if sec["type"] == "straight":
            total_length += sec["length"]
            for ob in sec.get("obstacles", []):
                if ob["kind"] == "real":
                    real_monsters += 1
                else:
                    fake_monsters += 1
        else:
            branches += 1
            max_len = max([p["length"] for p in sec["paths"]])
            total_length += max_len
            for path in sec["paths"]:
                for ob in path.get("obstacles", []):
                    if ob["kind"] == "real":
                        real_monsters += 1
                    else:
                        fake_monsters += 1
    
    total_monsters = real_monsters + fake_monsters
    monster_density = total_monsters / (total_length / 100) if total_length > 0 else 0
    real_ratio = real_monsters / total_monsters if total_monsters > 0 else 0
    
    # Calculate difficulty score (1-5)
    difficulty_score = 1
    if monster_density >= 2:
        difficulty_score = 2
    if monster_density >= 3:
        difficulty_score = 3
    if monster_density >= 4:
        difficulty_score = 4
    if monster_density >= 5 or real_ratio > 0.75:
        difficulty_score = 5
    
    return {
        "total_length": total_length,
        "sections": len(sections),
        "branches": branches,
        "real_monsters": real_monsters,
        "fake_monsters": fake_monsters,
        "total_monsters": total_monsters,
        "monster_density": round(monster_density, 2),
        "real_ratio": round(real_ratio, 2),
        "difficulty": difficulty_score
    }

def validate_level(level_data):
    """
    Validate level for playability issues
    
    Returns:
        tuple: (is_valid, list of warnings)
    """
    warnings = []
    
    sections = level_data.get("sections", [])
    if len(sections) == 0:
        return False, ["Level has no sections"]
    
    for i, sec in enumerate(sections):
        if sec["type"] == "straight":
            # Check for obstacles too close together
            obstacles = sorted(sec.get("obstacles", []), key=lambda x: x["x"])
            for j in range(len(obstacles) - 1):
                gap = obstacles[j+1]["x"] - obstacles[j]["x"]
                if gap < 60:
                    warnings.append(f"Section {i}: Obstacles too close ({gap}px)")
        
        elif sec["type"] == "branch":
            if len(sec.get("paths", [])) < 2:
                warnings.append(f"Section {i}: Branch must have at least 2 paths")
            
            for path_idx, path in enumerate(sec.get("paths", [])):
                obstacles = sorted(path.get("obstacles", []), key=lambda x: x["x"])
                for j in range(len(obstacles) - 1):
                    gap = obstacles[j+1]["x"] - obstacles[j]["x"]
                    if gap < 60:
                        warnings.append(f"Section {i} Path {path_idx}: Obstacles too close ({gap}px)")
    
    is_valid = len(warnings) == 0
    return is_valid, warnings

def print_level_info(filename):
    """Print detailed information about a level"""
    try:
        level = load_level_json(filename)
        metrics = analyze_level_difficulty(level)
        is_valid, warnings = validate_level(level)
        
        print(f"\n{'='*60}")
        print(f"Level: {filename}")
        print(f"{'='*60}")
        print(f"Total Length:     {metrics['total_length']}px")
        print(f"Sections:         {metrics['sections']}")
        print(f"Branch Points:    {metrics['branches']}")
        print(f"Real Monsters:    {metrics['real_monsters']}")
        print(f"Fake Monsters:    {metrics['fake_monsters']}")
        print(f"Total Monsters:   {metrics['total_monsters']}")
        print(f"Monster Density:  {metrics['monster_density']} per 100px")
        print(f"Real Monster %:   {metrics['real_ratio']*100:.1f}%")
        print(f"Difficulty:       {'★' * metrics['difficulty']}{'☆' * (5-metrics['difficulty'])}")
        print(f"\nValidation:       {'✓ VALID' if is_valid else '⚠ HAS WARNINGS'}")
        
        if warnings:
            print("\nWarnings:")
            for w in warnings:
                print(f"  - {w}")
        
        print(f"{'='*60}\n")
        
    except FileNotFoundError:
        print(f"Error: File '{filename}' not found")
    except Exception as e:
        print(f"Error analyzing level: {e}")

def batch_generate_levels(count=5, base_name="level_random", start_difficulty=1):
    """Generate multiple random levels with increasing difficulty"""
    print(f"\n🎲 Generating {count} random levels...")
    
    for i in range(count):
        difficulty = min(5, start_difficulty + i // 2)
        sections = 4 + i
        
        filename = f"{base_name}_{i+1}.json"
        level = generate_random_level(difficulty=difficulty, sections=sections, seed=None)
        save_level(level, filename)
        
        metrics = analyze_level_difficulty(level)
        print(f"   {filename}: Difficulty {metrics['difficulty']}/5, {metrics['total_length']}px, {metrics['total_monsters']} monsters")
    
    print(f"\n✓ Generated {count} levels successfully!\n")

def create_themed_level(theme="tutorial"):
    """Create a level based on predefined theme"""
    themes = {
        "tutorial": {
            "difficulty": 1,
            "sections": 4,
            "seed": 12345
        },
        "easy": {
            "difficulty": 2,
            "sections": 5,
            "seed": 23456
        },
        "medium": {
            "difficulty": 3,
            "sections": 6,
            "seed": 34567
        },
        "hard": {
            "difficulty": 4,
            "sections": 7,
            "seed": 45678
        },
        "extreme": {
            "difficulty": 5,
            "sections": 8,
            "seed": 56789
        }
    }
    
    config = themes.get(theme, themes["tutorial"])
    return generate_random_level(**config)

def merge_levels(*filenames):
    """Merge multiple levels into one long level"""
    merged = {"sections": []}
    
    for filename in filenames:
        try:
            level = load_level_json(filename)
            merged["sections"].extend(level.get("sections", []))
        except FileNotFoundError:
            print(f"Warning: {filename} not found, skipping")
    
    return merged

# CLI Interface
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("🛠️  Parkour Level Utilities")
        print("="*60)
        print("\nUsage:")
        print("  python utils.py generate <difficulty> <sections> <output.json>")
        print("  python utils.py analyze <level.json>")
        print("  python utils.py validate <level.json>")
        print("  python utils.py batch <count> [base_name]")
        print("  python utils.py theme <theme_name> <output.json>")
        print("\nExamples:")
        print("  python utils.py generate 3 6 my_level.json")
        print("  python utils.py analyze level1.json")
        print("  python utils.py batch 5 random_level")
        print("  python utils.py theme hard boss_level.json")
        print("\nThemes: tutorial, easy, medium, hard, extreme")
        sys.exit(0)
    
    command = sys.argv[1]
    
    if command == "generate":
        if len(sys.argv) < 5:
            print("Usage: python utils.py generate <difficulty> <sections> <output.json>")
            sys.exit(1)
        
        difficulty = int(sys.argv[2])
        sections = int(sys.argv[3])
        output = sys.argv[4]
        
        print(f"Generating level: difficulty={difficulty}, sections={sections}")
        level = generate_random_level(difficulty, sections)
        save_level(level, output)
        print_level_info(output)
    
    elif command == "analyze":
        if len(sys.argv) < 3:
            print("Usage: python utils.py analyze <level.json>")
            sys.exit(1)
        
        filename = sys.argv[2]
        print_level_info(filename)
    
    elif command == "validate":
        if len(sys.argv) < 3:
            print("Usage: python utils.py validate <level.json>")
            sys.exit(1)
        
        filename = sys.argv[2]
        level = load_level_json(filename)
        is_valid, warnings = validate_level(level)
        
        print(f"\nValidation for {filename}:")
        if is_valid:
            print("✓ Level is valid!")
        else:
            print("⚠ Level has warnings:")
            for w in warnings:
                print(f"  - {w}")
    
    elif command == "batch":
        count = int(sys.argv[2]) if len(sys.argv) > 2 else 5
        base_name = sys.argv[3] if len(sys.argv) > 3 else "level_random"
        batch_generate_levels(count, base_name)
    
    elif command == "theme":
        if len(sys.argv) < 4:
            print("Usage: python utils.py theme <theme_name> <output.json>")
            print("Themes: tutorial, easy, medium, hard, extreme")
            sys.exit(1)
        
        theme = sys.argv[2]
        output = sys.argv[3]
        
        print(f"Creating themed level: {theme}")
        level = create_themed_level(theme)
        save_level(level, output)
        print_level_info(output)
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)