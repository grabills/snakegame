#include <iostream>
#include <vector>
#include <string>
#include <random>
#include <algorithm>
#include <fstream>
#include <thread>
#include <mutex>
#include <future>
#include <map>

using namespace std;

// System Constants
const int HOLE = -1;
const int BRIDGE = -2;

struct Node {
    int r, c;
    char t; // 'n'=normal, 'h'=horizontal, 'v'=vertical
    bool operator==(const Node& o) const { return r == o.r && c == o.c && t == o.t; }
    bool operator<(const Node& o) const {
        if (r != o.r) return r < o.r;
        if (c != o.c) return c < o.c;
        return t < o.t;
    }
};

struct LevelCandidate {
    int score;
    string difficulty;
    vector<vector<int>> grid;
};

// Thread-safe Random Number Generator
thread_local mt19937 rng(random_device{}());

vector<vector<int>> get_mask(int grid_size, const string& shape_type) {
    vector<vector<int>> mask(grid_size, vector<int>(grid_size, 0));
    if (shape_type == "Donut") {
        int r1 = grid_size / 2 - 1;
        for (int r = r1; r < r1 + 2; ++r)
            for (int c = r1; c < r1 + 2; ++c)
                mask[r][c] = HOLE;
    } else if (shape_type == "Cross") {
        int k = grid_size / 3;
        for (int r = 0; r < grid_size; ++r)
            for (int c = 0; c < grid_size; ++c)
                if ((r < k || r >= grid_size - k) && (c < k || c >= grid_size - k))
                    mask[r][c] = HOLE;
    } else if (shape_type == "Bridges") {
        mask[grid_size / 2][grid_size / 2] = BRIDGE;
        if (grid_size >= 8) {
            mask[grid_size / 4][grid_size / 4] = BRIDGE;
            mask[grid_size - grid_size / 4 - 1][grid_size - grid_size / 4 - 1] = BRIDGE;
        }
    }
    return mask;
}

void build_graph(const vector<vector<int>>& mask, int grid_size, vector<Node>& nodes, map<Node, vector<Node>>& adj) {
    for (int r = 0; r < grid_size; ++r) {
        for (int c = 0; c < grid_size; ++c) {
            if (mask[r][c] == HOLE) continue;
            if (mask[r][c] == BRIDGE) {
                nodes.push_back({r, c, 'h'});
                nodes.push_back({r, c, 'v'});
                adj[{r, c, 'h'}] = {};
                adj[{r, c, 'v'}] = {};
            } else {
                nodes.push_back({r, c, 'n'});
                adj[{r, c, 'n'}] = {};
            }
        }
    }

    int dirs[4][3] = {{-1, 0, 'v'}, {1, 0, 'v'}, {0, -1, 'h'}, {0, 1, 'h'}};
    for (const auto& node : nodes) {
        int r = node.r, c = node.c; char t = node.t;
        if (t == 'n') {
            for (auto& d : dirs) {
                int nr = r + d[0], nc = c + d[1]; char req_t = d[2];
                if (nr >= 0 && nr < grid_size && nc >= 0 && nc < grid_size && mask[nr][nc] != HOLE) {
                    adj[node].push_back({nr, nc, mask[nr][nc] == BRIDGE ? req_t : 'n'});
                }
            }
        } else if (t == 'h') {
            int hdirs[2][2] = {{0, -1}, {0, 1}};
            for (auto& d : hdirs) {
                int nr = r + d[0], nc = c + d[1];
                if (nr >= 0 && nr < grid_size && nc >= 0 && nc < grid_size && mask[nr][nc] != HOLE)
                    adj[node].push_back({nr, nc, mask[nr][nc] == BRIDGE ? 'h' : 'n'});
            }
        } else if (t == 'v') {
            int vdirs[2][2] = {{-1, 0}, {1, 0}};
            for (auto& d : vdirs) {
                int nr = r + d[0], nc = c + d[1];
                if (nr >= 0 && nr < grid_size && nc >= 0 && nc < grid_size && mask[nr][nc] != HOLE)
                    adj[node].push_back({nr, nc, mask[nr][nc] == BRIDGE ? 'v' : 'n'});
            }
        }
    }
}

