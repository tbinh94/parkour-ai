"""
DEBUG PLAYER SPAWN POSITION
Test để đảm bảo player spawn đúng vị trí trên ground
"""
import pygame
import sys

# Import config
try:
    from src.config import *
except:
    from config import *

pygame.init()
screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
pygame.display.set_caption("Debug Player Spawn")
clock = pygame.time.Clock()

# Test values
print("\n" + "="*60)
print("🔍 PLAYER SPAWN POSITION DEBUG")
print("="*60)
print(f"Screen Resolution: {SCREEN_W}x{SCREEN_H}")
print(f"Ground Y: {GROUND_Y}")
print(f"Ground from bottom: {SCREEN_H - GROUND_Y}px")
print(f"Player Target X: {PLAYER_TARGET_X}")
print(f"Player Size: {PLAYER_W}x{PLAYER_H}")

# Create test player rect
player_rect = pygame.Rect(0, 0, PLAYER_W, PLAYER_H)
player_rect.x = PLAYER_TARGET_X
player_rect.bottom = GROUND_Y

print(f"\nPlayer Rect:")
print(f"  - X: {player_rect.x}")
print(f"  - Y (top): {player_rect.y}")
print(f"  - Bottom: {player_rect.bottom}")
print(f"  - Size: {player_rect.width}x{player_rect.height}")

# Create test platform
platform_x = 0
platform_y = GROUND_Y
platform_length = SCREEN_W

platform_rect = pygame.Rect(platform_x, platform_y, platform_length, 10)

print(f"\nPlatform Rect:")
print(f"  - X: {platform_rect.x}")
print(f"  - Y (top): {platform_rect.y}")
print(f"  - Width: {platform_rect.width}")
print(f"  - Height: {platform_rect.height}")

# Test collision
collision = player_rect.colliderect(platform_rect)
print(f"\n🎯 Collision Test:")
print(f"  - Player bottom: {player_rect.bottom}")
print(f"  - Platform top: {platform_rect.top}")
print(f"  - Difference: {abs(player_rect.bottom - platform_rect.top)}px")
print(f"  - Colliding: {collision}")

if player_rect.bottom == platform_rect.top:
    print("  ✅ Player is EXACTLY on ground!")
elif player_rect.bottom < platform_rect.top:
    print(f"  ❌ Player is {platform_rect.top - player_rect.bottom}px ABOVE ground!")
else:
    print(f"  ❌ Player is {player_rect.bottom - platform_rect.top}px BELOW ground!")

print("="*60)

# Visual test
running = True
frame_count = 0
test_vy = 0  # Simulated vertical velocity

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            elif event.key == pygame.K_SPACE:
                # Simulate jump
                test_vy = -10
            elif event.key == pygame.K_r:
                # Reset position
                player_rect.x = PLAYER_TARGET_X
                player_rect.bottom = GROUND_Y
                test_vy = 0
                print("🔄 Reset player position")
    
    # Simulate gravity
    if frame_count > 0:  # Skip first frame
        test_vy += 0.5
        player_rect.y += test_vy
        
        # Check collision
        if player_rect.colliderect(platform_rect):
            if test_vy >= 0 and player_rect.bottom >= platform_rect.top:
                player_rect.bottom = platform_rect.top
                test_vy = 0
    
    frame_count += 1
    
    # Draw
    screen.fill((30, 30, 40))
    
    # Draw ground line
    pygame.draw.line(screen, (100, 255, 100), 
                    (0, GROUND_Y), (SCREEN_W, GROUND_Y), 3)
    
    # Draw platform
    pygame.draw.rect(screen, (150, 150, 150), platform_rect)
    
    # Draw player
    player_color = (0, 255, 0) if player_rect.colliderect(platform_rect) else (255, 0, 0)
    pygame.draw.rect(screen, player_color, player_rect)
    
    # Draw center line at PLAYER_TARGET_X
    pygame.draw.line(screen, (255, 255, 0), 
                    (PLAYER_TARGET_X, 0), (PLAYER_TARGET_X, SCREEN_H), 1)
    
    # Draw info text
    font = pygame.font.SysFont(None, 24)
    
    info_texts = [
        f"Resolution: {SCREEN_W}x{SCREEN_H}",
        f"Ground Y: {GROUND_Y} ({SCREEN_H - GROUND_Y}px from bottom)",
        f"Player: {player_rect.x}, {player_rect.y} (bottom: {player_rect.bottom})",
        f"Velocity: {test_vy:.1f}",
        f"On Ground: {player_rect.colliderect(platform_rect)}",
        "",
        "SPACE = Jump | R = Reset | ESC = Quit"
    ]
    
    y_offset = 10
    for text in info_texts:
        text_surface = font.render(text, True, (255, 255, 255))
        screen.blit(text_surface, (10, y_offset))
        y_offset += 25
    
    # Draw measurement lines
    # Distance from player bottom to ground
    if player_rect.bottom != platform_rect.top:
        pygame.draw.line(screen, (255, 100, 100),
                        (player_rect.right + 5, player_rect.bottom),
                        (player_rect.right + 5, platform_rect.top), 2)
        
        distance = abs(player_rect.bottom - platform_rect.top)
        dist_text = font.render(f"{distance}px", True, (255, 100, 100))
        screen.blit(dist_text, (player_rect.right + 10, 
                               (player_rect.bottom + platform_rect.top) // 2))
    
    pygame.display.flip()
    clock.tick(60)

pygame.quit()

print("\n✓ Debug test complete!")
print("="*60)