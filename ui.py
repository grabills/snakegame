import pygame
import math

class Button:
    def __init__(self, text, x, y, w, h, default_col, hover_col):
        self.rect = pygame.Rect(x, y, w, h)
        self.text = text
        self.default_col = default_col
        self.hover_col = hover_col
        self.hover_state = 0.0

    def draw(self, screen, font, mouse_pos, dt):
        is_hover = self.rect.collidepoint(mouse_pos)
        target_state = 1.0 if is_hover else 0.0
        
        self.hover_state += (target_state - self.hover_state) * min(1.0, 15 * dt)
        current_color = self.default_col.lerp(self.hover_col, self.hover_state)
        
        shadow_rect = pygame.Rect(self.rect.x, self.rect.y + 4, self.rect.w, self.rect.h)
        pygame.draw.rect(screen, (10, 10, 12), shadow_rect, border_radius=12)
        pygame.draw.rect(screen, current_color, self.rect, border_radius=12)
        
        text_surf = font.render(self.text, True, (240, 240, 240))
        text_x = self.rect.x + (self.rect.w - text_surf.get_width()) // 2
        text_y = self.rect.y + (self.rect.h - text_surf.get_height()) // 2
        screen.blit(text_surf, (text_x, text_y))
        
        return is_hover

def draw_star(surface, x, y, size, color):
    """Mathematically draws a perfect 5-point vector star."""
    points = []
    for i in range(10):
        angle = i * math.pi / 5 - math.pi / 2
        radius = size if i % 2 == 0 else size * 0.4
        points.append((x + math.cos(angle) * radius, y + math.sin(angle) * radius))
    pygame.draw.polygon(surface, color, points)
