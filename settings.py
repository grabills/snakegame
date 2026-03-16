import pygame

DISTINCT_COLORS = [
    (255, 65, 85),   # 1: Soft Red
    (65, 235, 115),  # 2: Vibrant Green
    (70, 160, 255),  # 3: Bright Blue
    (255, 230, 60),  # 4: Yellow
    (255, 140, 50),  # 5: Orange
    (235, 70, 235),  # 6: Magenta
    (60, 240, 240),  # 7: Cyan
    (170, 90, 255),  # 8: Purple
    (170, 255, 70),  # 9: Lime
    (255, 130, 190), # 10: Pink
    (60, 200, 200),  # 11: Teal
    (210, 70, 70),   # 12: Maroon
    (255, 190, 100), # 13: Peach
    (120, 190, 255), # 14: Light Blue
    (200, 200, 200)  # 15: Gray
]

# --- SYSTEM TILES ---
HOLE = -1
BRIDGE = -2

# --- UI Palette ---
SCREEN_BG = (18, 18, 22)        
BOARD_BG = (32, 32, 38)         
GRID_COLOR = (60, 60, 70)    
BORDER_COLOR = (80, 80, 95)  
CURSOR_COLOR = (255, 255, 255)

BTN_DEFAULT = pygame.Color(45, 45, 55)
BTN_HOVER = pygame.Color(85, 85, 105)
BTN_SOLVED = pygame.Color(60, 180, 100) 
BTN_SOLVED_HOVER = pygame.Color(80, 200, 120)
BTN_MOD_ACTIVE = pygame.Color(200, 70, 70)
BTN_MOD_ACTIVE_HOVER = pygame.Color(220, 90, 90)

def get_color(col_id):
    return DISTINCT_COLORS[(col_id - 1) % len(DISTINCT_COLORS)]
