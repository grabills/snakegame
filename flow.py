import pygame
import sys
import json
import os
import math
import random
from collections import deque

# --- Hardcoded, visually distinct colors ---
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

# --- Modern UI Palette ---
SCREEN_BG = (18, 18, 22)        
BOARD_BG = (32, 32, 38)         
GRID_COLOR = (60, 60, 70)    
BORDER_COLOR = (80, 80, 95)  
CURSOR_COLOR = (255, 255, 255)

BTN_DEFAULT = pygame.Color(45, 45, 55)
BTN_HOVER = pygame.Color(85, 85, 105)
BTN_SOLVED = pygame.Color(60, 180, 100) 
BTN_SOLVED_HOVER = pygame.Color(80, 200, 120)

btn_hover_states = {}

def get_color(col_id):
    return DISTINCT_COLORS[(col_id - 1) % len(DISTINCT_COLORS)]

# --- LOAD LEVEL DATABASE ---
LEVELS = []
if os.path.exists("puzzles.json"):
    with open("puzzles.json", "r") as f:
        LEVELS = json.load(f)
else:
    print("\n ERROR: puzzles.json not found! Run puzzle_factory.py first.\n")
    sys.exit()

def draw_button(screen, btn_id, text, font, x, y, w, h, default_col, hover_col, mouse_pos, dt):
    rect = pygame.Rect(x, y, w, h)
    is_hover = rect.collidepoint(mouse_pos)
    
    if btn_id not in btn_hover_states:
        btn_hover_states[btn_id] = 0.0
        
    target_state = 1.0 if is_hover else 0.0
    btn_hover_states[btn_id] += (target_state - btn_hover_states[btn_id]) * min(1.0, 15 * dt)
    current_color = default_col.lerp(hover_col, btn_hover_states[btn_id])
    
    shadow_rect = pygame.Rect(x, y + 4, w, h)
    pygame.draw.rect(screen, (10, 10, 12), shadow_rect, border_radius=12)
    pygame.draw.rect(screen, current_color, rect, border_radius=12)
    
    text_surf = font.render(text, True, (240, 240, 240))
    text_x = x + (w - text_surf.get_width()) // 2
    text_y = y + (h - text_surf.get_height()) // 2
    screen.blit(text_surf, (text_x, text_y))
    
    return is_hover

def draw_star(surface, x, y, size, color):
    """Mathematically draws a perfect 5-point vector star."""
    points = []
    for i in range(10):
        # Alternate between outer radius and inner radius to create the star points
        angle = i * math.pi / 5 - math.pi / 2
        radius = size if i % 2 == 0 else size * 0.4
        points.append((x + math.cos(angle) * radius, y + math.sin(angle) * radius))
    pygame.draw.polygon(surface, color, points)

