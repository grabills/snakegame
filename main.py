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
        self.w, self.h, self.ui_h, self.fonts = screen_w, screen_h, ui_height, fonts
        
        self.grid, self.grid_size, self.cell_size = [], 0, 0
        self.off_x, self.off_y = 0, 0
        self.paths, self.cursor, self.active_color = {}, [0, 0], None
        self.solved = False
        
        self.visual_cursor, self.completed_pulses, self.history_stack = None, {}, []
        self.moves, self.perfect_moves = 0, 0
        self.particles, self.hint_path, self.hint_timer = [], [], 0.0
        
        self.action_dr, self.action_dc = 0, 0 
        self.move_dr, self.move_dc, self.move_timer, self.current_delay, self.halt_auto_move = 0, 0, 0, 150, False
        
        self.mods = {"Fog": False, "Meltdown": False}
        self.meltdown_timer = 0.0
        self.level_idx = 0
        self.levels = []
        self.solved_levels = set()
        self.is_torus = False

    def load_database(self, file_path="puzzles.json"):
        if os.path.exists(file_path):
            with open(file_path, "r") as f: self.levels = json.load(f)
        else:
            print(f"ERROR: {file_path} not found!"); sys.exit()

    def load_level(self, idx):
        if idx >= len(self.levels): return False
        self.level_idx = idx
        self.grid_size = len(self.levels[idx]["grid"])
        self.grid = [row[:] for row in self.levels[idx]["grid"]]
        self.is_torus = (self.levels[idx].get("difficulty") == "Torus")
        
        max_board = min(self.w, self.h - self.ui_h) - int(self.h * 0.20)
        self.cell_size = max_board // self.grid_size
        
        self.off_x = (self.w - (self.cell_size * self.grid_size)) // 2
        self.off_y = self.ui_h + (self.h - self.ui_h - (self.cell_size * self.grid_size)) // 2
        
        self.paths = {col: [] for row in self.grid for col in row if col > 0}
        self.cursor, self.visual_cursor, self.active_color, self.solved = [0, 0], None, None, False
        self.completed_pulses, self.history_stack, self.moves, self.particles, self.hint_path, self.hint_timer = {}, [], 0, [], [], 0.0
        
        self.perfect_moves = len(self.paths)
        self.meltdown_timer = self.grid_size * self.perfect_moves * 0.75 
        return True

    def save_state(self): 
        self.history_stack.append({k: v[:] for k, v in self.paths.items()})

    def undo_state(self):
        if self.history_stack: self.paths = self.history_stack.pop()

    def check_win(self):
        for col_id, path in self.paths.items():
            if len(path) < 2: return False
            if self.grid[path[0][0]][path[0][1]] != col_id or self.grid[path[-1][0]][path[-1][1]] != col_id: return False
            
        target_volume = sum(1 for r in range(self.grid_size) for c in range(self.grid_size) if self.grid[r][c] != HOLE)
        target_volume += sum(1 for r in range(self.grid_size) for c in range(self.grid_size) if self.grid[r][c] == BRIDGE)
        return sum(len(path) for path in self.paths.values()) == target_volume

    def process_event(self, event):
        if event.type == pygame.KEYDOWN:
            if self.solved:
                if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.solved_levels.add(self.level_idx)
                    return "NEXT_LEVEL"
                return None

            if event.key == pygame.K_z: self.undo_state()
            elif event.key == pygame.K_r: self.load_level(self.level_idx)
            elif event.key == pygame.K_h and self.active_color: self.trigger_hint()

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
                        for _ in range(18):
                            a, s = random.uniform(0, 2*math.pi), random.uniform(80, 200)
                            self.particles.append({
                                'pos': [self.off_x + c*self.cell_size + self.cell_size//2, self.off_y + r*self.cell_size + self.cell_size//2], 
                                'vel': [math.cos(a)*s, math.sin(a)*s], 
                                'color': get_color(self.active_color), 
                                'life': 1.0, 'max_life': 1.0
                            })
                        self.active_color = None 
                    else:
                        self.save_state(); self.paths[self.active_color] = []; self.active_color = None
                elif self.grid[r][c] > 0:
                    self.save_state(); self.active_color = self.grid[r][c]; self.paths[self.active_color] = [(r, c)]; self.moves += 1 
                else:
                    for col_id, path in self.paths.items():
                        if (r, c) in path:
                            self.save_state(); self.active_color = col_id; self.paths[col_id] = path[:path.index((r, c))+1]; self.moves += 1; break

            if dr != 0 or dc != 0:
                self.action_dr, self.action_dc = dr, dc 
                self.move_dr, self.move_dc, self.current_delay, self.move_timer, self.halt_auto_move = dr, dc, 160, pygame.time.get_ticks(), False

        elif event.type == pygame.KEYUP:
            if event.key in (pygame.K_w, pygame.K_UP) and self.move_dr == -1: self.move_dr, self.move_dc = 0, 0
            elif event.key in (pygame.K_s, pygame.K_DOWN) and self.move_dr == 1: self.move_dr, self.move_dc = 0, 0
            elif event.key in (pygame.K_a, pygame.K_LEFT) and self.move_dc == -1: self.move_dr, self.move_dc = 0, 0
            elif event.key in (pygame.K_d, pygame.K_RIGHT) and self.move_dc == 1: self.move_dr, self.move_dc = 0, 0
        return None

    def trigger_hint(self):
        target_pos, start_pos = None, tuple(self.cursor)
        for rr in range(self.grid_size):
            for cc in range(self.grid_size):
                if self.grid[rr][cc] == self.active_color and (rr, cc) != self.paths[self.active_color][0]: 
                    target_pos = (rr, cc); break
            if target_pos: break
            
        if target_pos:
            q, visited, blocked = deque([(start_pos, [start_pos])]), set([start_pos]), set()
            for rr in range(self.grid_size):
                for cc in range(self.grid_size):
                    if (self.grid[rr][cc] > 0 and (rr, cc) != target_pos and (rr, cc) != self.paths[self.active_color][0]) or self.grid[rr][cc] == HOLE: 
                        blocked.add((rr, cc))
            for p in self.paths.values():
                for cell in p: blocked.add(cell)
            blocked.discard(start_pos) 
            
            while q:
                curr, pth = q.popleft()
                if curr == target_pos: self.hint_path, self.hint_timer = pth, 2.0; break
                for dr, dc in [(-1,0), (1,0), (0,-1), (0,1)]:
                    nr, nc = curr[0] + dr, curr[1] + dc
                    if self.is_torus: nr, nc = nr % self.grid_size, nc % self.grid_size
                    if 0 <= nr < self.grid_size and 0 <= nc < self.grid_size:
                        if (nr, nc) not in visited and (nr, nc) not in blocked:
                            visited.add((nr, nc)); q.append(((nr, nc), pth + [(nr, nc)]))

    def update(self, dt):
        if self.solved: return
        current_time = pygame.time.get_ticks()
        
        if self.mods["Meltdown"]:
            self.meltdown_timer -= dt
            if self.meltdown_timer <= 0: self.load_level(self.level_idx)
        
        for p in reversed(self.particles):
            p['life'] -= dt
            p['pos'][0] += p['vel'][0] * dt
            p['pos'][1] += p['vel'][1] * dt
            p['vel'][0] *= 0.9  
            p['vel'][1] *= 0.9
            if p['life'] <= 0: self.particles.remove(p)
                
        if self.hint_timer > 0:
            self.hint_timer -= dt
            if self.hint_timer <= 0: self.hint_path = []

        action_dr, action_dc = self.action_dr, self.action_dc
        self.action_dr, self.action_dc = 0, 0 
        is_auto_move = False

        if action_dr == 0 and action_dc == 0 and (self.move_dr != 0 or self.move_dc != 0):
            if not self.halt_auto_move and current_time - self.move_timer >= self.current_delay:
                action_dr, action_dc = self.move_dr, self.move_dc
                is_auto_move, self.move_timer, self.current_delay = True, current_time, max(35, self.current_delay - 30) 

        if action_dr != 0 or action_dc != 0:
            r, c = self.cursor
            nr, nc = r + action_dr, c + action_dc
            
            if self.is_torus: nr, nc = nr % self.grid_size, nc % self.grid_size

            if 0 <= nr < self.grid_size and 0 <= nc < self.grid_size:
                dist = min(abs(r - nr), self.grid_size - abs(r - nr)) + min(abs(c - nc), self.grid_size - abs(c - nc)) if self.is_torus else abs(r - nr) + abs(c - nc)
                    
                if dist == 1:
                    move_allowed = True
                    target_val = self.grid[nr][nc]
                    
                    if target_val == HOLE: 
                        move_allowed = False
                    elif self.active_color is not None:
                        path = self.paths[self.active_color]
                        
                        if self.grid[r][c] == BRIDGE and len(path) >= 2:
                            prev_r, prev_c = path[-2]
                            heading_r, heading_c = r - prev_r, c - prev_c
                            if self.is_torus: 
                                if heading_r > 1: heading_r = -1
                                elif heading_r < -1: heading_r = 1
                                if heading_c > 1: heading_c = -1
                                elif heading_c < -1: heading_c = 1
                            if action_dr != heading_r or action_dc != heading_c:
                                move_allowed = False
                        
                        if move_allowed and target_val == BRIDGE and (nr, nc) not in path:
                            occupants = [col for col, p in self.paths.items() if (nr, nc) in p and col != self.active_color]
                            if len(occupants) == 2:
                                move_allowed = False 
                            elif len(occupants) == 1:
                                occ_path = self.paths[occupants[0]]
                                idx = occ_path.index((nr, nc))
                                if idx == 0 or idx == len(occ_path)-1: move_allowed = False 
                                else:
                                    p_occ, n_occ = occ_path[idx-1], occ_path[idx+1]
                                    if p_occ[1] == n_occ[1] and action_dc == 0: move_allowed = False 
                                    if p_occ[0] == n_occ[0] and action_dr == 0: move_allowed = False 

                        elif (nr, nc) not in path:
                            head = path[-1]
                            if self.grid[head[0]][head[1]] == self.active_color and len(path) > 1: move_allowed = False
                            elif target_val > 0 and target_val != self.active_color: move_allowed = False
                    
                    if move_allowed:
                        self.save_state()
                        self.cursor = [nr, nc]
                        if self.active_color is not None:
                            path = self.paths[self.active_color]
                            if (nr, nc) in path:
                                self.paths[self.active_color] = path[:path.index((nr, nc))+1]
                            else:
                                for col_id, p in self.paths.items():
                                    if col_id != self.active_color and (nr, nc) in p and self.grid[nr][nc] != BRIDGE:
                                        self.paths[col_id] = [] 
                                path.append((nr, nc))
                        if is_auto_move and self.grid[nr][nc] > 0: self.halt_auto_move = True
                    else:
                        if is_auto_move: self.halt_auto_move = True
            
        target_pos = pygame.math.Vector2(self.off_x + self.cursor[1]*self.cell_size + self.cell_size//2, self.off_y + self.cursor[0]*self.cell_size + self.cell_size//2)
        if self.visual_cursor is None or self.visual_cursor.distance_to(target_pos) > self.cell_size * 1.5:
            self.visual_cursor = pygame.math.Vector2(target_pos)
        else:
            self.visual_cursor = self.visual_cursor.lerp(target_pos, min(1.0, 30.0 * dt))

        if not self.solved and self.check_win():
            self.solved, self.active_color = True, None
            self.solved_levels.add(self.level_idx)

    def draw(self, screen):
        screen.fill(SCREEN_BG)
        board_px = self.cell_size * self.grid_size
        
        shake_x, shake_y = 0, 0
        if self.mods["Meltdown"] and not self.solved and self.meltdown_timer < 5.0:
            intensity = int((5.0 - self.meltdown_timer) * 3)
            shake_x, shake_y = random.randint(-intensity, intensity), random.randint(-intensity, intensity)
            
        b_off_x, b_off_y = self.off_x + shake_x, self.off_y + shake_y

        pygame.draw.rect(screen, (22, 22, 26), (0, 0, self.w, self.ui_h))
        pygame.draw.line(screen, (35, 35, 45), (0, self.ui_h), (self.w, self.ui_h), 2)
        
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                if self.grid[r][c] != HOLE:
                    tile_rect = (b_off_x + c*self.cell_size + 2, b_off_y + r*self.cell_size + 2, self.cell_size - 4, self.cell_size - 4)
                    pygame.draw.rect(screen, BOARD_BG, tile_rect, border_radius=8)
                    
                    if self.grid[r][c] == BRIDGE:
                        cx, cy = b_off_x + c*self.cell_size + self.cell_size//2, b_off_y + r*self.cell_size + self.cell_size//2
                        chan_w = int(self.cell_size * 0.4)
                        pygame.draw.rect(screen, (20, 20, 25), (cx - chan_w//2, cy - self.cell_size//2 + 4, chan_w, self.cell_size - 8), border_radius=2)
                        pygame.draw.rect(screen, (60, 60, 75), (cx - self.cell_size//2 + 4, cy - chan_w//2 - 4, self.cell_size - 8, 8), border_radius=2)
                        pygame.draw.rect(screen, (60, 60, 75), (cx - self.cell_size//2 + 4, cy + chan_w//2 - 4, self.cell_size - 8, 8), border_radius=2)

        if self.hint_timer > 0 and len(self.hint_path) > 1:
            hint_surf = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            c_thick = max(2, int(self.cell_size * 0.15))
            h_color = get_color(self.active_color) if self.active_color else (255,255,255)
            alpha_color = (*h_color, 120) 
            
            for i in range(len(self.hint_path) - 1):
                r1, c1 = self.hint_path[i]
                r2, c2 = self.hint_path[i+1]
                p1 = (b_off_x + c1 * self.cell_size + self.cell_size // 2, b_off_y + r1 * self.cell_size + self.cell_size // 2)
                p2 = (b_off_x + c2 * self.cell_size + self.cell_size // 2, b_off_y + r2 * self.cell_size + self.cell_size // 2)
                
                if abs(r1 - r2) > 1 or abs(c1 - c2) > 1:
                    if self.is_torus:
                        if abs(r1 - r2) > 1: 
                            pygame.draw.line(hint_surf, alpha_color, p1, (p1[0], p1[1] - self.cell_size if r1 < r2 else p1[1] + self.cell_size), c_thick)
                            pygame.draw.line(hint_surf, alpha_color, p2, (p2[0], p2[1] + self.cell_size if r1 < r2 else p2[1] - self.cell_size), c_thick)
                        elif abs(c1 - c2) > 1: 
                            pygame.draw.line(hint_surf, alpha_color, p1, (p1[0] - self.cell_size if c1 < c2 else p1[0] + self.cell_size, p1[1]), c_thick)
                            pygame.draw.line(hint_surf, alpha_color, p2, (p2[0] + self.cell_size if c1 < c2 else p2[0] - self.cell_size, p2[1]), c_thick)
                else:
                    pygame.draw.line(hint_surf, alpha_color, p1, p2, c_thick)
            screen.blit(hint_surf, (0, 0))

        pipe_thick, joint_rad = int(self.cell_size * 0.4), int(self.cell_size * 0.2)
        
        current_time = pygame.time.get_ticks()
        for col_id, path in self.paths.items():
            if not path: continue
            color = get_color(col_id)
            swell = 0
            if col_id in self.completed_pulses:
                elapsed = current_time - self.completed_pulses[col_id]
                if elapsed < 400.0:
                    prog = elapsed / 400.0
                    swell = int(math.sin(prog * math.pi) * (self.cell_size * 0.15))
                    rr = int(self.cell_size * 0.4 + ((1.0 - (1.0 - prog)**2) * self.cell_size * 0.6))
                    pygame.draw.circle(screen, color, (b_off_x + path[-1][1]*self.cell_size + self.cell_size//2, b_off_y + path[-1][0]*self.cell_size + self.cell_size//2), rr, max(1, int(self.cell_size * 0.1 * (1.0 - prog))))
                else: del self.completed_pulses[col_id]

            c_thick, c_rad = pipe_thick + swell, joint_rad + swell // 2
            
            for i in range(len(path) - 1):
                r1, c1, r2, c2 = path[i][0], path[i][1], path[i+1][0], path[i+1][1]
                p1 = (b_off_x + c1 * self.cell_size + self.cell_size // 2, b_off_y + r1 * self.cell_size + self.cell_size // 2)
                p2 = (b_off_x + c2 * self.cell_size + self.cell_size // 2, b_off_y + r2 * self.cell_size + self.cell_size // 2)
                
                if abs(r1 - r2) > 1 or abs(c1 - c2) > 1:
                    if self.is_torus:
                        if abs(r1 - r2) > 1: 
                            pygame.draw.line(screen, color, p1, (p1[0], p1[1] - self.cell_size if r1 < r2 else p1[1] + self.cell_size), c_thick)
                            pygame.draw.line(screen, color, p2, (p2[0], p2[1] + self.cell_size if r1 < r2 else p2[1] - self.cell_size), c_thick)
                        elif abs(c1 - c2) > 1: 
                            pygame.draw.line(screen, color, p1, (p1[0] - self.cell_size if c1 < c2 else p1[0] + self.cell_size, p1[1]), c_thick)
                            pygame.draw.line(screen, color, p2, (p2[0] + self.cell_size if c1 < c2 else p2[0] - self.cell_size, p2[1]), c_thick)
                else: pygame.draw.line(screen, color, p1, p2, c_thick)
                
            for r, c in path:
                pygame.draw.circle(screen, color, (b_off_x + c*self.cell_size + self.cell_size//2, b_off_y + r*self.cell_size + self.cell_size//2), c_rad)

        for r in range(self.grid_size):
            for c in range(self.grid_size):
                if self.grid[r][c] > 0:
                    dot_color = get_color(self.grid[r][c])
                    cx, cy = b_off_x + c*self.cell_size + self.cell_size//2, b_off_y + r*self.cell_size + self.cell_size//2
                    pygame.draw.circle(screen, dot_color, (cx, cy), int(self.cell_size * 0.35))
                    pygame.draw.circle(screen, (255, 255, 255), (cx - int(self.cell_size * 0.1), cy - int(self.cell_size * 0.1)), int(self.cell_size * 0.08)) 

        for p in self.particles:
            rect = pygame.Rect(0, 0, max(1, int(10 * (p['life'] / p['max_life']))), max(1, int(10 * (p['life'] / p['max_life']))))
            rect.center = (p['pos'][0] + shake_x, p['pos'][1] + shake_y)
            pygame.draw.rect(screen, p['color'], rect, border_radius=2)

        if self.visual_cursor and self.grid[self.cursor[0]][self.cursor[1]] != HOLE:
            draw_col = get_color(self.active_color) if self.active_color else CURSOR_COLOR
            c_rect = pygame.Rect(0, 0, self.cell_size, self.cell_size)
            c_rect.center = (self.visual_cursor.x + shake_x, self.visual_cursor.y + shake_y)
            pygame.draw.rect(screen, draw_col, c_rect, max(4, self.cell_size // 8) if self.active_color else 3, border_radius=10)

        # --- PERFECT CONTINUOUS LINE FOG MASK ---
        if self.mods["Fog"]:
            fog_surf = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            fog_surf.fill((0, 0, 0, 250)) 
            
            # Cursor Torch Glow
            if self.visual_cursor:
                cx, cy = int(self.visual_cursor.x + shake_x), int(self.visual_cursor.y + shake_y)
                vis_radius = int(self.cell_size * 1.5 + math.sin(current_time / 200.0) * (self.cell_size * 0.1))
                hole = pygame.Surface((vis_radius*2, vis_radius*2), pygame.SRCALPHA)
                for i in range(vis_radius, 0, -3):
                    pygame.draw.circle(hole, (255, 255, 255, int(250 * (i / vis_radius))), (vis_radius, vis_radius), i)
                fog_surf.blit(hole, (cx - vis_radius, cy - vis_radius), special_flags=pygame.BLEND_RGBA_SUB)
            
            # Continuous Path Glow
            path_mask = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            mask_thick = int(self.cell_size * 0.5)
            mask_rad = mask_thick // 2
            
            for col_id, path in self.paths.items():
                if len(path) > 1 and self.grid[path[-1][0]][path[-1][1]] == col_id:
                    for i in range(len(path) - 1):
                        r1, c1, r2, c2 = path[i][0], path[i][1], path[i+1][0], path[i+1][1]
                        p1 = (b_off_x + c1 * self.cell_size + self.cell_size // 2, b_off_y + r1 * self.cell_size + self.cell_size // 2)
                        p2 = (b_off_x + c2 * self.cell_size + self.cell_size // 2, b_off_y + r2 * self.cell_size + self.cell_size // 2)
                        
                        if abs(r1 - r2) > 1 or abs(c1 - c2) > 1:
                            if self.is_torus:
                                if abs(r1 - r2) > 1: 
                                    pygame.draw.line(path_mask, (255,255,255,120), p1, (p1[0], p1[1] - self.cell_size if r1 < r2 else p1[1] + self.cell_size), mask_thick)
                                    pygame.draw.line(path_mask, (255,255,255,120), p2, (p2[0], p2[1] + self.cell_size if r1 < r2 else p2[1] - self.cell_size), mask_thick)
                                elif abs(c1 - c2) > 1: 
                                    pygame.draw.line(path_mask, (255,255,255,120), p1, (p1[0] - self.cell_size if c1 < c2 else p1[0] + self.cell_size, p1[1]), mask_thick)
                                    pygame.draw.line(path_mask, (255,255,255,120), p2, (p2[0] + self.cell_size if c1 < c2 else p2[0] - self.cell_size, p2[1]), mask_thick)
                        else: 
                            pygame.draw.line(path_mask, (255,255,255,120), p1, p2, mask_thick)
                            
                    for r, c in path: 
                        pygame.draw.circle(path_mask, (255,255,255,120), (b_off_x + c*self.cell_size + self.cell_size//2, b_off_y + r*self.cell_size + self.cell_size//2), mask_rad)
            
            fog_surf.blit(path_mask, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
            screen.blit(fog_surf, (0, 0))

        diff = self.levels[self.level_idx].get("difficulty", "Unknown")
        hud_left = self.fonts['hud'].render(f"{diff} {self.level_idx + 1}  |  Moves: {self.moves}/{self.perfect_moves}", True, (220, 220, 220))
        screen.blit(hud_left, (30, (self.ui_h - hud_left.get_height()) // 2))
        
        if self.mods["Meltdown"]:
            time_surf = self.fonts['hud'].render(f"  |  TIME: {max(0.0, self.meltdown_timer):.1f}s", True, (255, 50, 50) if self.meltdown_timer < 5.0 else (220, 220, 220))
            screen.blit(time_surf, (30 + hud_left.get_width(), (self.ui_h - time_surf.get_height()) // 2))

        hud_right = self.fonts['hud'].render(f"[ESC] Menu    [R] Restart    [Z] Undo    [H] Hint", True, (150, 150, 150))
        screen.blit(hud_right, (self.w - hud_right.get_width() - 30, (self.ui_h - hud_right.get_height()) // 2))

        if self.solved:
            overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 220))
            screen.blit(overlay, (0, 0))
            win_text = self.fonts['title'].render("SOLVED!", True, DISTINCT_COLORS[1])
            stars = 3 if self.moves <= self.perfect_moves + 2 else (2 if self.moves <= self.perfect_moves + 6 else 1)
            rating_text = self.fonts['large'].render("Rating: ", True, (255, 215, 0))
            
            total_w = rating_text.get_width() + (3 * int(self.h * 0.0625))
            start_x, base_y = self.w // 2 - total_w // 2, self.h // 2
            
            screen.blit(win_text, (self.w//2 - win_text.get_width()//2, base_y - win_text.get_height()))
            screen.blit(rating_text, (start_x, base_y))
            for i in range(3): draw_star(screen, start_x + rating_text.get_width() + int(self.h * 0.025) + (i * int(self.h * 0.0625)), base_y + rating_text.get_height() // 2, int(self.h * 0.025), (255, 215, 0) if i < stars else BORDER_COLOR)
            sub_text = self.fonts['main'].render("Press ENTER to continue", True, (200, 200, 200))
            screen.blit(sub_text, (self.w//2 - sub_text.get_width()//2, base_y + rating_text.get_height() + 20))

def main():
    pygame.init()
    w, h = pygame.display.Info().current_w, pygame.display.Info().current_h
    screen = pygame.display.set_mode((w, h), pygame.FULLSCREEN)
    fonts = {
        'main': pygame.font.SysFont("segoeui, arial", int(h * 0.035)) if pygame.font.match_font("segoeui") else pygame.font.Font(None, int(h * 0.04)),
        'large': pygame.font.SysFont("segoeui, arial", int(h * 0.06)) if pygame.font.match_font("segoeui") else pygame.font.Font(None, int(h * 0.06)),
        'title': pygame.font.SysFont("segoeui, arial", int(h * 0.12), bold=True) if pygame.font.match_font("segoeui") else pygame.font.Font(None, int(h * 0.12)),
        'hud': pygame.font.SysFont("segoeui, arial", int(h * 0.03)) if pygame.font.match_font("segoeui") else pygame.font.Font(None, int(h * 0.03))
    }
    
    game = FlowGame(w, h, int(h * 0.08), fonts)
    game.load_database()
    
    state, clock, diff_page = "MENU", pygame.time.Clock(), 0
    diff_order = ["Easy", "Normal", "Hard", "Very Hard", "Impossible", "Irregular", "Bridges", "Torus"]
    
    cat_levels = {diff: [] for diff in diff_order}
    for idx, lvl in enumerate(game.levels):
        if lvl.get("difficulty", "Normal") in cat_levels:
            cat_levels[lvl.get("difficulty", "Normal")].append((idx, lvl))
        
    buttons = {} 

    running = True
    while running:
        dt, mouse_pos, click = clock.tick(60) / 1000.0, pygame.mouse.get_pos(), False

        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1: click = True
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if state == "PLAYING": state = "LEVEL_SELECT"
                elif state == "LEVEL_SELECT": state = "MENU"
                else: running = False
                
            if state == "PLAYING":
                if game.process_event(event) == "NEXT_LEVEL":
                    if not game.load_level(game.level_idx + 1): state = "LEVEL_SELECT"

        if state == "PLAYING": game.update(dt); game.draw(screen)
        elif state == "MENU":
            screen.fill(SCREEN_BG)
            title = fonts['title'].render("FLOW FREE", True, DISTINCT_COLORS[2]) 
            screen.blit(title, (w//2 - title.get_width()//2, h * 0.15))
            screen.blit(fonts['main'].render("Chaos Edition", True, (150, 150, 150)), (w//2 - fonts['main'].render("Chaos Edition", True, (150, 150, 150)).get_width()//2, h * 0.28))

            bx, bw, bh = w//2 - int(w * 0.25)//2, int(w * 0.25), int(h * 0.08)
            if 'play' not in buttons: buttons['play'] = Button("Play / Resume", bx, h * 0.40, bw, bh, BTN_DEFAULT, BTN_HOVER)
            if buttons['play'].draw(screen, fonts['main'], mouse_pos, dt) and click: game.load_level(game.level_idx); state = "PLAYING"
                
            if 'select' not in buttons: buttons['select'] = Button("Level Select", bx, h * 0.50, bw, bh, BTN_DEFAULT, BTN_HOVER)
            if buttons['select'].draw(screen, fonts['main'], mouse_pos, dt) and click: state = "LEVEL_SELECT"
            
            mod_y, mod_w, mod_gap = h * 0.65, int(w * 0.18), int(w * 0.02)
            mx = w // 2 - ((mod_w * 2) + mod_gap) // 2
            for i, mod in enumerate(["Fog", "Meltdown"]):
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
            
            title = fonts['title'].render(active_diff.upper(), True, DISTINCT_COLORS[diff_page % len(DISTINCT_COLORS)])
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
                cols, pad = min(6, len(lvls)), 15
                bsize = min(int(min((w*0.7 - (cols-1)*pad)//cols, (h*0.6 - 4*pad)//5)), 100)
                sx, sy = (w - (cols * bsize + (cols - 1) * pad)) // 2, int(h * 0.25)

                for li, (gidx, _) in enumerate(lvls):
                    r, c = li // cols, li % cols
                    bx, by = sx + c * (bsize + pad), sy + r * (bsize + pad)
                    bid = f"lvl_{gidx}"
                    if bid not in buttons: buttons[bid] = Button(str(li + 1), bx, by, bsize, bsize, BTN_DEFAULT, BTN_HOVER)
                    is_solved = gidx in game.solved_levels
                    buttons[bid].default_col = BTN_SOLVED if is_solved else BTN_DEFAULT
                    buttons[bid].hover_col = BTN_SOLVED_HOVER if is_solved else BTN_HOVER
                    buttons[bid].rect.x, buttons[bid].rect.y = bx, by 
                    if buttons[bid].draw(screen, fonts['main'], mouse_pos, dt) and click: game.load_level(gidx); state = "PLAYING"
        pygame.display.flip()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
