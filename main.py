import pygame
import sys
import json
import os
import math
import random
from collections import deque

from settings import *
from ui import Button, draw_star

class FlowGame:
    def __init__(self, screen_w, screen_h, ui_height, fonts):
        self.w = screen_w
        self.h = screen_h
        self.ui_h = ui_height
        self.fonts = fonts
        
        self.grid = []
        self.grid_size = 0
        self.cell_size = 0
        self.off_x = 0
        self.off_y = 0
        
        self.paths = {}
        self.cursor = [0, 0]
        self.active_color = None
        self.solved = False
        
        self.visual_cursor = None
        self.completed_pulses = {}
        self.history_stack = []
        
        self.moves = 0
        self.perfect_moves = 0
        self.particles = []
        self.hint_path = []
        self.hint_timer = 0.0
        
        # Input handling
        self.action_dr, self.action_dc = 0, 0 # Tracks instantaneous initial presses
        self.move_dr, self.move_dc = 0, 0
        self.move_timer = 0
        self.current_delay = 150
        self.halt_auto_move = False
        
        self.mods = {"Torus": False, "Fog": False, "Meltdown": False}
        self.meltdown_timer = 0.0
        self.level_idx = 0
        self.levels = []
        self.solved_levels = set()

    def load_database(self, file_path="puzzles.json"):
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                self.levels = json.load(f)
        else:
            print(f"ERROR: {file_path} not found!")
            sys.exit()

    def load_level(self, idx):
        if idx >= len(self.levels): return False
        self.level_idx = idx
        level_data = self.levels[idx]
        
        raw_grid = level_data["grid"]
        self.grid_size = len(raw_grid)
        self.grid = [row[:] for row in raw_grid]
        
        margin_padding = int(self.h * 0.20)
        max_board_size = min(self.w, self.h - self.ui_h) - margin_padding
        self.cell_size = max_board_size // self.grid_size
        board_size_px = self.cell_size * self.grid_size
        
        self.off_x = (self.w - board_size_px) // 2
        self.off_y = self.ui_h + (self.h - self.ui_h - board_size_px) // 2
        
        self.paths = {col: [] for row in self.grid for col in row if col != 0}
        self.cursor = [0, 0]
        self.visual_cursor = None
        self.active_color = None
        self.solved = False
        self.completed_pulses = {}
        self.history_stack = []
        
        self.moves = 0
        self.perfect_moves = len(self.paths)
        self.particles = []
        self.hint_path = []
        self.hint_timer = 0.0
        
        self.meltdown_timer = self.grid_size * self.perfect_moves * 0.75 
        return True

    def save_state(self):
        self.history_stack.append({k: v[:] for k, v in self.paths.items()})

    def undo_state(self):
        if self.history_stack:
            self.paths = self.history_stack.pop()

    def check_win(self):
        for col_id, path in self.paths.items():
            if len(path) < 2: return False
            start, end = path[0], path[-1]
            if self.grid[start[0]][start[1]] != col_id or self.grid[end[0]][end[1]] != col_id:
                return False
        return sum(len(path) for path in self.paths.values()) == self.grid_size * self.grid_size

    def spawn_particles(self, r, c, color):
        for _ in range(15):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(50, 150)
            px = self.off_x + c * self.cell_size + self.cell_size // 2
            py = self.off_y + r * self.cell_size + self.cell_size // 2
            self.particles.append({
                'pos': [px, py],
                'vel': [math.cos(angle) * speed, math.sin(angle) * speed],
                'color': color,
                'life': 1.0,
                'max_life': 1.0
            })

    def process_event(self, event):
        if event.type == pygame.KEYDOWN:
            if self.solved:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.solved_levels.add(self.level_idx)
                    return "NEXT_LEVEL"
                return None

            if event.key == pygame.K_z: self.undo_state()
            elif event.key == pygame.K_r: self.load_level(self.level_idx)
            
            # Hint Solver
            elif event.key == pygame.K_h and self.active_color is not None:
                target_pos = None
                start_pos = tuple(self.cursor)
                for rr in range(self.grid_size):
                    for cc in range(self.grid_size):
                        if self.grid[rr][cc] == self.active_color and (rr, cc) != self.paths[self.active_color][0]:
                            target_pos = (rr, cc)
                            break
                    if target_pos: break
                    
                if target_pos:
                    q = deque([(start_pos, [start_pos])])
                    visited = set([start_pos])
                    blocked = set()
                    
                    for rr in range(self.grid_size):
                        for cc in range(self.grid_size):
                            if self.grid[rr][cc] != 0 and (rr, cc) != target_pos and (rr, cc) != self.paths[self.active_color][0]:
                                blocked.add((rr, cc))
                    for col, p in self.paths.items():
                        for cell in p: blocked.add(cell)
                    blocked.discard(start_pos) 
                    
                    while q:
                        curr, pth = q.popleft()
                        if curr == target_pos:
                            self.hint_path = pth
                            self.hint_timer = 2.0 
                            break
                        
                        r, c = curr
                        for dr, dc in [(-1,0), (1,0), (0,-1), (0,1)]:
                            nr, nc = r + dr, c + dc
                            if self.mods["Torus"]:
                                nr %= self.grid_size
                                nc %= self.grid_size
                            if 0 <= nr < self.grid_size and 0 <= nc < self.grid_size:
                                if (nr, nc) not in visited and (nr, nc) not in blocked:
                                    visited.add((nr, nc))
                                    q.append(((nr, nc), pth + [(nr, nc)]))

            # Movement
            dr, dc = 0, 0
            if event.key in (pygame.K_w, pygame.K_UP): dr, dc = -1, 0
            elif event.key in (pygame.K_s, pygame.K_DOWN): dr, dc = 1, 0
            elif event.key in (pygame.K_a, pygame.K_LEFT): dr, dc = 0, -1
            elif event.key in (pygame.K_d, pygame.K_RIGHT): dr, dc = 0, 1

            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                r, c = self.cursor
                if self.active_color is not None:
                    path = self.paths[self.active_color]
                    if len(path) > 1 and self.grid[r][c] == self.active_color and path[-1] == (r, c):
                        self.completed_pulses[self.active_color] = pygame.time.get_ticks()
                        self.spawn_particles(r, c, get_color(self.active_color))
                        self.active_color = None 
                    else:
                        self.save_state()
                        self.paths[self.active_color] = []
                        self.active_color = None
                else:
                    if self.grid[r][c] != 0:
                        self.save_state()
                        self.active_color = self.grid[r][c]
                        self.paths[self.active_color] = [(r, c)]
                        self.moves += 1 
                    else:
                        for col_id, path in self.paths.items():
                            if (r, c) in path:
                                self.save_state()
                                self.active_color = col_id
                                idx = path.index((r, c))
                                self.paths[col_id] = path[:idx+1]
                                self.moves += 1 
                                break

            # FIX: Ensure initial keypress triggers an instantaneous move
            if dr != 0 or dc != 0:
                self.action_dr, self.action_dc = dr, dc 
                self.move_dr, self.move_dc = dr, dc
                self.current_delay = 160 
                self.move_timer = pygame.time.get_ticks()
                self.halt_auto_move = False

        elif event.type == pygame.KEYUP:
            if event.key in (pygame.K_w, pygame.K_UP) and self.move_dr == -1: self.move_dr, self.move_dc = 0, 0
            elif event.key in (pygame.K_s, pygame.K_DOWN) and self.move_dr == 1: self.move_dr, self.move_dc = 0, 0
            elif event.key in (pygame.K_a, pygame.K_LEFT) and self.move_dc == -1: self.move_dr, self.move_dc = 0, 0
            elif event.key in (pygame.K_d, pygame.K_RIGHT) and self.move_dc == 1: self.move_dr, self.move_dc = 0, 0
            
        return None

    def update(self, dt):
        if self.solved: return
        
        current_time = pygame.time.get_ticks()
        
        if self.mods["Meltdown"]:
            self.meltdown_timer -= dt
            if self.meltdown_timer <= 0:
                self.load_level(self.level_idx)
        
        for p in reversed(self.particles):
            p['life'] -= dt
            p['pos'][0] += p['vel'][0] * dt
            p['pos'][1] += p['vel'][1] * dt
            if p['life'] <= 0: self.particles.remove(p)
                
        if self.hint_timer > 0:
            self.hint_timer -= dt
            if self.hint_timer <= 0: self.hint_path = []

        is_auto_move = False
        
        # FIX: Consume the instantaneous action if it exists, otherwise check the holding timer
        action_dr, action_dc = self.action_dr, self.action_dc
        self.action_dr, self.action_dc = 0, 0 

        if action_dr == 0 and action_dc == 0:
            if self.move_dr != 0 or self.move_dc != 0:
                if not self.halt_auto_move and current_time - self.move_timer >= self.current_delay:
                    action_dr, action_dc = self.move_dr, self.move_dc
                    is_auto_move = True
                    self.move_timer = current_time
                    self.current_delay = max(35, self.current_delay - 30) 

        if action_dr != 0 or action_dc != 0:
            r, c = self.cursor
            nr, nc = r + action_dr, c + action_dc
            
            if self.mods["Torus"]:
                nr %= self.grid_size
                nc %= self.grid_size

            if 0 <= nr < self.grid_size and 0 <= nc < self.grid_size:
                dist = abs(r - nr) + abs(c - nc)
                if self.mods["Torus"]:
                    dist = min(abs(r - nr), self.grid_size - abs(r - nr)) + min(abs(c - nc), self.grid_size - abs(c - nc))
                    
                if dist == 1:
                    move_allowed = True
                    if self.active_color is not None:
                        target_dot = self.grid[nr][nc]
                        path = self.paths[self.active_color]
                        if (nr, nc) not in path:
                            head = path[-1]
                            if self.grid[head[0]][head[1]] == self.active_color and len(path) > 1:
                                move_allowed = False
                            elif target_dot != 0 and target_dot != self.active_color:
                                move_allowed = False
                    
                    if move_allowed:
                        self.save_state()
                        self.cursor = [nr, nc]
                        if self.active_color is not None:
                            path = self.paths[self.active_color]
                            if (nr, nc) in path:
                                idx = path.index((nr, nc))
                                self.paths[self.active_color] = path[:idx+1]
                            else:
                                for col_id, p in self.paths.items():
                                    if col_id != self.active_color and (nr, nc) in p:
                                        self.paths[col_id] = [] 
                                path.append((nr, nc))
                        
                        if is_auto_move and self.grid[nr][nc] != 0:
                            self.halt_auto_move = True
                    else:
                        if is_auto_move: self.halt_auto_move = True
        
        target_pos = pygame.math.Vector2(self.off_x + self.cursor[1] * self.cell_size + self.cell_size // 2, 
                                         self.off_y + self.cursor[0] * self.cell_size + self.cell_size // 2)
        if self.visual_cursor is None:
            self.visual_cursor = pygame.math.Vector2(target_pos)
        else:
            if self.visual_cursor.distance_to(target_pos) > self.cell_size * 1.5:
                self.visual_cursor = pygame.math.Vector2(target_pos)
            else:
                self.visual_cursor = self.visual_cursor.lerp(target_pos, min(1.0, 30.0 * dt))

        if not self.solved and self.check_win():
            self.solved = True
            self.solved_levels.add(self.level_idx)
            self.active_color = None

    def draw(self, screen):
        # FIX: Wipe the screen clean before drawing the board to prevent menu-ghosting
        screen.fill(SCREEN_BG)
        
        board_size_px = self.cell_size * self.grid_size
        
        # --- Screen Shake (Meltdown Refinement) ---
        shake_x, shake_y = 0, 0
        if self.mods["Meltdown"] and not self.solved and self.meltdown_timer < 5.0:
            intensity = int((5.0 - self.meltdown_timer) * 3)
            shake_x = random.randint(-intensity, intensity)
            shake_y = random.randint(-intensity, intensity)
            
        base_off_x = self.off_x + shake_x
        base_off_y = self.off_y + shake_y

        pygame.draw.rect(screen, (22, 22, 26), (0, 0, self.w, self.ui_h))
        pygame.draw.rect(screen, BOARD_BG, (base_off_x, base_off_y, board_size_px, board_size_px), border_radius=8)
        
        border_col = BORDER_COLOR
        if self.mods["Meltdown"] and not self.solved and self.meltdown_timer < 5.0:
            border_col = (255, 50, 50)
            
        pygame.draw.rect(screen, border_col, (base_off_x - 2, base_off_y - 2, board_size_px + 4, board_size_px + 4), 3, border_radius=8)

        if self.mods["Torus"]:
            for r in range(self.grid_size):
                for c in range(self.grid_size):
                    if self.grid[r][c] != 0:
                        raw = get_color(self.grid[r][c])
                        ghost = (max(20, raw[0]-150), max(20, raw[1]-150), max(20, raw[2]-150))
                        cs = self.cell_size
                        if r == 0: pygame.draw.circle(screen, ghost, (base_off_x + c * cs + cs // 2, base_off_y + self.grid_size * cs + cs // 2), cs // 3)
                        if r == self.grid_size - 1: pygame.draw.circle(screen, ghost, (base_off_x + c * cs + cs // 2, base_off_y - cs // 2), cs // 3)
                        if c == 0: pygame.draw.circle(screen, ghost, (base_off_x + self.grid_size * cs + cs // 2, base_off_y + r * cs + cs // 2), cs // 3)
                        if c == self.grid_size - 1: pygame.draw.circle(screen, ghost, (base_off_x - cs // 2, base_off_y + r * cs + cs // 2), cs // 3)

        for x in range(self.cell_size, board_size_px, self.cell_size):
            pygame.draw.line(screen, GRID_COLOR, (base_off_x + x, base_off_y), (base_off_x + x, base_off_y + board_size_px), 2)
        for y in range(self.cell_size, board_size_px, self.cell_size):
            pygame.draw.line(screen, GRID_COLOR, (base_off_x, base_off_y + y), (base_off_x + board_size_px, base_off_y + y), 2)

        if self.hint_timer > 0 and len(self.hint_path) > 1:
            hint_surf = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            c_thick = max(2, int(self.cell_size * 0.15))
            h_color = get_color(self.active_color) if self.active_color else (255,255,255)
            alpha_color = (*h_color, 120) 
            
            for i in range(len(self.hint_path) - 1):
                r1, c1 = self.hint_path[i]
                r2, c2 = self.hint_path[i+1]
                p1 = (base_off_x + c1 * self.cell_size + self.cell_size // 2, base_off_y + r1 * self.cell_size + self.cell_size // 2)
                p2 = (base_off_x + c2 * self.cell_size + self.cell_size // 2, base_off_y + r2 * self.cell_size + self.cell_size // 2)
                
                if abs(r1 - r2) <= 1 and abs(c1 - c2) <= 1:
                    pygame.draw.line(hint_surf, alpha_color, p1, p2, c_thick)
            screen.blit(hint_surf, (0, 0))

        pipe_thickness = int(self.cell_size * 0.4)
        joint_radius = int(self.cell_size * 0.2)
        
        current_time = pygame.time.get_ticks()
        for col_id, path in self.paths.items():
            if not path: continue
            color = get_color(col_id)
            
            swell_radius = 0
            if col_id in self.completed_pulses:
                elapsed = current_time - self.completed_pulses[col_id]
                if elapsed < 400.0:
                    progress = elapsed / 400.0
                    ease_out = 1.0 - (1.0 - progress)**2
                    swell_radius = int(math.sin(progress * math.pi) * (self.cell_size * 0.15))
                    ring_rad = int(self.cell_size * 0.4 + (ease_out * self.cell_size * 0.6))
                    ring_thick = max(1, int(self.cell_size * 0.1 * (1.0 - progress)))
                    end_node = path[-1]
                    ring_p = (base_off_x + end_node[1] * self.cell_size + self.cell_size // 2, base_off_y + end_node[0] * self.cell_size + self.cell_size // 2)
                    pygame.draw.circle(screen, color, ring_p, ring_rad, ring_thick)
                else:
                    del self.completed_pulses[col_id]

            c_thick = pipe_thickness + swell_radius
            c_rad = joint_radius + swell_radius // 2
            
            for i in range(len(path) - 1):
                r1, c1 = path[i]
                r2, c2 = path[i+1]
                p1 = (base_off_x + c1 * self.cell_size + self.cell_size // 2, base_off_y + r1 * self.cell_size + self.cell_size // 2)
                p2 = (base_off_x + c2 * self.cell_size + self.cell_size // 2, base_off_y + r2 * self.cell_size + self.cell_size // 2)
                
                if abs(r1 - r2) > 1 or abs(c1 - c2) > 1:
                    if self.mods["Torus"]:
                        if abs(r1 - r2) > 1: 
                            p_out = (p1[0], p1[1] - self.cell_size) if r1 < r2 else (p1[0], p1[1] + self.cell_size)
                            p_in = (p2[0], p2[1] + self.cell_size) if r1 < r2 else (p2[0], p2[1] - self.cell_size)
                            pygame.draw.line(screen, color, p1, p_out, c_thick)
                            pygame.draw.line(screen, color, p2, p_in, c_thick)
                        elif abs(c1 - c2) > 1: 
                            p_out = (p1[0] - self.cell_size, p1[1]) if c1 < c2 else (p1[0] + self.cell_size, p1[1])
                            p_in = (p2[0] + self.cell_size, p2[1]) if c1 < c2 else (p2[0] - self.cell_size, p2[1])
                            pygame.draw.line(screen, color, p1, p_out, c_thick)
                            pygame.draw.line(screen, color, p2, p_in, c_thick)
                else:
                    pygame.draw.line(screen, color, p1, p2, c_thick)
                
            for r, c in path:
                p = (base_off_x + c * self.cell_size + self.cell_size // 2, base_off_y + r * self.cell_size + self.cell_size // 2)
                pygame.draw.circle(screen, color, p, c_rad)

        for r in range(self.grid_size):
            for c in range(self.grid_size):
                if self.grid[r][c] != 0:
                    color = get_color(self.grid[r][c])
                    center = (base_off_x + c * self.cell_size + self.cell_size // 2, base_off_y + r * self.cell_size + self.cell_size // 2)
                    pygame.draw.circle(screen, color, center, int(self.cell_size * 0.35))

        for p in self.particles:
            size = max(1, int(12 * (p['life'] / p['max_life'])))
            rect = pygame.Rect(0, 0, size, size)
            rect.center = (p['pos'][0] + shake_x, p['pos'][1] + shake_y)
            pygame.draw.rect(screen, p['color'], rect)

        draw_color = get_color(self.active_color) if self.active_color else CURSOR_COLOR
        thickness = max(4, self.cell_size // 8) if self.active_color else 3
        
        cursor_rect = pygame.Rect(0, 0, self.cell_size, self.cell_size)
        if self.visual_cursor:
            cursor_rect.center = (self.visual_cursor.x + shake_x, self.visual_cursor.y + shake_y)
        pygame.draw.rect(screen, draw_color, cursor_rect, thickness, border_radius=8)

        if self.mods["Fog"]:
            fog_surf = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            fog_surf.fill((0, 0, 0, 250)) 
            
            breathe = math.sin(current_time / 200.0) * (self.cell_size * 0.1)
            vis_radius = int(self.cell_size * 1.5 + breathe)
            
            if self.visual_cursor:
                pygame.draw.circle(fog_surf, (0, 0, 0, 0), (int(self.visual_cursor.x + shake_x), int(self.visual_cursor.y + shake_y)), vis_radius)
            
            for col_id, path in self.paths.items():
                if len(path) > 1 and self.grid[path[-1][0]][path[-1][1]] == col_id:
                    for r, c in path:
                        px = base_off_x + c * self.cell_size + self.cell_size // 2
                        py = base_off_y + r * self.cell_size + self.cell_size // 2
                        pygame.draw.circle(fog_surf, (0, 0, 0, 150), (px, py), self.cell_size // 2)
            
            screen.blit(fog_surf, (0, 0))

        diff = self.levels[self.level_idx].get("difficulty", "Unknown")
        mod_str = " | ".join([m for m, active in self.mods.items() if active])
        if mod_str: mod_str = " | " + mod_str
        
        time_col = (255, 50, 50) if (self.mods["Meltdown"] and self.meltdown_timer < 5.0) else (220, 220, 220)
        time_str = f" | TIME: {max(0.0, self.meltdown_timer):.1f}s" if self.mods["Meltdown"] else ""
        
        hud_font = self.fonts['hud']
        hud_left = hud_font.render(f"{diff} {self.level_idx + 1} | Moves: {self.moves}/{self.perfect_moves}{time_str}{mod_str}", True, (220, 220, 220))
        time_surf = hud_font.render(time_str, True, time_col)
        hud_right = hud_font.render(f"[ESC] Menu  [R] Restart  [Z] Undo  [H] Hint", True, (150, 150, 150))
        
        screen.blit(hud_left, (30, (self.ui_h - hud_left.get_height()) // 2))
        screen.blit(time_surf, (30 + hud_left.get_width(), (self.ui_h - time_surf.get_height()) // 2))
        screen.blit(hud_right, (self.w - hud_right.get_width() - 30, (self.ui_h - hud_right.get_height()) // 2))

        if self.solved:
            overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 220))
            screen.blit(overlay, (0, 0))
            
            win_text = self.fonts['title'].render("SOLVED!", True, DISTINCT_COLORS[1])
            stars = 3
            if self.moves > self.perfect_moves + 2: stars = 2
            if self.moves > self.perfect_moves + 6: stars = 1
            
            rating_text = self.fonts['large'].render("Rating: ", True, (255, 215, 0))
            sub_text = self.fonts['main'].render("Press ENTER to continue", True, (200, 200, 200))
            
            star_size = int(self.h * 0.025)
            star_spacing = star_size * 2.5
            total_w = rating_text.get_width() + (3 * star_spacing)
            start_x = self.w // 2 - total_w // 2
            base_y = self.h // 2
            
            screen.blit(win_text, (self.w//2 - win_text.get_width()//2, base_y - win_text.get_height()))
            screen.blit(rating_text, (start_x, base_y))
            
            star_start_x = start_x + rating_text.get_width() + star_size
            star_y = base_y + rating_text.get_height() // 2
            
            for i in range(3):
                color = (255, 215, 0) if i < stars else BORDER_COLOR 
                draw_star(screen, star_start_x + (i * star_spacing), star_y, star_size, color)

            screen.blit(sub_text, (self.w//2 - sub_text.get_width()//2, base_y + rating_text.get_height() + 20))


def main():
    pygame.init()
    info = pygame.display.Info()
    w, h = info.current_w, info.current_h
    screen = pygame.display.set_mode((w, h), pygame.FULLSCREEN)
    
    fonts = {
        'main': pygame.font.SysFont("segoeui, arial", int(h * 0.035)) if pygame.font.match_font("segoeui") else pygame.font.Font(None, int(h * 0.04)),
        'large': pygame.font.SysFont("segoeui, arial", int(h * 0.06)) if pygame.font.match_font("segoeui") else pygame.font.Font(None, int(h * 0.06)),
        'title': pygame.font.SysFont("segoeui, arial", int(h * 0.12), bold=True) if pygame.font.match_font("segoeui") else pygame.font.Font(None, int(h * 0.12)),
        'hud': pygame.font.SysFont("segoeui, arial", int(h * 0.03)) if pygame.font.match_font("segoeui") else pygame.font.Font(None, int(h * 0.03))
    }
    
    game = FlowGame(w, h, int(h * 0.08), fonts)
    game.load_database()
    
    state = "MENU"
    clock = pygame.time.Clock()
    diff_page = 0
    diff_order = ["Easy", "Normal", "Hard", "Very Hard", "Impossible"]
    
    cat_levels = {diff: [] for diff in diff_order}
    for idx, lvl in enumerate(game.levels):
        cat_levels[lvl.get("difficulty", "Normal")].append((idx, lvl))
        
    buttons = {} 

    running = True
    while running:
        dt = clock.tick(60) / 1000.0 
        mouse_pos = pygame.mouse.get_pos()
        click = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1: click = True
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if state == "PLAYING": state = "LEVEL_SELECT"
                elif state == "LEVEL_SELECT": state = "MENU"
                else: running = False
                
            if state == "PLAYING":
                res = game.process_event(event)
                if res == "NEXT_LEVEL":
                    if not game.load_level(game.level_idx + 1): state = "LEVEL_SELECT"

        if state == "PLAYING":
            game.update(dt)
            game.draw(screen)
            
        elif state == "MENU":
            screen.fill(SCREEN_BG)
            title = fonts['title'].render("FLOW FREE", True, DISTINCT_COLORS[2]) 
            screen.blit(title, (w//2 - title.get_width()//2, h * 0.15))
            
            sub = fonts['main'].render("Chaos Edition", True, (150, 150, 150))
            screen.blit(sub, (w//2 - sub.get_width()//2, h * 0.28))

            bw, bh = int(w * 0.25), int(h * 0.08)
            bx = w//2 - bw//2
            
            if 'play' not in buttons: buttons['play'] = Button("Play / Resume", bx, h * 0.40, bw, bh, BTN_DEFAULT, BTN_HOVER)
            if buttons['play'].draw(screen, fonts['main'], mouse_pos, dt) and click:
                game.load_level(game.level_idx)
                state = "PLAYING"
                
            if 'select' not in buttons: buttons['select'] = Button("Level Select", bx, h * 0.50, bw, bh, BTN_DEFAULT, BTN_HOVER)
            if buttons['select'].draw(screen, fonts['main'], mouse_pos, dt) and click: state = "LEVEL_SELECT"
            
            mod_y, mod_w, mod_gap = h * 0.65, int(w * 0.18), int(w * 0.02)
            mx = w // 2 - ((mod_w * 3) + (mod_gap * 2)) // 2
            
            for i, mod in enumerate(["Torus", "Fog", "Meltdown"]):
                bid = f"mod_{mod}"
                if bid not in buttons: buttons[bid] = Button(mod, mx + i*(mod_w+mod_gap), mod_y, mod_w, bh, BTN_DEFAULT, BTN_HOVER)
                buttons[bid].default_col = BTN_MOD_ACTIVE if game.mods[mod] else BTN_DEFAULT
                buttons[bid].hover_col = BTN_MOD_ACTIVE_HOVER if game.mods[mod] else BTN_HOVER
                if buttons[bid].draw(screen, fonts['main'], mouse_pos, dt) and click: game.mods[mod] = not game.mods[mod]

            if 'quit' not in buttons: buttons['quit'] = Button("Quit Game", bx, h * 0.80, bw, bh, BTN_DEFAULT, BTN_HOVER)
            if buttons['quit'].draw(screen, fonts['main'], mouse_pos, dt) and click: running = False

        elif state == "LEVEL_SELECT":
            screen.fill(SCREEN_BG)
            active_diff = diff_order[diff_page]
            lvls = cat_levels[active_diff]
            
            title = fonts['title'].render(active_diff.upper(), True, DISTINCT_COLORS[diff_page])
            screen.blit(title, (w//2 - title.get_width()//2, h * 0.05))
            screen.blit(fonts['hud'].render("[ESC] Back to Menu", True, (150, 150, 150)), (30, 30))
            
            aw, ah = 60, 100
            if diff_page > 0:
                if 'prev' not in buttons: buttons['prev'] = Button("<", int(w * 0.05), int(h * 0.4), aw, ah, BTN_DEFAULT, BTN_HOVER)
                if buttons['prev'].draw(screen, fonts['large'], mouse_pos, dt) and click: diff_page -= 1
            if diff_page < len(diff_order) - 1:
                if 'next' not in buttons: buttons['next'] = Button(">", int(w * 0.95) - aw, int(h * 0.4), aw, ah, BTN_DEFAULT, BTN_HOVER)
                if buttons['next'].draw(screen, fonts['large'], mouse_pos, dt) and click: diff_page += 1

            if lvls:
                cols = min(6, len(lvls))
                pad = 15
                bsize = min(int(min((w*0.7 - (cols-1)*pad)//cols, (h*0.6 - 4*pad)//5)), 100)
                
                sx = (w - (cols * bsize + (cols - 1) * pad)) // 2
                sy = int(h * 0.25)

                for li, (gidx, _) in enumerate(lvls):
                    r, c = li // cols, li % cols
                    bx, by = sx + c * (bsize + pad), sy + r * (bsize + pad)
                    
                    bid = f"lvl_{gidx}"
                    if bid not in buttons: buttons[bid] = Button(str(li + 1), bx, by, bsize, bsize, BTN_DEFAULT, BTN_HOVER)
                    
                    is_solved = gidx in game.solved_levels
                    buttons[bid].default_col = BTN_SOLVED if is_solved else BTN_DEFAULT
                    buttons[bid].hover_col = BTN_SOLVED_HOVER if is_solved else BTN_HOVER
                    buttons[bid].rect.x, buttons[bid].rect.y = bx, by 
                    
                    if buttons[bid].draw(screen, fonts['main'], mouse_pos, dt) and click:
                        game.load_level(gidx)
                        state = "PLAYING"

        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
