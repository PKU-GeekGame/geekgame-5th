#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include "game.h"

Player* player;
MonsterType monster_types[MONSTER_TYPE_COUNT];
bool wall[MAP_HEIGHT][MAP_WIDTH];
Monster *monster_map[MAP_HEIGHT][MAP_WIDTH];
int player_x, player_y;
Monster *boss_monster;
int hide_x = 0;
int hide_y = 0;
bool in_battle = false;
bool debug_mode = false;
bool rename_ability = false;
bool game_over = false;
bool hide_flag = false;

// Internal helper prototypes
static void carve_maze_dfs(int cx, int cy,int step);
static void add_monster(int x, int y, int type);

void init_game() {
    player = malloc(sizeof(Player));
    // Initialize player stats
    memcpy(player->name, "Hero", sizeof(player->name));
    player->emoji = L"🧙";  // Hero's avatar (wizard emoji)
    // player->emoji = L"#";  // Hero's avatar (wizard emoji)
    player->level = 1;
    player->maxHP = 100;
    player->currentHP = 100;
    player->atk = 10;
    player->def = 10;
    player->xp = 0;
    player->xp_to_next = 50 + player->level * 5;  // XP needed for next level
    player->potions = 10;
    player->pet_count = 0;
    for(int i = 0; i < MAX_PETS; ++i) {
        player->pets[i].type = -1;    // mark empty slot
        player->pets[i].currentHP = 0;
        player->pets[i].battle_pos = 0;
    }
    // Initialize monster type list (name, emoji, HP, ATK, DEF, XP)
    monster_types[MONSTER_SLIME]   = (MonsterType){ "Slime",    L"👾",  30,  5,  0,  5 };
    monster_types[MONSTER_GOBLIN]  = (MonsterType){ "Goblin",   L"👺",  50,  10,  2,  8 };
    monster_types[MONSTER_SKELETON]= (MonsterType){ "Skeleton", L"💀",  60, 12,  4, 10 };
    monster_types[MONSTER_ZOMBIE]  = (MonsterType){ "Zombie",   L"🧟",  80, 16,  5, 12 };
    monster_types[MONSTER_GHOST]   = (MonsterType){ "Ghost",    L"👻",  70, 20,  3, 15 };
    monster_types[MONSTER_ORC]     = (MonsterType){ "Orc",      L"👹", 120, 18,  8, 18 };
    monster_types[MONSTER_VAMPIRE] = (MonsterType){ "Vampire",  L"🧛", 100, 24, 10, 20 };
    monster_types[MONSTER_DEMON]   = (MonsterType){ "Demon",    L"👿", 150, 30, 15, 30 };
    monster_types[MONSTER_HYDRA]   = (MonsterType){ "Hydra",    L"🦖", 300, 40, 20, 50 };
    monster_types[MONSTER_BOSS]    = (MonsterType){ "Evil Dragon", L"🐉", 1000, 80, 30, 0 };
    monster_types[MONSTER_NAMELESS_BOSS] = (MonsterType){ "???", L"❓", 1000, 20, 20, 10000 }; // Hidden placeholder

    // monster_types[MONSTER_SLIME]   = (MonsterType){ "Slime",    L"@",  30,  5,  0,  5 };
    // monster_types[MONSTER_GOBLIN]  = (MonsterType){ "Goblin",   L"@",  50,  10,  2,  8 };
    // monster_types[MONSTER_SKELETON]= (MonsterType){ "Skeleton", L"@",  60, 12,  4, 10 };
    // monster_types[MONSTER_ZOMBIE]  = (MonsterType){ "Zombie",   L"@",  80, 16,  5, 12 };
    // monster_types[MONSTER_GHOST]   = (MonsterType){ "Ghost",    L"@",  70, 20,  3, 15 };
    // monster_types[MONSTER_ORC]     = (MonsterType){ "Orc",      L"@", 120, 18,  8, 18 };
    // monster_types[MONSTER_VAMPIRE] = (MonsterType){ "Vampire",  L"@", 100, 24, 10, 20 };
    // monster_types[MONSTER_DEMON]   = (MonsterType){ "Demon",    L"@", 150, 30, 15, 30 };
    // monster_types[MONSTER_HYDRA]   = (MonsterType){ "Hydra",    L"@", 300, 40, 20, 50 };
    // monster_types[MONSTER_BOSS]    = (MonsterType){ "Evil Dragon", L"!", 1000, 80, 30, 0 };
    // monster_types[MONSTER_NAMELESS_BOSS] = (MonsterType){ "???", L"?", 1000, 20, 20, 10000 }; // Hidden placeholder
    // Seed random for maze and monsters
    srand(time(NULL));
    // Generate maze and populate monsters
    generate_maze();
    place_monsters();
    // Set player starting position (top-left of maze)
    player_x = 0;
    player_y = 0;
    game_over = false;
}