vector<Node> get_initial_path(const vector<Node>& nodes, map<Node, vector<Node>>& adj) {
    for (int attempt = 0; attempt < 50; ++attempt) {
        uniform_int_distribution<int> dist(0, nodes.size() - 1);
        Node start = nodes[dist(rng)];
        
        vector<Node> path;
        vector<bool> visited(nodes.size(), false);
        map<Node, int> node_to_idx;
        for(size_t i=0; i<nodes.size(); ++i) node_to_idx[nodes[i]] = i;
        
        struct StackFrame { Node curr; int idx; vector<Node> nbrs; };
        vector<StackFrame> stack;
        
        path.push_back(start);
        visited[node_to_idx[start]] = true;
        stack.push_back({start, 0, adj[start]});
        
        int steps = 0;
        while (!stack.empty() && steps < 50000) {
            steps++;
            if (path.size() == nodes.size()) return path;
            
            auto& frame = stack.back();
            if (frame.idx < frame.nbrs.size()) {
                Node nxt = frame.nbrs[frame.idx++];
                int nxt_idx = node_to_idx[nxt];
                
                if (!visited[nxt_idx]) {
                    visited[nxt_idx] = true;
                    path.push_back(nxt);
                    
                    vector<Node> next_nbrs;
                    for (auto& n : adj[nxt]) if (!visited[node_to_idx[n]]) next_nbrs.push_back(n);
                    
                    // Warnsdorff's Heuristic Sort
                    sort(next_nbrs.begin(), next_nbrs.end(), [&](const Node& a, const Node& b) {
                        int c_a = 0, c_b = 0;
                        for(auto& n : adj[a]) if(!visited[node_to_idx[n]]) c_a++;
                        for(auto& n : adj[b]) if(!visited[node_to_idx[n]]) c_b++;
                        return c_a < c_b;
                    });
                    
                    stack.push_back({nxt, 0, next_nbrs});
                }
            } else {
                visited[node_to_idx[frame.curr]] = false;
                path.pop_back();
                stack.pop_back();
            }
        }
    }
    return {};
}

void backbite_graph(vector<Node>& path, map<Node, vector<Node>>& adj, int iterations) {
    uniform_real_distribution<float> prob(0.0, 1.0);
    for (int i = 0; i < iterations; ++i) {
        if (prob(rng) < 0.5) reverse(path.begin(), path.end());
        Node tail = path.back();
        auto& nbrs = adj[tail];
        if (nbrs.empty()) continue;
        
        uniform_int_distribution<int> dist(0, nbrs.size() - 1);
        Node nxt = nbrs[dist(rng)];
        if (path.size() > 1 && nxt == path[path.size() - 2]) continue;
        
        auto it = find(path.begin(), path.end(), nxt);
        if (it != path.end()) {
            reverse(it + 1, path.end());
        }
    }
}

