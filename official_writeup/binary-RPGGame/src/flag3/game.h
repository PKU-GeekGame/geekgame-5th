#ifndef GAME_H
#define GAME_H
#include <wchar.h>
#include <stdbool.h>

// Constants for map size and UI
#define MAP_WIDTH 60
#define MAP_HEIGHT 40
#define VIEW_HEIGHT 30
#define VIEW_WIDTH 90
#define LOG_LINES 10
#define STAT_COUNT 6   // 1 for player + 5 pets
#define STAT_WIDTH 38
#define STAT_HEIGHT 5

// Max number of pets
#define MAX_PETS 5
#define MAX_NAME 128

// Define monster type indices
typedef enum {
    MONSTER_SLIME,
    MONSTER_GOBLIN,
    MONSTER_SKELETON,
    MONSTER_ZOMBIE,
    MONSTER_GHOST,
    MONSTER_ORC,
    MONSTER_VAMPIRE,
    MONSTER_DEMON,
    MONSTER_HYDRA,
    MONSTER_BOSS,
    MONSTER_NAMELESS_BOSS,
    MONSTER_TYPE_COUNT
} MonsterTypeID;

// Monster prototype info
typedef struct {
    char *name;
    const wchar_t *emoji;   // 由 const char* 改为 const wchar_t*
    int maxHP;
    int atk;
    int def;
    int xp;
} MonsterType;
// Monster instance (for monsters on map or pets)
typedef struct Monster {
    char name[128];
    int type;               // index referencing MonsterType
    int maxHP;
    int currentHP;
    int atk;
    int def;
    int xp;                 // experience yield if defeated
    int battle_pos;         // 0 = not in battle lineup, 1 or 2 = battle slot
} Monster;

// Player (hero) structure
typedef struct {
    char name[128];
    const char *emoji;
    int level;
    int maxHP;
    int currentHP;
    int atk;
    int def;
    int xp;
    int xp_to_next;
    int potions;                 // healing potions available
    Monster pets[MAX_PETS];      // pet collection (up to 5 pets)
    int pet_count;
} Player;

// Global game state variables
extern Player* player;
extern MonsterType monster_types[MONSTER_TYPE_COUNT];
extern bool wall[MAP_HEIGHT][MAP_WIDTH];           // maze layout (true = wall)
extern Monster *monster_map[MAP_HEIGHT][MAP_WIDTH]; // monster presence map
extern int player_x, player_y;                     // player map position
extern Monster *boss_monster;                     // pointer to final boss monster
extern bool in_battle;                            // flag if currently in a battle
extern bool debug_mode;                           // flag if debug/command mode is active
extern bool game_over;                            // flag if game is over (win/lose)
extern bool rename_ability;                       // flag if rename ability is active

// Game initialization and logic functions
void init_game();
void generate_maze();
void place_monsters();
void start_battle(Monster *monster);
void end_battle();
void player_attack(Monster *monster, Monster *pet1, Monster *pet2);
void monster_attack(Monster *monster);
void gain_experience(int xp);
void level_up();
void use_healing(int target_type, int pet_index);
bool move_player(int dx, int dy, bool continuous);
void pet_free_by_id(int pet_id);
void pet_free_by_name(char* pet_name);

#endif
