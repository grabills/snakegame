import pygame
import sys
import random

# --- Hardcoded, visually distinct colors ---
DISTINCT_COLORS = [
    (255, 50, 50),   # Red
    (50, 255, 50),   # Green
    (80, 150, 255),  # Blue (Lightened slightly for dark BGs)
    (255, 255, 50),  # Yellow
    (255, 150, 50),  # Orange
    (255, 50, 255),  # Magenta
    (50, 255, 255),  # Cyan
    (180, 80, 255),  # Purple
    (150, 255, 50),  # Lime
    (255, 150, 200), # Pink
    (50, 200, 200),  # Teal
    (200, 50, 50),   # Maroon
    (255, 200, 100), # Peach
    (100, 200, 255), # Light Blue
    (200, 200, 200)  # Gray
]

# --- High Visibility Palette ---
SCREEN_BG = (10, 10, 12)        # Outer background (very dark)
BOARD_BG = (40, 40, 45)         # Playable grid (distinctly lighter)
GRID_COLOR = (130, 130, 140)    # Grid lines (much brighter gray)
BORDER_COLOR = (200, 200, 200)  # Bright border to separate real vs ghost
CURSOR_COLOR = (255, 255, 255)

def get_color(col_id):
    idx = col_id - 1
    if idx < len(DISTINCT_COLORS):
        return DISTINCT_COLORS[idx]
    random.seed(col_id * 12345)
    return (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))

def get_empty_neighbors(r, c, grid, wrap, grid_size):
    neighbors = []
    for dr, dc in [(-1,0), (1,0), (0,-1), (0,1)]:
        nr, nc = r + dr, c + dc
        if wrap:
            nr %= grid_size
            nc %= grid_size
        if 0 <= nr < grid_size and 0 <= nc < grid_size and grid[nr][nc] == 0:
            neighbors.append((nr, nc))
    return neighbors

def generate_hamiltonian_path(grid_size, wrap):
    for attempt in range(150):
        grid = [[0]*grid_size for _ in range(grid_size)]
        start_r, start_c = random.randint(0, grid_size - 1), random.randint(0, grid_size - 1)
        path = [(start_r, start_c)]
        grid[start_r][start_c] = 1
        
        while len(path) < grid_size * grid_size:
            r, c = path[-1]
            neighbors = get_empty_neighbors(r, c, grid, wrap, grid_size)
            if not neighbors: break
            
            neighbors.sort(key=lambda n: len(get_empty_neighbors(n[0], n[1], grid, wrap, grid_size)))
            min_onward = len(get_empty_neighbors(neighbors[0][0], neighbors[0][1], grid, wrap, grid_size))
            best = [n for n in neighbors if len(get_empty_neighbors(n[0], n[1], grid, wrap, grid_size)) == min_onward]
            
            next_cell = random.choice(best)
            path.append(next_cell)
            grid[next_cell[0]][next_cell[1]] = 1
            
        if len(path) == grid_size * grid_size:
            return path
            
    path = []
    for r in range(grid_size):
        if r % 2 == 0:
            for c in range(grid_size): path.append((r, c))
        else:
            for c in range(grid_size - 1, -1, -1): path.append((r, c))
    return path

def generate_level(grid_size, wrap=False):
    for generation_attempt in range(100):
        full_path = generate_hamiltonian_path(grid_size, wrap)
        total_cells = grid_size * grid_size
        
        num_colors = max(4, int(grid_size * 0.75)) 
        valid_cut_indices = list(range(3, total_cells - 3))
        cut_points = []
        
        for _ in range(num_colors - 1):
            if not valid_cut_indices: break
            cut = random.choice(valid_cut_indices)
            cut_points.append(cut)
            valid_cut_indices = [x for x in valid_cut_indices if abs(x - cut) > 3]
            
        cut_points.sort()
        cut_points = [0] + cut_points + [total_cells]
        
        paths = []
        for i in range(len(cut_points) - 1):
            start, end = cut_points[i], cut_points[i+1]
            paths.append(full_path[start:end])
            
        is_valid_puzzle = True
        for p in paths:
            if not p: continue
            r1, c1 = p[0]
            r2, c2 = p[-1]
            
            dr = abs(r1 - r2)
            dc = abs(c1 - c2)
            if wrap:
                dr = min(dr, grid_size - dr)
                dc = min(dc, grid_size - dc)
                
            if (dr + dc) <= 1:
                is_valid_puzzle = False
                break
                
        if is_valid_puzzle:
            level_grid = [[0]*grid_size for _ in range(grid_size)]
            for i, p in enumerate(paths):
                if not p: continue
                col = i + 1
                level_grid[p[0][0]][p[0][1]] = col
                level_grid[p[-1][0]][p[-1][1]] = col
            return level_grid
            
    return level_grid

