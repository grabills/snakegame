import random
import json

def get_mask(grid_size, shape_type):
    """Creates a base layout. 0 = Normal, -1 = Hole, -2 = Bridge."""
    mask = [[0]*grid_size for _ in range(grid_size)]
    
    if shape_type == "Donut":
        r1 = grid_size // 2 - 1
        for r in range(r1, r1 + 2):
            for c in range(r1, r1 + 2):
                mask[r][c] = -1
                
    elif shape_type == "Cross":
        k = grid_size // 3
        for r in range(grid_size):
            for c in range(grid_size):
                if (r < k or r >= grid_size - k) and (c < k or c >= grid_size - k):
                    mask[r][c] = -1
                    
    elif shape_type == "Bridges":
        mask[grid_size // 2][grid_size // 2] = -2
        if grid_size >= 8:
            mask[grid_size // 4][grid_size // 4] = -2
            mask[grid_size - grid_size // 4 - 1][grid_size - grid_size // 4 - 1] = -2
            
    return mask

def build_graph(mask, grid_size):
    """Converts the 2D grid into a mathematical graph to support overlapping bridges."""
    nodes = []
    adj = {}
    
    for r in range(grid_size):
        for c in range(grid_size):
            if mask[r][c] == -1: continue 
            if mask[r][c] == -2:
                # Bridges act as two separate overlapping nodes
                nodes.extend([(r, c, 'h'), (r, c, 'v')])
                adj[(r, c, 'h')] = []
                adj[(r, c, 'v')] = []
            else:
                nodes.append((r, c, 'n'))
                adj[(r, c, 'n')] = []

    for node in nodes:
        r, c, t = node
        if t == 'n':
            for dr, dc, req_t in [(-1,0,'v'), (1,0,'v'), (0,-1,'h'), (0,1,'h')]:
                nr, nc = r+dr, c+dc
                if 0 <= nr < grid_size and 0 <= nc < grid_size and mask[nr][nc] != -1:
                    adj[node].append((nr, nc, req_t) if mask[nr][nc] == -2 else (nr, nc, 'n'))
        elif t == 'h': # Horizontal bridge node only connects left/right
            for dr, dc in [(0,-1), (0,1)]:
                nr, nc = r+dr, c+dc
                if 0 <= nr < grid_size and 0 <= nc < grid_size and mask[nr][nc] != -1:
                    adj[node].append((nr, nc, 'h') if mask[nr][nc] == -2 else (nr, nc, 'n'))
        elif t == 'v': # Vertical bridge node only connects up/down
            for dr, dc in [(-1,0), (1,0)]:
                nr, nc = r+dr, c+dc
                if 0 <= nr < grid_size and 0 <= nc < grid_size and mask[nr][nc] != -1:
                    adj[node].append((nr, nc, 'v') if mask[nr][nc] == -2 else (nr, nc, 'n'))
                    
    return nodes, adj

def get_initial_path(nodes, adj):
    """Uses Warnsdorff's Iterative DFS to find a path through complex shapes."""
    for _ in range(50): 
        start = random.choice(nodes)
        visited = set([start])
        path = [start]
        stack = [(start, 0, [n for n in adj[start]])]
        
        steps = 0
        while stack and steps < 50000:
            steps += 1
            if len(path) == len(nodes): return path
            curr, idx, nbrs = stack.pop()
            
            if idx < len(nbrs):
                nxt = nbrs[idx]
                stack.append((curr, idx + 1, nbrs)) 
                if nxt not in visited:
                    visited.add(nxt)
                    path.append(nxt)
                    next_nbrs = [n for n in adj[nxt] if n not in visited]
                    # Heuristic: Prioritize nodes with the fewest onward moves to prevent getting trapped
                    next_nbrs.sort(key=lambda n: sum(1 for nn in adj[n] if nn not in visited))
                    stack.append((nxt, 0, next_nbrs))
            else:
                visited.remove(curr)
                path.pop()
    return None

def backbite_graph(path, adj, iterations):
    """Generalized backbite that works on bridges and holes."""
    for _ in range(iterations):
        if random.random() < 0.5: path.reverse()
        tail = path[-1]
        nbrs = adj[tail]
        if not nbrs: continue
        nxt = random.choice(nbrs)
        if nxt == path[-2]: continue
        idx = path.index(nxt)
        path[idx+1:] = reversed(path[idx+1:])
    return path

def score_puzzle(paths, grid_size, difficulty, mask):
    color_grid = [[0]*grid_size for _ in range(grid_size)]
    for i, p in enumerate(paths):
        for r, c, t in p:
            if t != 'n': color_grid[r][c] = 99 # Ignore bridges for snaking calculations
            else: color_grid[r][c] = i + 1
            
    score = 0
    for p in paths:
        if difficulty != "Easy" and len(p) <= 3: return -9999 
        elif len(p) <= 1: return -9999
        
        r1, c1 = p[0][0], p[0][1]
        r2, c2 = p[-1][0], p[-1][1]
        if abs(r1 - r2) + abs(c1 - c2) <= 1: return -9999 
        
        if difficulty in ["Hard", "Very Hard", "Impossible", "Bridges", "Irregular"]:
            score -= (abs(r1 - grid_size/2) + abs(c1 - grid_size/2)) * 5
            score -= (abs(r2 - grid_size/2) + abs(c2 - grid_size/2)) * 5
        elif difficulty == "Easy":
            score += (abs(r1 - grid_size/2) + abs(c1 - grid_size/2)) * 2

    for r in range(grid_size - 1):
        for c in range(grid_size - 1):
            if mask[r][c] == -1 or mask[r+1][c] == -1 or mask[r][c+1] == -1 or mask[r+1][c+1] == -1: continue
            cols = {color_grid[r][c], color_grid[r+1][c], color_grid[r][c+1], color_grid[r+1][c+1]}
            if 99 in cols: continue 
            if len(cols) == 1: score -= 150 if difficulty in ["Very Hard", "Impossible"] else 50
            elif len(cols) == 4: score += 150 if difficulty in ["Hard", "Very Hard", "Impossible"] else 20

    for p in paths:
        for i in range(1, len(p) - 1):
            if p[i-1][0] != p[i+1][0] and p[i-1][1] != p[i+1][1]:
                score += 10 if difficulty != "Easy" else 2

    return score

def mine_levels(difficulty, grid_size, min_colors, max_colors, shape, batch_size, keep_top_n):
    print(f"Mining {batch_size} [{difficulty}] levels ({grid_size}x{grid_size} {shape})...")
    candidates = []
    
    mask = get_mask(grid_size, shape)
    nodes, adj = build_graph(mask, grid_size)
    
    multiplier = {"Easy": 5, "Normal": 15, "Hard": 25, "Very Hard": 35, "Impossible": 50, "Irregular": 35, "Bridges": 40}
    backbite_iterations = len(nodes) * multiplier[difficulty]
    
    for attempt in range(batch_size):
        num_colors = random.randint(min_colors, max_colors)
        
        base_path = get_initial_path(nodes, adj)
        if not base_path: continue
        
        chaotic_path = backbite_graph(base_path, adj, backbite_iterations)
        
        valid_cuts = []
        for i in range(3, len(chaotic_path) - 3):
            # Enforce that endpoints NEVER land on a bridge
            if chaotic_path[i][2] == 'n' and chaotic_path[i-1][2] == 'n':
                valid_cuts.append(i)
                
        if len(valid_cuts) < num_colors - 1: continue

        cuts = []
        for _ in range(num_colors - 1):
            if not valid_cuts: break
            c = random.choice(valid_cuts)
            cuts.append(c)
            spacing = 3 if difficulty == "Easy" else 4
            valid_cuts = [x for x in valid_cuts if abs(x - c) > spacing]
            
        if len(cuts) < num_colors - 1: continue
            
        cuts.sort()
        cuts = [0] + cuts + [len(chaotic_path)]
        
        paths = []
        for i in range(len(cuts) - 1):
            paths.append(chaotic_path[cuts[i]:cuts[i+1]])
            
        fitness_score = score_puzzle(paths, grid_size, difficulty, mask)
        
        if fitness_score > -5000:
            level_grid = [row[:] for row in mask] 
            for i, p in enumerate(paths):
                col = i + 1
                level_grid[p[0][0]][p[0][1]] = col
                level_grid[p[-1][0]][p[-1][1]] = col
                
            candidates.append({"score": fitness_score, "difficulty": difficulty, "grid": level_grid})
            
    candidates.sort(key=lambda x: x["score"], reverse=True)
    elite_levels = candidates[:keep_top_n]
    print(f" -> Mined {len(elite_levels)} levels. Top Score: {elite_levels[0]['score'] if elite_levels else 0:.1f}")
    return elite_levels

def main():
    database = []
    
    # (Difficulty, Grid Size, Min Colors, Max Colors, Shape, Batch Size, Keep)
    configs = [
        ("Easy", 6, 4, 5, "Square", 500, 8),
        ("Normal", 8, 6, 8, "Square", 1000, 8),
        ("Hard", 10, 8, 10, "Square", 2000, 8),
        ("Very Hard", 12, 10, 12, "Square", 2000, 8),
        ("Impossible", 14, 13, 15, "Square", 3000, 8),
        ("Irregular", 10, 8, 11, "Donut", 2000, 4),
        ("Irregular", 9, 7, 9, "Cross", 2000, 4),
        ("Bridges", 10, 8, 11, "Bridges", 3000, 8)
    ]
    
    for conf in configs:
        database.extend(mine_levels(*conf))
    
    with open("puzzles.json", "w") as f:
        json.dump(database, f, indent=2)
        
    print(f"\nSaved a total of {len(database)} curated levels to puzzles.json")

if __name__ == "__main__":
    main()