def main():
    pygame.init()
    
    info = pygame.display.Info()
    SCREEN_WIDTH = info.current_w
    SCREEN_HEIGHT = info.current_h
    
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
    pygame.display.set_caption("Flow Free")
    
    try:
        font = pygame.font.SysFont("segoeui, arial", int(SCREEN_HEIGHT * 0.035))
        large_font = pygame.font.SysFont("segoeui, arial", int(SCREEN_HEIGHT * 0.06))
        title_font = pygame.font.SysFont("segoeui, arial", int(SCREEN_HEIGHT * 0.12), bold=True)
        hud_font = pygame.font.SysFont("segoeui, arial", int(SCREEN_HEIGHT * 0.03))
    except:
        font = pygame.font.Font(None, int(SCREEN_HEIGHT * 0.04))
        large_font = pygame.font.Font(None, int(SCREEN_HEIGHT * 0.06))
        title_font = pygame.font.Font(None, int(SCREEN_HEIGHT * 0.12))
        hud_font = pygame.font.Font(None, int(SCREEN_HEIGHT * 0.03))

    UI_HEIGHT = int(SCREEN_HEIGHT * 0.08) 
    
    game_state = "MENU" 
    current_level_idx = 0
    wrap_mode = False 
    solved_levels = set() 
    
    level_grid = []
    cell_size = 0
    off_x, off_y = 0, 0
    paths = {}
    cursor = [0, 0]
    board_size_px = 0
    grid_size = 0
    active_color = None
    level_solved = False
    
    visual_cursor = None
    completed_pulses = {} 
    history_stack = []    
    
    # --- NEW FEATURE VARIABLES ---
    moves = 0
    perfect_moves = 0
    particles = []
    hint_path = []
    hint_timer = 0.0
    
    def save_state():
        history_stack.append({k: v[:] for k, v in paths.items()})
        
    def undo_state():
        nonlocal paths
        if history_stack:
            paths = history_stack.pop()

    def load_level(idx):
        if idx >= len(LEVELS): return False 
        nonlocal grid_size, level_grid, cell_size, off_x, off_y, paths, cursor, board_size_px, active_color, level_solved, visual_cursor, completed_pulses, history_stack, moves, perfect_moves, particles, hint_path, hint_timer
        
        level_data = LEVELS[idx]
        raw_grid = level_data["grid"]

        grid_size = len(raw_grid)
        level_grid = [row[:] for row in raw_grid]
        margin_padding = int(SCREEN_HEIGHT * 0.20)
        max_board_size = min(SCREEN_WIDTH, SCREEN_HEIGHT - UI_HEIGHT) - margin_padding
        
        cell_size = max_board_size // grid_size
        board_size_px = cell_size * grid_size
        off_x = (SCREEN_WIDTH - board_size_px) // 2
        off_y = UI_HEIGHT + (SCREEN_HEIGHT - UI_HEIGHT - board_size_px) // 2
        
        paths = {col: [] for row in level_grid for col in row if col != 0}
        cursor = [0, 0]
        visual_cursor = None
        active_color = None
        level_solved = False
        completed_pulses = {}
        history_stack = []
        
        moves = 0
        perfect_moves = len(paths)
        particles = []
        hint_path = []
        hint_timer = 0.0
        return True

    def check_win():
        for col_id in paths:
            path = paths[col_id]
            if len(path) < 2: return False
            start, end = path[0], path[-1]
            if level_grid[start[0]][start[1]] != col_id or level_grid[end[0]][end[1]] != col_id:
                return False
        
        filled_cells = sum(len(path) for path in paths.values())
        return filled_cells == grid_size * grid_size

    clock = pygame.time.Clock()
    move_dr, move_dc = 0, 0
    move_timer = 0
    current_delay = 150
    halt_auto_move = False

    running = True
    while running:
        dt = clock.tick(60) / 1000.0 
        current_time = pygame.time.get_ticks()
        mouse_pos = pygame.mouse.get_pos()
        action_dr, action_dc = 0, 0
        is_auto_move = False
        click = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1: click = True

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: 
                    if game_state == "PLAYING": game_state = "LEVEL_SELECT"
                    elif game_state == "LEVEL_SELECT": game_state = "MENU"
                    else: running = False 
                    continue
                    
                if game_state == "PLAYING":
                    if level_solved:
                        if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                            solved_levels.add(current_level_idx)
                            current_level_idx += 1
                            if not load_level(current_level_idx): game_state = "LEVEL_SELECT" 
                        continue

                    if event.key == pygame.K_z:
                        undo_state()

                    # --- FEATURE 4: BFS DETERMINISTIC HINT SOLVER ---
                    if event.key == pygame.K_h:
                        if active_color is not None:
                            target_pos = None
                            start_pos = tuple(cursor)
                            # Find the other dot of the same color
                            for rr in range(grid_size):
                                for cc in range(grid_size):
                                    if level_grid[rr][cc] == active_color and (rr, cc) != paths[active_color][0]:
                                        target_pos = (rr, cc)
                                        break
                                if target_pos: break
                                
                            if target_pos:
                                q = deque([(start_pos, [start_pos])])
                                visited = set([start_pos])
                                
                                # Find all solid blockages
                                blocked = set()
                                for rr in range(grid_size):
                                    for cc in range(grid_size):
                                        if level_grid[rr][cc] != 0 and (rr, cc) != target_pos and (rr, cc) != paths[active_color][0]:
                                            blocked.add((rr, cc))
                                for col, p in paths.items():
                                    if col != active_color:
                                        for cell in p: blocked.add(cell)
                                    else:
                                        for cell in p: blocked.add(cell)
                                blocked.discard(start_pos) # Starting position is fine
                                
                                # Run Breadth-First Search
                                while q:
                                    curr, pth = q.popleft()
                                    if curr == target_pos:
                                        hint_path = pth
                                        hint_timer = 2.0 # Show hint for 2 seconds
                                        break
                                    
                                    r, c = curr
                                    for dr, dc in [(-1,0), (1,0), (0,-1), (0,1)]:
                                        nr, nc = r + dr, c + dc
                                        if wrap_mode:
                                            nr %= grid_size
                                            nc %= grid_size
                                        if 0 <= nr < grid_size and 0 <= nc < grid_size:
                                            if (nr, nc) not in visited and (nr, nc) not in blocked:
                                                visited.add((nr, nc))
                                                q.append(((nr, nc), pth + [(nr, nc)]))

                    dr, dc = 0, 0
                    if event.key in (pygame.K_w, pygame.K_UP): dr, dc = -1, 0
                    elif event.key in (pygame.K_s, pygame.K_DOWN): dr, dc = 1, 0
                    elif event.key in (pygame.K_a, pygame.K_LEFT): dr, dc = 0, -1
                    elif event.key in (pygame.K_d, pygame.K_RIGHT): dr, dc = 0, 1
                    elif event.key == pygame.K_t: wrap_mode = not wrap_mode
                    elif event.key == pygame.K_r: load_level(current_level_idx)

                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        r, c = cursor
                        if active_color is not None:
                            path = paths[active_color]
                            if len(path) > 1 and level_grid[r][c] == active_color and path[-1] == (r, c):
                                completed_pulses[active_color] = current_time 
                                
                                # --- FEATURE 5: PARTICLE BURST ---
                                for _ in range(15):
                                    angle = random.uniform(0, 2 * math.pi)
                                    speed = random.uniform(50, 150)
                                    px = off_x + c * cell_size + cell_size // 2
                                    py = off_y + r * cell_size + cell_size // 2
                                    particles.append({
                                        'pos': [px, py],
                                        'vel': [math.cos(angle) * speed, math.sin(angle) * speed],
                                        'color': get_color(active_color),
                                        'life': 1.0,
                                        'max_life': 1.0
                                    })
                                
                                active_color = None 
                            else:
                                save_state()
                                paths[active_color] = []
                                active_color = None
                        else:
                            if level_grid[r][c] != 0:
                                save_state()
                                active_color = level_grid[r][c]
                                paths[active_color] = [(r, c)]
                                moves += 1 # Feature 2: Count the Move
                            else:
                                for col_id, path in paths.items():
                                    if (r, c) in path:
                                        save_state()
                                        active_color = col_id
                                        idx = path.index((r, c))
                                        paths[col_id] = path[:idx+1]
                                        moves += 1 # Feature 2: Count the Move
                                        break

                    if dr != 0 or dc != 0:
                        action_dr, action_dc = dr, dc
                        move_dr, move_dc = dr, dc
                        current_delay = 160 
                        move_timer = current_time
                        halt_auto_move = False

            elif event.type == pygame.KEYUP:
                if game_state == "PLAYING":
                    if event.key in (pygame.K_w, pygame.K_UP) and move_dr == -1: move_dr, move_dc = 0, 0
                    elif event.key in (pygame.K_s, pygame.K_DOWN) and move_dr == 1: move_dr, move_dc = 0, 0
                    elif event.key in (pygame.K_a, pygame.K_LEFT) and move_dc == -1: move_dr, move_dc = 0, 0
                    elif event.key in (pygame.K_d, pygame.K_RIGHT) and move_dc == 1: move_dr, move_dc = 0, 0

        # --- PLAYING LOGIC ---
        if game_state == "PLAYING":
            # Animate Particles
            for p in reversed(particles):
                p['life'] -= dt
                p['pos'][0] += p['vel'][0] * dt
                p['pos'][1] += p['vel'][1] * dt
                if p['life'] <= 0:
                    particles.remove(p)
                    
            # Animate Hint Timer
            if hint_timer > 0:
                hint_timer -= dt
                if hint_timer <= 0:
                    hint_path = []
                    
            if action_dr == 0 and action_dc == 0:
                if (move_dr != 0 or move_dc != 0) and not halt_auto_move:
                    if current_time - move_timer >= current_delay:
                        action_dr, action_dc = move_dr, move_dc
                        is_auto_move = True
                        move_timer = current_time
                        current_delay = max(35, current_delay - 30) 

            if action_dr != 0 or action_dc != 0:
                r, c = cursor
                nr, nc = r + action_dr, c + action_dc
                
                if wrap_mode:
                    nr %= grid_size
                    nc %= grid_size

                if 0 <= nr < grid_size and 0 <= nc < grid_size:
                    dist = abs(r - nr) + abs(c - nc)
                    if wrap_mode:
                        dist = min(abs(r - nr), grid_size - abs(r - nr)) + min(abs(c - nc), grid_size - abs(c - nc))
                        
                    if dist == 1:
                        move_allowed = True
                        if active_color is not None:
                            target_dot = level_grid[nr][nc]
                            path = paths[active_color]
                            if (nr, nc) in path:
                                pass 
                            else:
                                head = path[-1]
                                if level_grid[head[0]][head[1]] == active_color and len(path) > 1:
                                    move_allowed = False
                                elif target_dot != 0 and target_dot != active_color:
                                    move_allowed = False
                        
                        if move_allowed:
                            save_state()
                            cursor = [nr, nc]
                            if active_color is not None:
                                path = paths[active_color]
                                if (nr, nc) in path:
                                    idx = path.index((nr, nc))
                                    paths[active_color] = path[:idx+1]
                                else:
                                    for col_id, p in paths.items():
                                        if col_id != active_color and (nr, nc) in p:
                                            paths[col_id] = [] 
                                    path.append((nr, nc))
                            
                            if is_auto_move and level_grid[nr][nc] != 0:
                                halt_auto_move = True
                        else:
                            if is_auto_move: halt_auto_move = True
            
            target_pos = pygame.math.Vector2(off_x + cursor[1] * cell_size + cell_size // 2, 
                                             off_y + cursor[0] * cell_size + cell_size // 2)
            if visual_cursor is None:
                visual_cursor = pygame.math.Vector2(target_pos)
            else:
                if visual_cursor.distance_to(target_pos) > cell_size * 1.5:
                    visual_cursor = pygame.math.Vector2(target_pos)
                else:
                    lerp_speed = min(1.0, 30.0 * dt)
                    visual_cursor = visual_cursor.lerp(target_pos, lerp_speed)

            if not level_solved and check_win():
                level_solved = True
                solved_levels.add(current_level_idx)
                active_color = None

        # --- DRAWING ---
        screen.fill(SCREEN_BG)

        if game_state == "MENU":
            title_text = title_font.render("FLOW FREE", True, DISTINCT_COLORS[2]) 
            screen.blit(title_text, (SCREEN_WIDTH//2 - title_text.get_width()//2, SCREEN_HEIGHT * 0.2))

            btn_w, btn_h = int(SCREEN_WIDTH * 0.25), int(SCREEN_HEIGHT * 0.08)
            btn_x = SCREEN_WIDTH//2 - btn_w//2
            
            if draw_button(screen, "play_btn", "Play / Resume", font, btn_x, SCREEN_HEIGHT * 0.45, btn_w, btn_h, BTN_DEFAULT, BTN_HOVER, mouse_pos, dt):
                if click:
                    load_level(current_level_idx)
                    game_state = "PLAYING"
                    
            if draw_button(screen, "select_btn", "Level Select", font, btn_x, SCREEN_HEIGHT * 0.58, btn_w, btn_h, BTN_DEFAULT, BTN_HOVER, mouse_pos, dt):
                if click: game_state = "LEVEL_SELECT"
                    
            if draw_button(screen, "quit_btn", "Quit Game", font, btn_x, SCREEN_HEIGHT * 0.71, btn_w, btn_h, BTN_DEFAULT, BTN_HOVER, mouse_pos, dt):
                if click: running = False

        elif game_state == "LEVEL_SELECT":
            title_text = font.render("Select a Puzzle", True, (255, 255, 255))
            screen.blit(title_text, (SCREEN_WIDTH//2 - title_text.get_width()//2, SCREEN_HEIGHT * 0.05))
            
            back_text = hud_font.render("[ESC] Back", True, (150, 150, 150))
            screen.blit(back_text, (30, 30))

            cols = 8
            padding = 15
            usable_w = SCREEN_WIDTH * 0.8
            usable_h = SCREEN_HEIGHT * 0.7
            
            btn_size = int(min((usable_w - (cols-1)*padding) // cols, (usable_h - (4)*padding) // 5))
            btn_size = min(btn_size, 100) 
            
            total_w = cols * btn_size + (cols - 1) * padding
            start_x = (SCREEN_WIDTH - total_w) // 2
            start_y = int(SCREEN_HEIGHT * 0.18)

            for i in range(len(LEVELS)):
                row = i // cols
                col = i % cols
                x = start_x + col * (btn_size + padding)
                y = start_y + row * (btn_size + padding)
                
                is_solved = i in solved_levels
                d_col = BTN_SOLVED if is_solved else BTN_DEFAULT
                h_col = BTN_SOLVED_HOVER if is_solved else BTN_HOVER
                
                if draw_button(screen, f"lvl_{i}", str(i + 1), font, x, y, btn_size, btn_size, d_col, h_col, mouse_pos, dt):
                    if click:
                        current_level_idx = i
                        load_level(current_level_idx)
                        game_state = "PLAYING"

        elif game_state == "PLAYING":
            pygame.draw.rect(screen, (22, 22, 26), (0, 0, SCREEN_WIDTH, UI_HEIGHT))
            
            pygame.draw.rect(screen, BOARD_BG, (off_x, off_y, board_size_px, board_size_px), border_radius=8)
            pygame.draw.rect(screen, BORDER_COLOR, (off_x - 2, off_y - 2, board_size_px + 4, board_size_px + 4), 3, border_radius=8)

            if wrap_mode:
                for r in range(grid_size):
                    for c in range(grid_size):
                        if level_grid[r][c] != 0:
                            raw_color = get_color(level_grid[r][c])
                            ghost = (max(20, raw_color[0]-150), max(20, raw_color[1]-150), max(20, raw_color[2]-150))
                            if r == 0: pygame.draw.circle(screen, ghost, (off_x + c * cell_size + cell_size // 2, off_y + grid_size * cell_size + cell_size // 2), cell_size // 3)
                            if r == grid_size - 1: pygame.draw.circle(screen, ghost, (off_x + c * cell_size + cell_size // 2, off_y - cell_size // 2), cell_size // 3)
                            if c == 0: pygame.draw.circle(screen, ghost, (off_x + grid_size * cell_size + cell_size // 2, off_y + r * cell_size + cell_size // 2), cell_size // 3)
                            if c == grid_size - 1: pygame.draw.circle(screen, ghost, (off_x - cell_size // 2, off_y + r * cell_size + cell_size // 2), cell_size // 3)

            for x in range(cell_size, board_size_px, cell_size):
                pygame.draw.line(screen, GRID_COLOR, (off_x + x, off_y), (off_x + x, off_y + board_size_px), 2)
            for y in range(cell_size, board_size_px, cell_size):
                pygame.draw.line(screen, GRID_COLOR, (off_x, off_y + y), (off_x + board_size_px, off_y + y), 2)

            # --- DRAW BFS HINT LINE ---
            if hint_timer > 0 and len(hint_path) > 1:
                hint_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                c_thick = max(2, int(cell_size * 0.15))
                h_color = get_color(active_color) if active_color else (255,255,255)
                alpha_color = (*h_color, 120) # Semi-transparent
                
                for i in range(len(hint_path) - 1):
                    r1, c1 = hint_path[i]
                    r2, c2 = hint_path[i+1]
                    p1 = (off_x + c1 * cell_size + cell_size // 2, off_y + r1 * cell_size + cell_size // 2)
                    p2 = (off_x + c2 * cell_size + cell_size // 2, off_y + r2 * cell_size + cell_size // 2)
                    
                    if abs(r1 - r2) > 1 or abs(c1 - c2) > 1:
                        if wrap_mode:
                            if abs(r1 - r2) > 1: 
                                if r1 < r2:
                                    pygame.draw.line(hint_surf, alpha_color, p1, (p1[0], p1[1] - cell_size), c_thick)
                                    pygame.draw.line(hint_surf, alpha_color, p2, (p2[0], p2[1] + cell_size), c_thick)
                                else:
                                    pygame.draw.line(hint_surf, alpha_color, p1, (p1[0], p1[1] + cell_size), c_thick)
                                    pygame.draw.line(hint_surf, alpha_color, p2, (p2[0], p2[1] - cell_size), c_thick)
                            elif abs(c1 - c2) > 1: 
                                if c1 < c2:
                                    pygame.draw.line(hint_surf, alpha_color, p1, (p1[0] - cell_size, p1[1]), c_thick)
                                    pygame.draw.line(hint_surf, alpha_color, p2, (p2[0] + cell_size, p2[1]), c_thick)
                                else:
                                    pygame.draw.line(hint_surf, alpha_color, p1, (p1[0] + cell_size, p1[1]), c_thick)
                                    pygame.draw.line(hint_surf, alpha_color, p2, (p2[0] - cell_size, p2[1]), c_thick)
                    else:
                        pygame.draw.line(hint_surf, alpha_color, p1, p2, c_thick)
                        
                screen.blit(hint_surf, (0, 0))

            pipe_thickness = int(cell_size * 0.4)
            joint_radius = int(cell_size * 0.2)
            
            for col_id, path in paths.items():
                if not path: continue
                color = get_color(col_id)
                
                swell_radius = 0
                if col_id in completed_pulses:
                    elapsed = current_time - completed_pulses[col_id]
                    duration = 400.0
                    if elapsed < duration:
                        progress = elapsed / duration
                        ease_out = 1.0 - (1.0 - progress) * (1.0 - progress)
                        swell_radius = int(math.sin(progress * math.pi) * (cell_size * 0.15))
                        ring_rad = int(cell_size * 0.4 + (ease_out * cell_size * 0.6))
                        ring_thick = max(1, int(cell_size * 0.1 * (1.0 - progress)))
                        end_node = path[-1]
                        ring_p = (off_x + end_node[1] * cell_size + cell_size // 2, off_y + end_node[0] * cell_size + cell_size // 2)
                        pygame.draw.circle(screen, color, ring_p, ring_rad, ring_thick)
                    else:
                        del completed_pulses[col_id]

                c_thick = pipe_thickness + swell_radius
                c_rad = joint_radius + swell_radius // 2
                
                for i in range(len(path) - 1):
                    r1, c1 = path[i]
                    r2, c2 = path[i+1]
                    p1 = (off_x + c1 * cell_size + cell_size // 2, off_y + r1 * cell_size + cell_size // 2)
                    p2 = (off_x + c2 * cell_size + cell_size // 2, off_y + r2 * cell_size + cell_size // 2)
                    
                    if abs(r1 - r2) > 1 or abs(c1 - c2) > 1:
                        if wrap_mode:
                            if abs(r1 - r2) > 1: 
                                if r1 < r2:
                                    pygame.draw.line(screen, color, p1, (p1[0], p1[1] - cell_size), c_thick)
                                    pygame.draw.line(screen, color, p2, (p2[0], p2[1] + cell_size), c_thick)
                                else:
                                    pygame.draw.line(screen, color, p1, (p1[0], p1[1] + cell_size), c_thick)
                                    pygame.draw.line(screen, color, p2, (p2[0], p2[1] - cell_size), c_thick)
                            elif abs(c1 - c2) > 1: 
                                if c1 < c2:
                                    pygame.draw.line(screen, color, p1, (p1[0] - cell_size, p1[1]), c_thick)
                                    pygame.draw.line(screen, color, p2, (p2[0] + cell_size, p2[1]), c_thick)
                                else:
                                    pygame.draw.line(screen, color, p1, (p1[0] + cell_size, p1[1]), c_thick)
                                    pygame.draw.line(screen, color, p2, (p2[0] - cell_size, p2[1]), c_thick)
                        continue 
                    else:
                        pygame.draw.line(screen, color, p1, p2, c_thick)
                    
                for r, c in path:
                    p = (off_x + c * cell_size + cell_size // 2, off_y + r * cell_size + cell_size // 2)
                    pygame.draw.circle(screen, color, p, c_rad)

            for r in range(grid_size):
                for c in range(grid_size):
                    if level_grid[r][c] != 0:
                        color = get_color(level_grid[r][c])
                        center = (off_x + c * cell_size + cell_size // 2, off_y + r * cell_size + cell_size // 2)
                        pygame.draw.circle(screen, color, center, int(cell_size * 0.35))

            # --- DRAW PARTICLES ---
            for p in particles:
                size = max(1, int(12 * (p['life'] / p['max_life'])))
                rect = pygame.Rect(0, 0, size, size)
                rect.center = p['pos']
                pygame.draw.rect(screen, p['color'], rect)

            draw_color = get_color(active_color) if active_color else CURSOR_COLOR
            thickness = max(4, cell_size // 8) if active_color else 3
            
            cursor_rect = pygame.Rect(0, 0, cell_size, cell_size)
            if visual_cursor:
                cursor_rect.center = visual_cursor
            pygame.draw.rect(screen, draw_color, cursor_rect, thickness, border_radius=8)

            diff = LEVELS[current_level_idx].get("difficulty", "Unknown")
            hud_left = hud_font.render(f"Level {current_level_idx + 1} / {len(LEVELS)} | {diff} | Moves: {moves}/{perfect_moves}", True, (220, 220, 220))
            hud_right = hud_font.render(f"[ESC] Menu    [R] Restart    [Z] Undo    [H] Hint    [T] Torus", True, (150, 150, 150))
            
            screen.blit(hud_left, (30, (UI_HEIGHT - hud_left.get_height()) // 2))
            screen.blit(hud_right, (SCREEN_WIDTH - hud_right.get_width() - 30, (UI_HEIGHT - hud_right.get_height()) // 2))

            if level_solved:
                overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 200))
                screen.blit(overlay, (0, 0))
                
                win_text = title_font.render("SOLVED!", True, DISTINCT_COLORS[1])
                
                # --- STAR RATING ---
                stars = 3
                if moves > perfect_moves + 2: stars = 2
                if moves > perfect_moves + 6: stars = 1
                
                rating_text = large_font.render("Rating: ", True, (255, 215, 0))
                sub_text = font.render("Press ENTER to continue", True, (200, 200, 200))
                
                # Calculate layout to center everything perfectly
                star_size = int(SCREEN_HEIGHT * 0.025)
                star_spacing = star_size * 2.5
                total_w = rating_text.get_width() + (3 * star_spacing)
                
                start_x = SCREEN_WIDTH // 2 - total_w // 2
                base_y = SCREEN_HEIGHT // 2
                
                # Draw Text
                screen.blit(win_text, (SCREEN_WIDTH//2 - win_text.get_width()//2, base_y - win_text.get_height()))
                screen.blit(rating_text, (start_x, base_y))
                
                # Draw Vector Stars
                star_start_x = start_x + rating_text.get_width() + star_size
                star_y = base_y + rating_text.get_height() // 2
                
                for i in range(3):
                    color = (255, 215, 0) if i < stars else BORDER_COLOR # Gold or dark gray
                    draw_star(screen, star_start_x + (i * star_spacing), star_y, star_size, color)

                screen.blit(sub_text, (SCREEN_WIDTH//2 - sub_text.get_width()//2, base_y + rating_text.get_height() + 20))


        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
