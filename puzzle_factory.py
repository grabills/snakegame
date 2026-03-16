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
    """Turns a neat snake into a chaotic space-filling curve."""
    for _ in range(iterations):
        if random.random() < 0.5:
            path.reverse()
            
        tail = path[-1]
        r, c = tail
        
        neighbors = []
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < grid_size and 0 <= nc < grid_size:
                neighbors.append((nr, nc))
                
        neighbor = random.choice(neighbors)
        
        if neighbor == path[-2]:
            continue
            
        idx = path.index(neighbor)
        path[idx+1:] = reversed(path[idx+1:])
        
    return path

def score_puzzle(paths, grid_size, difficulty):
    """FITNESS FUNCTION: Dynamically scales based on desired difficulty."""
    grid = [[0]*grid_size for _ in range(grid_size)]
    for i, p in enumerate(paths):
        for r, c in p:
            grid[r][c] = i + 1
            
    score = 0
    
    for p in paths:
        # Ban trivially short paths for anything above Easy
        if difficulty != "Easy" and len(p) <= 3: return -9999 
        elif len(p) <= 1: return -9999
        
        r1, c1 = p[0]
        r2, c2 = p[-1]
        dist = abs(r1 - r2) + abs(c1 - c2)
        
        # Endpoints strictly touching is mathematically trivial
        if dist <= 1: return -9999 
        
        # Endpoint burial: Harder difficulties reward endpoints trapped in the center
        if difficulty in ["Hard", "Very Hard", "Impossible"]:
            score -= (abs(r1 - grid_size/2) + abs(c1 - grid_size/2)) * 5
            score -= (abs(r2 - grid_size/2) + abs(c2 - grid_size/2)) * 5
        elif difficulty == "Easy":
            # Easy levels actually prefer endpoints near the edges
            score += (abs(r1 - grid_size/2) + abs(c1 - grid_size/2)) * 2

    # Analyze topology
    for r in range(grid_size - 1):
        for c in range(grid_size - 1):
            cols = {grid[r][c], grid[r+1][c], grid[r][c+1], grid[r+1][c+1]}
            
            # Penalize 2x2 blobs of the same color (Snaking)
            if len(cols) == 1:
                score -= 150 if difficulty in ["Very Hard", "Impossible"] else 50
                
            # MASSIVE REWARD if 4 different colors meet at a single corner (High Density)
            elif len(cols) == 4:
                score += 150 if difficulty in ["Hard", "Very Hard", "Impossible"] else 20

    # Reward highly winding paths (corners)
    for p in paths:
        for i in range(1, len(p) - 1):
            if p[i-1][0] != p[i+1][0] and p[i-1][1] != p[i+1][1]:
                score += 10 if difficulty != "Easy" else 2

    return score

def mine_levels(difficulty, grid_size, min_colors, max_colors, batch_size, keep_top_n):
    print(f"Mining {batch_size} [{difficulty}] levels ({grid_size}x{grid_size})...")
    candidates = []
    
    # Scale backbites by difficulty. Easy needs fewer scrambles.
    multiplier = {"Easy": 5, "Normal": 15, "Hard": 25, "Very Hard": 35, "Impossible": 50}
    backbite_iterations = grid_size * grid_size * multiplier[difficulty]
    
    for attempt in range(batch_size):
        num_colors = random.randint(min_colors, max_colors)
        
        base_path = generate_base_snake(grid_size)
        chaotic_path = backbite_randomize(base_path, grid_size, backbite_iterations)
        
        total_cells = grid_size * grid_size
        valid_cut_indices = list(range(4, total_cells - 4))
        cut_points = []
        
        for _ in range(num_colors - 1):
            if not valid_cut_indices: break
            cut = random.choice(valid_cut_indices)
            cut_points.append(cut)
            # Cut spacing defines path lengths
            spacing = 3 if difficulty == "Easy" else 4
            valid_cut_indices = [x for x in valid_cut_indices if abs(x - cut) > spacing]
            
        cut_points.sort()
        cut_points = [0] + cut_points + [total_cells]
        
        paths = []
        for i in range(len(cut_points) - 1):
            start, end = cut_points[i], cut_points[i+1]
            paths.append(chaotic_path[start:end])
            
        fitness_score = score_puzzle(paths, grid_size, difficulty)
        
        if fitness_score > -5000:
            level_grid = [[0]*grid_size for _ in range(grid_size)]
            for i, p in enumerate(paths):
                col = i + 1
                level_grid[p[0][0]][p[0][1]] = col
                level_grid[p[-1][0]][p[-1][1]] = col
                
            candidates.append({
                "score": fitness_score, 
                "difficulty": difficulty, 
                "grid": level_grid
            })
            
    candidates.sort(key=lambda x: x["score"], reverse=True)
    elite_levels = candidates[:keep_top_n]
    
    print(f" -> Mined {len(elite_levels)} {difficulty} levels. Top Score: {elite_levels[0]['score'] if elite_levels else 0:.1f}")
    return elite_levels

def main():
    database = []
    
    # Mining Configuration: (Difficulty, Grid Size, Min Colors, Max Colors, Batch Size, Keep)
    configs = [
        ("Easy", 6, 4, 5, 1000, 10),
        ("Normal", 8, 6, 8, 2000, 10),
        ("Hard", 10, 9, 11, 3000, 10),
        ("Very Hard", 12, 12, 14, 4000, 10),
        ("Impossible", 14, 15, 15, 5000, 10) # 14x14 grid with max colors
    ]
    
    for conf in configs:
        database.extend(mine_levels(*conf))
    
    with open("puzzles.json", "w") as f:
        json.dump(database, f, indent=2) # Indent makes it readable if you want to inspect it
        
    print(f"\nSaved a total of {len(database)} curated levels to puzzles.json")

if __name__ == "__main__":
    main()