void generate_maze() {
    // Initialize all cells as walls
    for(int i = 0; i < MAP_HEIGHT; ++i) {
        for(int j = 0; j < MAP_WIDTH; ++j) {
            wall[i][j] = true;
            monster_map[i][j] = NULL;
        }
    }
    // Carve out maze paths using DFS from (0,0)
    wall[0][0] = false;
    carve_maze_dfs(0, 0, 0);
    // Ensure start and boss locations are open
    wall[0][0] = false;
    wall[MAP_HEIGHT-1][MAP_WIDTH-1] = false;
}

// Recursive DFS carve function for maze generation
static void carve_maze_dfs(int cx, int cy,int step) {
    int dirs[4] = {0, 1, 2, 3};
    // Shuffle directions
    for(int i = 3; i > 0; --i) {
        int r = rand() % (i + 1);
        int temp = dirs[i];
        dirs[i] = dirs[r];
        dirs[r] = temp;
    }
    // Direction vectors: 0=up,1=right,2=down,3=left
    int dx[4] = { -1, 0, 1, 0 };
    int dy[4] = { 0, 1, 0, -1 };
    for(int k = 0; k < 4; ++k) {
        int dir = dirs[k];
        int nx = cx + dx[dir] * 2;
        int ny = cy + dy[dir] * 2;
        if(nx >= 0 && nx < MAP_HEIGHT && ny >= 0 && ny < MAP_WIDTH && wall[nx][ny]) {
            // Carve passage between (cx,cy) and (nx,ny)
            wall[nx][ny] = false;
            wall[cx + dx[dir]][cy + dy[dir]] = false;
            if (step > 15 && !hide_flag) {
                add_monster(nx, ny, MONSTER_NAMELESS_BOSS);
                hide_x = nx;
                hide_y = ny;
                hide_flag = true;
            }
            carve_maze_dfs(nx, ny , step+1);
        }
    }
}

void place_monsters() {
    boss_monster = NULL;
    // Place final boss at bottom-right cell
    int bx = MAP_HEIGHT - 2;
    int by = MAP_WIDTH - 2;
    wall[bx][by] = false;
    // Create boss monster
    Monster *boss = malloc(sizeof(Monster));
    boss->type = MONSTER_BOSS;
    boss->maxHP = monster_types[MONSTER_BOSS].maxHP;
    boss->currentHP = boss->maxHP;
    boss->atk = monster_types[MONSTER_BOSS].atk;
    boss->def = monster_types[MONSTER_BOSS].def;
    boss->xp = monster_types[MONSTER_BOSS].xp;
    boss->battle_pos = 0;
    monster_map[bx][by] = boss;
    boss_monster = boss;
    // Place random smaller monsters in maze
    for(int i = 0; i < MAP_HEIGHT; ++i) {
        for(int j = 0; j < MAP_WIDTH; ++j) {
            if((i == 0 && j == 0) || (i == bx && j == by)) {
                continue; // skip player start and boss cell
            }
            if(!wall[i][j]) {
                // floor cell: decide to place monster (15% chance)
                if(rand() % 100 < 15) {
                    // Determine monster type based on distance from start
                    int dist = i + j;
                    MonsterTypeID mtype;
                    if(dist < 20) {
                        MonsterTypeID pool[] = { MONSTER_SLIME, MONSTER_GOBLIN, MONSTER_SKELETON, MONSTER_ZOMBIE };
                        mtype = pool[rand() % 4];
                    } else if(dist < 40) {
                        MonsterTypeID pool[] = { MONSTER_SKELETON, MONSTER_ZOMBIE, MONSTER_GHOST, MONSTER_ORC };
                        mtype = pool[rand() % 4];
                    } else if(dist < 60) {
                        MonsterTypeID pool[] = { MONSTER_ORC, MONSTER_VAMPIRE, MONSTER_DEMON };
                        mtype = pool[rand() % 3];
                    } else {
                        MonsterTypeID pool[] = { MONSTER_DEMON, MONSTER_HYDRA };
                        mtype = pool[rand() % 2];
                    }
                    if(i!= hide_x || j != hide_y){
                        add_monster(i, j, mtype);
                    }
                    
                }
            }
        }
    }
}

// Helper to allocate and place a monster of given type at map cell (x,y)
static void add_monster(int x, int y, int type) {
    Monster *m = malloc(sizeof(Monster));
    memcpy(m->name, monster_types[type].name, sizeof(m->name));
    m->type = type;
    m->maxHP = monster_types[type].maxHP;
    m->currentHP = m->maxHP;
    m->atk = monster_types[type].atk;
    m->def = monster_types[type].def;
    m->xp = monster_types[type].xp;
    m->battle_pos = 0;
    monster_map[x][y] = m;
}