int score_puzzle(const vector<vector<Node>>& paths, int grid_size, const string& difficulty, const vector<vector<int>>& mask) {
    vector<vector<int>> color_grid(grid_size, vector<int>(grid_size, 0));
    for (size_t i = 0; i < paths.size(); ++i) {
        for (const auto& n : paths[i]) {
            if (n.t != 'n') color_grid[n.r][n.c] = 99; 
            else color_grid[n.r][n.c] = i + 1;
        }
    }

    int score = 0;
    for (const auto& p : paths) {
        if (difficulty != "Easy" && p.size() <= 3) return -9999;
        if (p.size() <= 1) return -9999;

        int r1 = p.front().r, c1 = p.front().c;
        int r2 = p.back().r, c2 = p.back().c;
        if (abs(r1 - r2) + abs(c1 - c2) <= 1) return -9999;

        float mid = grid_size / 2.0;
        if (difficulty == "Easy") {
            score += (abs(r1 - mid) + abs(c1 - mid)) * 2;
        } else {
            score -= (abs(r1 - mid) + abs(c1 - mid)) * 5;
            score -= (abs(r2 - mid) + abs(c2 - mid)) * 5;
        }
    }

    for (int r = 0; r < grid_size - 1; ++r) {
        for (int c = 0; c < grid_size - 1; ++c) {
            if (mask[r][c] == HOLE || mask[r+1][c] == HOLE || mask[r][c+1] == HOLE || mask[r+1][c+1] == HOLE) continue;
            
            int cols[4] = {color_grid[r][c], color_grid[r+1][c], color_grid[r][c+1], color_grid[r+1][c+1]};
            bool has_bridge = false;
            vector<int> unique_cols;
            for(int v : cols) {
                if(v == 99) has_bridge = true;
                if(find(unique_cols.begin(), unique_cols.end(), v) == unique_cols.end()) unique_cols.push_back(v);
            }
            if (has_bridge) continue;
            
            if (unique_cols.size() == 1) score -= (difficulty == "Very Hard" || difficulty == "Impossible") ? 150 : 50;
            else if (unique_cols.size() == 4) score += (difficulty == "Hard" || difficulty == "Very Hard" || difficulty == "Impossible") ? 150 : 20;
        }
    }

    for (const auto& p : paths) {
        for (size_t i = 1; i < p.size() - 1; ++i) {
            if (p[i-1].r != p[i+1].r && p[i-1].c != p[i+1].c) {
                score += (difficulty != "Easy") ? 10 : 2;
            }
        }
    }
    return score;
}

vector<LevelCandidate> mine_levels(string difficulty, int grid_size, int min_colors, int max_colors, string shape, int batch_size, int keep_top_n) {
    cout << "Mining " << batch_size << " [" << difficulty << "] levels (" << grid_size << "x" << grid_size << " " << shape << ")..." << flush;
    
    auto mask = get_mask(grid_size, shape);
    vector<Node> nodes;
    map<Node, vector<Node>> adj;
    build_graph(mask, grid_size, nodes, adj);
    
    map<string, int> mult = {{"Easy", 5}, {"Normal", 15}, {"Hard", 25}, {"Very Hard", 35}, {"Impossible", 50}, {"Irregular", 35}, {"Bridges", 40}};
    int backbite_iterations = nodes.size() * mult[difficulty];

    vector<LevelCandidate> candidates;
    mutex cand_mutex;

    int num_threads = thread::hardware_concurrency();
    vector<future<void>> futures;
    int chunk_size = batch_size / num_threads;

    for (int t = 0; t < num_threads; ++t) {
        futures.push_back(async(launch::async, [&, t]() {
            int local_batch = (t == num_threads - 1) ? (batch_size - t * chunk_size) : chunk_size;
            vector<LevelCandidate> local_candidates;

            for (int attempt = 0; attempt < local_batch; ++attempt) {
                uniform_int_distribution<int> c_dist(min_colors, max_colors);
                int num_colors = c_dist(rng);
                
                auto chaotic_path = get_initial_path(nodes, adj);
                if (chaotic_path.empty()) continue;
                
                backbite_graph(chaotic_path, adj, backbite_iterations);
                
                vector<int> valid_cuts;
                for (size_t i = 3; i < chaotic_path.size() - 3; ++i) {
                    if (chaotic_path[i].t == 'n' && chaotic_path[i-1].t == 'n') valid_cuts.push_back(i);
                }
                if (valid_cuts.size() < num_colors - 1) continue;

                vector<int> cuts;
                for (int c = 0; c < num_colors - 1; ++c) {
                    if (valid_cuts.empty()) break;
                    uniform_int_distribution<int> v_dist(0, valid_cuts.size() - 1);
                    int cut = valid_cuts[v_dist(rng)];
                    cuts.push_back(cut);
                    
                    int spacing = (difficulty == "Easy") ? 3 : 4;
                    vector<int> next_valid;
                    for (int x : valid_cuts) if (abs(x - cut) > spacing) next_valid.push_back(x);
                    valid_cuts = next_valid;
                }
                
                if (cuts.size() < num_colors - 1) continue;
                
                sort(cuts.begin(), cuts.end());
                cuts.insert(cuts.begin(), 0);
                cuts.push_back(chaotic_path.size());
                
                vector<vector<Node>> paths;
                for (size_t i = 0; i < cuts.size() - 1; ++i) {
                    paths.push_back(vector<Node>(chaotic_path.begin() + cuts[i], chaotic_path.begin() + cuts[i+1]));
                }
                
                int score = score_puzzle(paths, grid_size, difficulty, mask);
                
                if (score > -5000) {
                    vector<vector<int>> level_grid = mask;
                    for (size_t i = 0; i < paths.size(); ++i) {
                        int col = i + 1;
                        level_grid[paths[i].front().r][paths[i].front().c] = col;
                        level_grid[paths[i].back().r][paths[i].back().c] = col;
                    }
                    local_candidates.push_back({score, difficulty, level_grid});
                }
            }
            
            lock_guard<mutex> lock(cand_mutex);
            candidates.insert(candidates.end(), local_candidates.begin(), local_candidates.end());
        }));
    }

    for (auto& f : futures) f.wait();

    sort(candidates.begin(), candidates.end(), [](const LevelCandidate& a, const LevelCandidate& b) {
        return a.score > b.score;
    });

    if (candidates.size() > keep_top_n) candidates.resize(keep_top_n);
    
    cout << " -> Mined " << candidates.size() << " levels. Top Score: " << (candidates.empty() ? 0 : candidates.front().score) << endl;
    return candidates;
}

