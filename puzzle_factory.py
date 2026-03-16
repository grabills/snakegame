import random
import json

def generate_base_snake(grid_size):
    """Creates a basic back-and-forth 100% full path."""
    path = []
    for r in range(grid_size):
        if r % 2 == 0:
            for c in range(grid_size): path.append((r, c))
        else:
            for c in range(grid_size - 1, -1, -1): path.append((r, c))
    return path

def backbite_randomize(path, grid_size, iterations):
    """
    THE BACKBITE ALGORITHM:
    Turns a neat snake into a violently interwoven, chaotic space-filling curve.
    """
    for _ in range(iterations):
        # 50% chance to flip the path so we bite from both ends randomly
        if random.random() < 0.5:
            path.reverse()
            
        tail = path[-1]
        r, c = tail
        
        # Find all physical grid neighbors of the tail
        neighbors = []
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < grid_size and 0 <= nc < grid_size:
                neighbors.append((nr, nc))
                
        neighbor = random.choice(neighbors)
        
        # If the neighbor is already the segment connected to the tail, do nothing
        if neighbor == path[-2]:
            continue
            
        # The backbite creates a loop. To fix it, we reverse the segment 
        # inside the loop, creating a brand new, highly complex path.
        idx = path.index(neighbor)
        path[idx+1:] = reversed(path[idx+1:])
        
    return path

def score_puzzle(paths, grid_size):
    """FITNESS FUNCTION: Scans for 'CrazyGames' style interlocking features."""
    grid = [[0]*grid_size for _ in range(grid_size)]
    for i, p in enumerate(paths):
        for r, c in p:
            grid[r][c] = i + 1
            
    score = 0
    
    for p in paths:
        # Ban trivially short paths
        if len(p) <= 2: return -9999 
        
        r1, c1 = p[0]
        r2, c2 = p[-1]
        dist = abs(r1 - r2) + abs(c1 - c2)
        
        # Endpoints strictly touching is mathematically trivial
        if dist <= 1: return -9999 
        
        # Reward Endpoints trapped in the center of the board
        score -= (abs(r1 - grid_size/2) + abs(c1 - grid_size/2))
        score -= (abs(r2 - grid_size/2) + abs(c2 - grid_size/2))

    for r in range(grid_size - 1):
        for c in range(grid_size - 1):
            cols = {grid[r][c], grid[r+1][c], grid[r][c+1], grid[r+1][c+1]}
            # Penalize 2x2 blobs of the same color (Snaking)
            if len(cols) == 1:
                score -= 100 
            # MASSIVE REWARD if 4 different colors meet at a single corner (High Density)
            elif len(cols) == 4:
                score += 100 

    # Reward highly winding paths (corners)
    for p in paths:
        for i in range(1, len(p) - 1):
            if p[i-1][0] != p[i+1][0] and p[i-1][1] != p[i+1][1]:
                score += 5

    return score

def mine_levels(grid_size, min_colors, max_colors, batch_size, keep_top_n):
    print(f"Mining {batch_size} candidate levels for size {grid_size}x{grid_size}...")
    candidates = []
    
    # The larger the board, the more bites it needs to fully scramble
    backbite_iterations = grid_size * grid_size * 25 
    
    for attempt in range(batch_size):
        num_colors = random.randint(min_colors, max_colors)
        
        # Generate and completely scramble the base path
        base_path = generate_base_snake(grid_size)
        chaotic_path = backbite_randomize(base_path, grid_size, backbite_iterations)
        
        total_cells = grid_size * grid_size
        valid_cut_indices = list(range(4, total_cells - 4))
        cut_points = []
        
        for _ in range(num_colors - 1):
            if not valid_cut_indices: break
            cut = random.choice(valid_cut_indices)
            cut_points.append(cut)
            # Ensure pieces don't get sliced too small
            valid_cut_indices = [x for x in valid_cut_indices if abs(x - cut) > 3]
            
        cut_points.sort()
        cut_points = [0] + cut_points + [total_cells]
        
        paths = []
        for i in range(len(cut_points) - 1):
            start, end = cut_points[i], cut_points[i+1]
            paths.append(chaotic_path[start:end])
            
        fitness_score = score_puzzle(paths, grid_size)
        
        # Store anything that passes the strict kill-switches
        if fitness_score > -5000:
            level_grid = [[0]*grid_size for _ in range(grid_size)]
            for i, p in enumerate(paths):
                col = i + 1
                level_grid[p[0][0]][p[0][1]] = col
                level_grid[p[-1][0]][p[-1][1]] = col
                
            candidates.append({"score": fitness_score, "grid": level_grid})
            
    # Sort and extract the absolute most tangled boards
    candidates.sort(key=lambda x: x["score"], reverse=True)
    elite_levels = candidates[:keep_top_n]
    
    print(f"Mined {len(elite_levels)} elite levels. Top Score: {elite_levels[0]['score'] if elite_levels else 0:.1f}")
    return elite_levels

def main():
    database = []
    
    # 15 highly dense 10x10 levels (10 to 13 colors)
    database.extend(mine_levels(grid_size=10, min_colors=10, max_colors=13, batch_size=4000, keep_top_n=15))
    
    # 15 absurdly dense 12x12 levels (13 to 16 colors)
    database.extend(mine_levels(grid_size=12, min_colors=13, max_colors=16, batch_size=4000, keep_top_n=15))

    final_output = [level["grid"] for level in database]
    
    with open("puzzles.json", "w") as f:
        json.dump(final_output, f)
        
    print(f"Saved {len(final_output)} extremely intertwined levels to puzzles.json")

if __name__ == "__main__":
    main()