// Handle player leveling up if XP threshold reached
void level_up() {
    while(player->level < 99 && player->xp >= player->xp_to_next) {
        player->xp -= player->xp_to_next;
        player->level++;
        // Increase player stats at level-up
        player->maxHP += 10;
        player->currentHP = player->maxHP;
        player->atk += 2;
        player->def += 1;
        if(player->level < 99) {
            player->xp_to_next = 50 + player->level * 3;
        } else {
            player->xp_to_next = 0; // max level reached
        }
        add_log("Leveled up! You are now Level %d.", player->level);
    }
}

// Award experience and trigger level-up check
void gain_experience(int xp) {
    player->xp += xp;
    level_up();
}

// Use a healing potion on player or a pet
// target_type: 0 for player, 1 for pet; pet_index for which pet (1-5)
void use_healing(int target_type, int pet_index) {
    if(player->potions <= 0) {
        add_log("No healing potions left!");
        return;
    }
    if(target_type == 0) {
        // Heal player to full
        player->currentHP = player->maxHP;
        add_log("You feel rejuvenated to full health.");
    } else if(target_type == 1) {
        if(pet_index >= 1 && pet_index <= player->pet_count) {
            Monster *pet = &player->pets[pet_index - 1];
            pet->currentHP = pet->maxHP;
            add_log("Pet%d (%s) is fully healed.", pet_index, monster_types[pet->type].name);
        } else {
            add_log("Invalid pet ID for healing.");
            return;
        }
    }
    player->potions--;
}

// Move player by (dx,dy). Returns true if movement triggered a battle.
bool move_player(int dx, int dy, bool continuous) {
    if(continuous) {
        // Move continuously until obstacle or monster is encountered
        while(true) {
            int nx = player_x + dx;
            int ny = player_y + dy;
            if(nx < 0 || nx >= MAP_HEIGHT || ny < 0 || ny >= MAP_WIDTH) {
                // Reached boundary
                break;
            }
            if(wall[nx][ny]) {
                // Wall encountered
                break;
            }
            if(monster_map[nx][ny] != NULL) {
                // Monster ahead, stop before stepping into it
                break;
            }
            // Move one step
            player_x = nx;
            player_y = ny;
        }
        // Stopped moving (either at wall or just before monster)
        return false;
    } else {
        // Single-step movement
        int nx = player_x + dx;
        int ny = player_y + dy;
        if(nx < 0 || nx >= MAP_HEIGHT || ny < 0 || ny >= MAP_WIDTH) {
            // Out of bounds, ignore
            return false;
        }
        if(wall[nx][ny]) {
            // There's a wall, cannot move
            return false;
        }
        if(monster_map[nx][ny] != NULL) {
            // Stepping into a monster triggers battle
            Monster *mon = monster_map[nx][ny];
            start_battle(mon);
            return true;
        } else {
            // Move into empty cell
            player_x = nx;
            player_y = ny;
            return false;
        }
    }
}


void pet_free_by_id(int pet_id) {
    if (pet_id < 1 || pet_id > player->pet_count || player->pets[pet_id - 1].type == -1) {
        add_log("Invalid pet ID");
        return; 
    }

    if(player->pet_count >= 1 && player->pets[pet_id - 1].battle_pos == 0) {
        // Free pet in slot 1 (if not currently in battle)
        for(int j = pet_id - 1; j < MAX_PETS - 1; ++j) {
            player->pets[j] = player->pets[j+1];
        }
        player->pets[player->pet_count - 1].type = -1; // Clear last slot
        player->pet_count--;
        add_log("Pet%d released.", pet_id);
    } else {
        add_log("Cannot release Pet%d (ensure it's not in battle).", pet_id);
    }
    draw_stats();
}

void pet_free_by_name(char* pet_name) {
    int pet_index = -1;
    for(int i = 0; i < player->pet_count; ++i) {
        if(strcmp(player->pets[i].name, pet_name) == 0 && player->pets[i].type != -1) {
            pet_index = i;
            break;
        }
    }
    if(pet_index == -1) {
        add_log("Pet name not found: %s", pet_name);
        return;
    }
    if(player->pet_count >= 1 && player->pets[pet_index].battle_pos == 0) {
        // Free pet by name (if not currently in battle)
        for(int j = pet_index; j < MAX_PETS - 1; ++j) {
            player->pets[j] = player->pets[j+1];
        }
        player->pets[player->pet_count - 1].type = -1; // Clear last slot
        player->pet_count--;
        add_log("Pet %s released.", pet_name);
    } else {
        add_log("Cannot release Pet %s (ensure it's not in battle).", pet_name);
    }
    draw_stats();
}