int main() {
    vector<LevelCandidate> database;
    
    // Helper lambda to cleanly extract and append the vectors
    auto append_levels = [&](const string& diff, int size, int min_c, int max_c, const string& shape, int batch, int keep) {
        auto results = mine_levels(diff, size, min_c, max_c, shape, batch, keep);
        database.insert(database.end(), results.begin(), results.end());
    };
    
    append_levels("Easy", 6, 4, 5, "Square", 500, 8);
    append_levels("Normal", 8, 6, 8, "Square", 1000, 8);
    append_levels("Hard", 10, 8, 10, "Square", 2000, 8);
    append_levels("Very Hard", 12, 10, 12, "Square", 2000, 8);
    append_levels("Impossible", 14, 13, 15, "Square", 3000, 8);
    append_levels("Irregular", 10, 8, 11, "Donut", 2000, 4);
    append_levels("Irregular", 9, 7, 9, "Cross", 2000, 4);
    append_levels("Bridges", 10, 8, 11, "Bridges", 3000, 8);

    // Manual JSON string building to avoid external dependencies
    ofstream out("puzzles.json");
    out << "[\n";
    for (size_t i = 0; i < database.size(); ++i) {
        out << "  {\n";
        out << "    \"score\": " << database[i].score << ",\n";
        out << "    \"difficulty\": \"" << database[i].difficulty << "\",\n";
        out << "    \"grid\": [\n";
        for (size_t r = 0; r < database[i].grid.size(); ++r) {
            out << "      [";
            for (size_t c = 0; c < database[i].grid[r].size(); ++c) {
                out << database[i].grid[r][c] << (c < database[i].grid[r].size() - 1 ? ", " : "");
            }
            out << "]" << (r < database[i].grid.size() - 1 ? ",\n" : "\n");
        }
        out << "    ]\n";
        out << "  }" << (i < database.size() - 1 ? ",\n" : "\n");
    }
    out << "]\n";
    out.close();

    cout << "\nSaved a total of " << database.size() << " curated levels to puzzles.json" << endl;
    return 0;
}