def main():
    pygame.init()
    
    info = pygame.display.Info()
    SCREEN_WIDTH = info.current_w
    SCREEN_HEIGHT = info.current_h
    
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.FULLSCREEN)
    pygame.display.set_caption("Flow Free: High Visibility")
    font = pygame.font.SysFont(None, int(SCREEN_HEIGHT * 0.04))
    large_font = pygame.font.SysFont(None, int(SCREEN_HEIGHT * 0.1))

    UI_HEIGHT = int(SCREEN_HEIGHT * 0.08) 
    grid_size = 7
    wrap_mode = False 
    
    def load_new_level():
        level_grid = generate_level(grid_size, wrap_mode)
        
        # --- LAYOUT FIX ---
        # Force a massive margin (at least 20% of the screen height) so ghost dots NEVER hit the UI
        margin_padding = int(SCREEN_HEIGHT * 0.25)
        max_board_size = min(SCREEN_WIDTH, SCREEN_HEIGHT - UI_HEIGHT) - margin_padding
        
        cell_size = max_board_size // grid_size
        board_pixel_size = cell_size * grid_size
        
        # Center the board perfectly in the remaining space below the UI
        offset_x = (SCREEN_WIDTH - board_pixel_size) // 2
        offset_y = UI_HEIGHT + (SCREEN_HEIGHT - UI_HEIGHT - board_pixel_size) // 2
        
        paths = {col: [] for row in level_grid for col in row if col != 0}
        return level_grid, cell_size, offset_x, offset_y, paths, [0, 0], False, board_pixel_size

    level_grid, cell_size, off_x, off_y, paths, cursor, level_solved, board_size_px = load_new_level()
    active_color = None

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
    current_delay = 200
    halt_auto_move = False

    running = True
    while running:
        current_time = pygame.time.get_ticks()
        action_dr, action_dc = 0, 0
        is_auto_move = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE: 
                    running = False
                    continue
                    
                if level_solved:
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        level_grid, cell_size, off_x, off_y, paths, cursor, level_solved, board_size_px = load_new_level()
                        active_color = None
                    continue

                dr, dc = 0, 0
                if event.key in (pygame.K_w, pygame.K_UP): dr, dc = -1, 0
                elif event.key in (pygame.K_s, pygame.K_DOWN): dr, dc = 1, 0
                elif event.key in (pygame.K_a, pygame.K_LEFT): dr, dc = 0, -1
                elif event.key in (pygame.K_d, pygame.K_RIGHT): dr, dc = 0, 1

                elif event.key == pygame.K_t: 
                    wrap_mode = not wrap_mode
                    level_grid, cell_size, off_x, off_y, paths, cursor, level_solved, board_size_px = load_new_level()
                    active_color = None
                elif event.key == pygame.K_g: 
                    level_grid, cell_size, off_x, off_y, paths, cursor, level_solved, board_size_px = load_new_level()
                    active_color = None
                elif event.key in (pygame.K_PLUS, pygame.K_EQUALS):
                    grid_size = min(15, grid_size + 1)
                    level_grid, cell_size, off_x, off_y, paths, cursor, level_solved, board_size_px = load_new_level()
                    active_color = None
                elif event.key == pygame.K_MINUS:
                    grid_size = max(4, grid_size - 1)
                    level_grid, cell_size, off_x, off_y, paths, cursor, level_solved, board_size_px = load_new_level()
                    active_color = None

                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    r, c = cursor
                    if active_color is not None:
                        path = paths[active_color]
                        if len(path) > 1 and level_grid[r][c] == active_color and path[-1] == (r, c):
                            active_color = None 
                        else:
                            paths[active_color] = []
                            active_color = None
                    else:
                        if level_grid[r][c] != 0:
                            active_color = level_grid[r][c]
                            paths[active_color] = [(r, c)]
                        else:
                            for col_id, path in paths.items():
                                if (r, c) in path:
                                    active_color = col_id
                                    idx = path.index((r, c))
                                    paths[col_id] = path[:idx+1]
                                    break

                if dr != 0 or dc != 0:
                    action_dr, action_dc = dr, dc
                    move_dr, move_dc = dr, dc
                    current_delay = 200 
                    move_timer = current_time
                    halt_auto_move = False

            elif event.type == pygame.KEYUP:
                if event.key in (pygame.K_w, pygame.K_UP) and move_dr == -1: move_dr, move_dc = 0, 0
                elif event.key in (pygame.K_s, pygame.K_DOWN) and move_dr == 1: move_dr, move_dc = 0, 0
                elif event.key in (pygame.K_a, pygame.K_LEFT) and move_dc == -1: move_dr, move_dc = 0, 0
                elif event.key in (pygame.K_d, pygame.K_RIGHT) and move_dc == 1: move_dr, move_dc = 0, 0

        if action_dr == 0 and action_dc == 0:
            if (move_dr != 0 or move_dc != 0) and not halt_auto_move:
                if current_time - move_timer >= current_delay:
                    action_dr, action_dc = move_dr, move_dc
                    is_auto_move = True
                    move_timer = current_time
                    current_delay = max(40, current_delay - 40)

        if action_dr != 0 or action_dc != 0:
            nr, nc = cursor[0] + action_dr, cursor[1] + action_dc
            
            if wrap_mode:
                nr %= grid_size
                nc %= grid_size

            if 0 <= nr < grid_size and 0 <= nc < grid_size:
                cursor = [nr, nc]
                
                if active_color is not None:
                    path = paths[active_color]
                    
                    if (nr, nc) in path:
                        idx = path.index((nr, nc))
                        paths[active_color] = path[:idx+1]
                    else:
                        head = path[-1]
                        if level_grid[head[0]][head[1]] == active_color and len(path) > 1:
                            pass 
                        else:
                            target_dot = level_grid[nr][nc]
                            if target_dot != 0 and target_dot != active_color:
                                pass 
                            else:
                                for col_id, p in paths.items():
                                    if col_id != active_color and (nr, nc) in p:
                                        paths[col_id] = [] 
                                
                                path.append((nr, nc))
                
                if is_auto_move and level_grid[nr][nc] != 0:
                    halt_auto_move = True
        
        if not level_solved and check_win():
            level_solved = True
            active_color = None

        # --- Graphics ---
        screen.fill(SCREEN_BG)

        # Draw UI Header Bar
        pygame.draw.rect(screen, (15, 15, 18), (0, 0, SCREEN_WIDTH, UI_HEIGHT))
        pygame.draw.line(screen, (100, 100, 100), (0, UI_HEIGHT), (SCREEN_WIDTH, UI_HEIGHT), 2)
        
        # Draw Playable Board Area
        pygame.draw.rect(screen, BOARD_BG, (off_x, off_y, board_size_px, board_size_px))
        
        # --- NEW: Bright Border to clearly define the Playable Area ---
        pygame.draw.rect(screen, BORDER_COLOR, (off_x - 2, off_y - 2, board_size_px + 4, board_size_px + 4), 3)

        # --- Draw Ghost Dots for 3D Wrap Visualization ---
        if wrap_mode:
            for r in range(grid_size):
                for c in range(grid_size):
                    if level_grid[r][c] != 0:
                        raw_color = get_color(level_grid[r][c])
                        ghost_color = (max(20, raw_color[0]-150), max(20, raw_color[1]-150), max(20, raw_color[2]-150))
                        
                        if r == 0: # Ghost at bottom
                            pygame.draw.circle(screen, ghost_color, (off_x + c * cell_size + cell_size // 2, off_y + grid_size * cell_size + cell_size // 2), cell_size // 3)
                        if r == grid_size - 1: # Ghost at top
                            pygame.draw.circle(screen, ghost_color, (off_x + c * cell_size + cell_size // 2, off_y - cell_size // 2), cell_size // 3)
                        if c == 0: # Ghost on right
                            pygame.draw.circle(screen, ghost_color, (off_x + grid_size * cell_size + cell_size // 2, off_y + r * cell_size + cell_size // 2), cell_size // 3)
                        if c == grid_size - 1: # Ghost on left
                            pygame.draw.circle(screen, ghost_color, (off_x - cell_size // 2, off_y + r * cell_size + cell_size // 2), cell_size // 3)

        # Draw Grid (Now much brighter)
        for x in range(0, board_size_px + 1, cell_size):
            pygame.draw.line(screen, GRID_COLOR, (off_x + x, off_y), (off_x + x, off_y + board_size_px), 2)
        for y in range(0, board_size_px + 1, cell_size):
            pygame.draw.line(screen, GRID_COLOR, (off_x, off_y + y), (off_x + board_size_px, off_y + y), 2)

        # Draw Pipes
        for col_id, path in paths.items():
            if not path: continue
            color = get_color(col_id)
            
            for i in range(len(path) - 1):
                r1, c1 = path[i]
                r2, c2 = path[i+1]
                
                p1 = (off_x + c1 * cell_size + cell_size // 2, off_y + r1 * cell_size + cell_size // 2)
                p2 = (off_x + c2 * cell_size + cell_size // 2, off_y + r2 * cell_size + cell_size // 2)
                
                if abs(r1 - r2) > 1 or abs(c1 - c2) > 1:
                    if wrap_mode:
                        if abs(r1 - r2) > 1: 
                            if r1 < r2:
                                pygame.draw.line(screen, color, p1, (p1[0], p1[1] - cell_size), cell_size // 3)
                                pygame.draw.line(screen, color, p2, (p2[0], p2[1] + cell_size), cell_size // 3)
                            else:
                                pygame.draw.line(screen, color, p1, (p1[0], p1[1] + cell_size), cell_size // 3)
                                pygame.draw.line(screen, color, p2, (p2[0], p2[1] - cell_size), cell_size // 3)
                        elif abs(c1 - c2) > 1: 
                            if c1 < c2:
                                pygame.draw.line(screen, color, p1, (p1[0] - cell_size, p1[1]), cell_size // 3)
                                pygame.draw.line(screen, color, p2, (p2[0] + cell_size, p2[1]), cell_size // 3)
                            else:
                                pygame.draw.line(screen, color, p1, (p1[0] + cell_size, p1[1]), cell_size // 3)
                                pygame.draw.line(screen, color, p2, (p2[0] - cell_size, p2[1]), cell_size // 3)
                    continue 
                else:
                    pygame.draw.line(screen, color, p1, p2, cell_size // 3)
                
            for r, c in path:
                p = (off_x + c * cell_size + cell_size // 2, off_y + r * cell_size + cell_size // 2)
                pygame.draw.circle(screen, color, p, cell_size // 6)

        # Draw Real Playable Dots
        for r in range(grid_size):
            for c in range(grid_size):
                if level_grid[r][c] != 0:
                    color = get_color(level_grid[r][c])
                    center = (off_x + c * cell_size + cell_size // 2, off_y + r * cell_size + cell_size // 2)
                    pygame.draw.circle(screen, color, center, cell_size // 2.5)

        # Draw Cursor
        cr, cc = cursor
        cursor_rect = (off_x + cc * cell_size, off_y + cr * cell_size, cell_size, cell_size)
        draw_color = get_color(active_color) if active_color else CURSOR_COLOR
        thickness = max(3, cell_size // 10) if active_color else 3
        pygame.draw.rect(screen, draw_color, cursor_rect, thickness)

        # HUD Text
        mode_text = "3D Torus" if wrap_mode else "2D Grid"
        hud_left = font.render(f"Size: {grid_size}x{grid_size} | Mode: {mode_text}", True, (220, 220, 220))
        hud_right = font.render(f"[ESC] Quit | [G] New Level | [T] Toggle Mode | [+/-] Resize", True, (150, 150, 150))
        
        screen.blit(hud_left, (20, (UI_HEIGHT - hud_left.get_height()) // 2))
        screen.blit(hud_right, (SCREEN_WIDTH - hud_right.get_width() - 20, (UI_HEIGHT - hud_right.get_height()) // 2))

        if level_solved:
            bg_rect = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            bg_rect.fill((0, 0, 0, 180))
            screen.blit(bg_rect, (0, 0))
            win_text = large_font.render("PUZZLE SOLVED! Press ENTER", True, (255, 255, 255))
            screen.blit(win_text, (SCREEN_WIDTH//2 - win_text.get_width()//2, SCREEN_HEIGHT//2 - win_text.get_height()//2))

        pygame.display.flip()
        clock.tick(60)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
