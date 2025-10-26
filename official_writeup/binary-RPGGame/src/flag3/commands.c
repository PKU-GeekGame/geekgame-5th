#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <ctype.h>
#include "game.h"
#include "battle.h"
#include "ui.h"

// Command parser structures
struct command_data_block;
typedef bool (*trans_operation)(void *,char* input);
typedef void (*exec_callback)(struct command_data_block*);

// 命令参数结构
typedef struct {
    const char *pname;
    uint32_t mini_match;
} struct_keyword;

typedef struct {
    exec_callback exec_func;
    uint32_t subcmd;
} struct_eol;

typedef struct {
    const char *pHelp;
    int min;
    int max;
} struct_num;

typedef struct {
    const char *pHelp;
    uint32_t mini_match;
} struct_string;

// 状态转移结构
typedef struct struct_transtion {
    trans_operation pfn;
    void *argument;  // 可指向任意参数类型
    struct struct_transtion *accept; // 可接受的下一个参数
    struct struct_transtion *alternate; // 可替代的下一个参数
} command_node;

// 命令数据块
typedef struct command_data_block {
    char tokens[16][128];
    int token_count;
} command_context;


// Parsing helper functions
bool keyword_action(struct_keyword *kw, char *input) {
    int inputlen = strlen(input);
    int kwlen = strlen(kw->pname);
    if(inputlen > kwlen || inputlen < kw->mini_match) {
        return false;
    }
    if(strncmp(input, kw->pname, inputlen) == 0) {
        return true;
    }
    return false;
}

bool string_action(struct_string* str, char* input) {
    char input_buf[128];
    int inputlen = strlen(input);
    if (inputlen >= MAX_NAME) {
        add_log("name too long!");
        return false;
    }

    for(int i=0;i< 5;i++) {
        if (strncmp(input,player->pets[i].name,inputlen) == 0) {
            return true;
        }
    }
    snprintf(input_buf, 30, "Pet name not exist: %s...", input);
    add_log(input_buf);
    return false;
}

bool rename_action(struct_string* str, char* input) {
    char input_buf[128];
    int inputlen = strlen(input);
    if (inputlen >= MAX_NAME) {
        add_log("name too long!");
        return false;
    }
    return true;
}

bool num_action(struct_num *num, char *input) {
    // numeric validation
    for(size_t i = 0; i < strlen(input); ++i) {
        if(!isdigit((unsigned char)input[i])) return false;
    }
    int val = atoi(input);
    if(val < num->min || val > num->max) return false;
    return true;
}

// Node creation helpers
command_node* create_node(trans_operation op, void *arg) {
    command_node *node = calloc(1, sizeof(command_node));
    node->pfn = op;
    node->argument = arg;
    return node;
}
struct_keyword* create_keyword(const char *name) {
    struct_keyword *kw = malloc(sizeof(struct_keyword));
    kw->pname = name;
    kw->mini_match = 2;  // require at least 2 characters to match
    return kw;
}

struct_string* create_string(int mini_match, const char* help) {
    struct_string* cs = calloc(1, sizeof(struct_string));
    cs->pHelp = help;
    cs->mini_match = mini_match;
    return cs;
}

struct_num* create_num(int min,int max,const char* help) {
    struct_num* num = calloc(1, sizeof(struct_num));
    num->min = min;
    num->max = max;
    num->pHelp = help;
    return num;
}
struct_eol* create_eol(exec_callback func) {
    struct_eol *e = malloc(sizeof(struct_eol));
    e->exec_func = func;
    return e;
}

// Global command trees for map mode and battle mode
static command_node *map_cmd_tree;
static command_node *battle_cmd_tree;
command_context cmd_ctx;

// Exec functions for map commands
void exec_move(command_context* data) {
    char * subcmd = data->tokens[1];
    char * opt = data->tokens[2];
    bool continuous = false;
    if (opt != NULL && strcmp(opt, "always") == 0) {
        continuous = true;
    }
    if(strcmp(subcmd, "up") == 0) {
        move_player(-1, 0, continuous);
        draw_map();
        draw_stats();
    }

    else if(strcmp(subcmd, "down") == 0) {
        move_player(1, 0, continuous);
        draw_map();
        draw_stats();
    }
    else if(strcmp(subcmd, "left") == 0) {
        move_player(0, -1, continuous);
        draw_map();
        draw_stats();
    }
    else if(strcmp(subcmd, "right") == 0) {
        move_player(0, 1, continuous);
        draw_map();
        draw_stats();
    }
    else {
        add_log("Invalid direction for move.");
    }

}

void exec_heal_user(command_context* data) { use_healing(0, 0); }
void exec_heal_pet(command_context* data) { use_healing(1, 1); }

void bring_pet_by_id(command_context* data) {
    char * subcmd = data->tokens[2];
    if(strcmp(subcmd, "id") == 0) {
        int id = atoi(data->tokens[3]);
        int pos = atoi(data->tokens[4]);
        if (id < 1 || id > player->pet_count) {
            add_log("Invalid pet ID.");
            return;
        }
        if (pos < 1 || pos > 2) {
            add_log("Invalid battle position (1 or 2).");
            return;
        }
        if(player->pets[id - 1].type != -1) {
            // Bring pet into battle slot
            // Check if slot already occupied
            for(int i = 0; i < player->pet_count; ++i) {
                if(player->pets[i].battle_pos == pos) {
                    add_log("Battle slot %d already occupied.", pos);
                    return;
                }
            }
            player->pets[id - 1].battle_pos = pos;
            add_log("Pet%d (%s) brought into battle slot %d.", id, player->pets[id - 1].name, pos);
        } else {
            add_log("Pet%d is already in battle.", id);
        }
    }
    else {
        add_log("Invalid subcommand for bring pet.");
    }
    draw_stats();
}

void bring_pet_by_name(command_context* data) {
    char* subcmd = data->tokens[2];
    if(strcmp(subcmd, "name") == 0) {
        char* pet_name = data->tokens[3];
        int pos = atoi(data->tokens[4]);
        int pet_index = -1;
        for(int i = 0; i < player->pet_count; ++i) {
            if(player->pets[i].type != -1 && strcmp(player->pets[i].name, pet_name) == 0) {
                pet_index = i;
                break;
            }
        }
        if (pet_index == -1) {
            add_log("Pet not found: %s", pet_name);
            return;
        }
        if (pos < 1 || pos > 2) {
            add_log("Invalid battle position (1 or 2).");
            return;
        }
        if (player->pets[pet_index].type != -1) {
            // Bring pet into battle slot
            // Check if slot already occupied
            for (int i = 0; i < player->pet_count; ++i) {
                if (player->pets[i].battle_pos == pos) {
                    add_log("Battle slot %d already occupied.", pos);
                    return;
                }
            }
            player->pets[pet_index].battle_pos = pos;
            add_log("Pet %s brought into battle slot %d.", pet_name, pos);
        } else {
            add_log("Pet %s is already in battle.", pet_name);
        }
    }
    else {
        add_log("Invalid subcommand for bring pet.");
    }
    draw_stats();
}

void pet_free(command_context* data) {
    char * subcmd = data->tokens[2];
    if(strcmp(subcmd, "id") == 0) {
        int id = atoi(data->tokens[3]);
        pet_free_by_id(id);
    }
    else if(strcmp(subcmd, "name") == 0) {
        pet_free_by_name(data->tokens[3]);
    }
    else {
        add_log("Invalid subcommand for pet free.");
    }
    draw_stats();
}

void pet_rename(command_context* data) {
    // rename_ability = true;
    if (rename_ability == false) {
        add_log("Rename ability locked.");
        return;
    }
    int pet_id = atoi(data->tokens[2]);
    if (pet_id < 1 || pet_id > player->pet_count) {
        add_log("Invalid pet ID.");
        return; 
    }
    char* new_name = data->tokens[3];
    if (strlen(new_name) >= MAX_NAME) {
        add_log("New name too long.");
        return;
    }
    memcpy(player->pets[pet_id - 1].name, new_name, 128);
    add_log("Pet%d renamed to %s.", pet_id, player->pets[pet_id - 1].name);
    draw_stats();

}

void exec_pet_release(command_context* data) {
    // Remove pet from battle slot 1
    int res_pos = atoi(data->tokens[2]);
    for(int i = 0; i < player->pet_count; ++i) {
        if(player->pets[i].battle_pos == res_pos) player->pets[i].battle_pos = 0;
    }
    draw_stats();
}

// Exec functions for battle commands
void exec_fight(command_context* data)   { battle_action_fight(); }
void exec_defense(command_context* data) { battle_action_defense(); }
void exec_catch_cmd(command_context* data) { battle_action_catch(); }
void exec_run(command_context* data)    { battle_action_run(); }
void exec_skip(command_context* data)   { battle_action_skip(); }

// Build the command trees for map and battle modes
void init_commands() {
    // Map mode commands tree
    command_node *root = create_node(NULL, NULL);
    // "move" command and directions
    command_node *move_node = create_node(keyword_action, create_keyword("move"));
    root->alternate = move_node;
    command_node *move_up = create_node(keyword_action, create_keyword("up"));
    command_node *move_down = create_node(keyword_action, create_keyword("down"));
    command_node *move_left = create_node(keyword_action, create_keyword("left"));
    command_node *move_right = create_node(keyword_action, create_keyword("right"));
    move_node->accept = move_up;
    move_up->alternate = move_down;
    move_down->alternate = move_left;
    move_left->alternate = move_right;
    // Optional "always" for each direction
    command_node *always_up = create_node(keyword_action, create_keyword("always"));
    command_node *always_down = create_node(keyword_action, create_keyword("always"));
    command_node *always_left = create_node(keyword_action, create_keyword("always"));
    command_node *always_right = create_node(keyword_action, create_keyword("always"));
    // End-of-line for move actions
    command_node *move_up_end = create_node(NULL, create_eol(exec_move));
    command_node *move_down_end = create_node(NULL, create_eol(exec_move));
    command_node *move_left_end = create_node(NULL, create_eol(exec_move));
    command_node *move_right_end = create_node(NULL, create_eol(exec_move));
    // Attach optional branches
    move_up->accept = always_up;
    always_up->accept = move_up_end;
    always_up->alternate = move_up_end;
    move_down->accept = always_down;
    always_down->accept = move_down_end;
    always_down->alternate = move_down_end;
    move_left->accept = always_left;
    always_left->accept = move_left_end;
    always_left->alternate = move_left_end;
    move_right->accept = always_right;
    always_right->accept = move_right_end;
    always_right->alternate = move_right_end;
    // "heal" command
    command_node *heal_node = create_node(keyword_action, create_keyword("heal"));
    move_node->alternate = heal_node;
    command_node *heal_user_node = create_node(keyword_action, create_keyword("user"));
    command_node *heal_pet_node = create_node(keyword_action, create_keyword("pet"));
    heal_node->accept = heal_user_node;
    heal_user_node->alternate = heal_pet_node;
    command_node *heal_user_end = create_node(NULL, create_eol(exec_heal_user));
    heal_user_node->accept = heal_user_end;
    // Heal pet with pet ID
    command_node *pet_id_node = create_node(num_action, create_num(1, MAX_PETS,"<pet_id>"));
    heal_pet_node->accept = pet_id_node;
    // EOL nodes for each pet ID
    command_node *heal_pet_end = create_node(NULL, create_eol(exec_heal_pet));
    pet_id_node->accept = heal_pet_end;
    // "pet" command (bring, release, free)
    command_node *pet_node = create_node(keyword_action, create_keyword("pet"));
    heal_node->alternate = pet_node;
    command_node *bring_node = create_node(keyword_action, create_keyword("bring"));
    command_node *release_node = create_node(keyword_action, create_keyword("release"));
    command_node *free_node = create_node(keyword_action, create_keyword("free"));
    command_node *rename_node = create_node(keyword_action, create_keyword("rename"));

    pet_node->accept = bring_node;
    bring_node->alternate = release_node;
    release_node->alternate = free_node;
    free_node->alternate = rename_node;
    // pet bring id <id> <pos> 
    // pet bring name <name> <pos>
    command_node *bring_id_node = create_node(keyword_action, create_keyword("id"));
    command_node *bring_name_node = create_node(keyword_action, create_keyword("name"));
    command_node *bring_name_str_node = create_node(string_action, create_string(2,"<name>"));
    command_node *bring_id_num_node = create_node(num_action, create_num(1, MAX_PETS, "<pet_id>"));
    bring_node->accept = bring_id_node;
    bring_id_node->accept = bring_id_num_node;
    bring_id_node->alternate = bring_name_node;
    bring_name_node->accept = bring_name_str_node;
    command_node *bring_id_pos_node = create_node(num_action, create_num(1, 2,"<pet_pos>"));
    bring_id_num_node->accept = bring_id_pos_node;
    command_node *bring_id_end = create_node(NULL, create_eol(bring_pet_by_id));
    command_node *bring_name_end = create_node(NULL, create_eol(bring_pet_by_name));
    command_node *bring_name_pos_node = create_node(num_action, create_num(1, 2,"<pet_pos>"));
    bring_name_str_node->accept = bring_name_pos_node;
    bring_id_pos_node->accept = bring_id_end;
    bring_name_pos_node->accept = bring_name_end;
    // pet release <pos>
    command_node *release_pos_node = create_node(num_action, create_num(1, 2,"<pet_pos>"));
    release_node->accept = release_pos_node;
    command_node *release_end = create_node(NULL, create_eol(exec_pet_release));
    release_pos_node->accept = release_end;
    // pet free id <id>
    // pet free name <name>
    command_node *free_id_node = create_node(keyword_action, create_keyword("id"));
    command_node *free_id_num_node = create_node(num_action, create_num(1, MAX_PETS, "<pet_id>"));
    command_node *free_name_node = create_node(keyword_action, create_keyword("name"));
    command_node *free_name_str_node = create_node(string_action, create_string(2,"<name>"));
    free_node->accept = free_id_node;
    command_node *free_id_end = create_node(NULL, create_eol(pet_free));
    command_node *free_name_end = create_node(NULL, create_eol(pet_free));
    free_id_node->accept = free_id_num_node;
    free_id_node->alternate = free_name_node;
    free_id_num_node->accept = free_id_end;
    free_id_end->alternate = free_name_node;
    free_name_node->accept = free_name_str_node;
    free_name_str_node->accept = free_id_end;
    // pet rename <id> <newname>
    command_node *rename_id_node = create_node(num_action, create_num(1, MAX_PETS,"<pet_id>"));
    command_node *rename_name_node = create_node(rename_action, create_string(2,"<new_name>"));
    command_node *rename_end = create_node(NULL, create_eol(pet_rename));
    rename_node->accept = rename_id_node;
    rename_id_node->accept = rename_name_node;
    rename_name_node->accept = rename_end;


    // Save map commands root
    map_cmd_tree = root;
    // Battle mode commands tree
    command_node *broot = create_node(NULL, NULL);
    command_node *fight_node = create_node(keyword_action, create_keyword("fight"));
    broot->alternate = fight_node;
    fight_node->accept = create_node(NULL, create_eol(exec_fight));
    command_node *def_node = create_node(keyword_action, create_keyword("defense"));
    fight_node->alternate = def_node;
    def_node->accept = create_node(NULL, create_eol(exec_defense));
    command_node *catch_node = create_node(keyword_action, create_keyword("catch"));
    def_node->alternate = catch_node;
    catch_node->accept = create_node(NULL, create_eol(exec_catch_cmd));
    command_node *run_node = create_node(keyword_action, create_keyword("run"));
    catch_node->alternate = run_node;
    run_node->accept = create_node(NULL, create_eol(exec_run));
    command_node *skip_node = create_node(keyword_action, create_keyword("skip"));
    run_node->alternate = skip_node;
    skip_node->accept = create_node(NULL, create_eol(exec_skip));
    battle_cmd_tree = broot;
}


int handle_tab(char *buf, int buf_sz, int cur_pos)
{
    char stack_cmd[512];
    memcpy(stack_cmd, buf, buf_sz);
    cmd_ctx.token_count = 0;
    char* token = strtok(stack_cmd, " ");
    int token_len = 127;
    while (token && cmd_ctx.token_count < 16) {
        memcpy(cmd_ctx.tokens[cmd_ctx.token_count], token, token_len);
        cmd_ctx.tokens[cmd_ctx.token_count++][token_len] = '\0';
        token = strtok(NULL, " ");
    }
    command_node *root = in_battle ? battle_cmd_tree : map_cmd_tree;
    command_context *ctx = &cmd_ctx;
    command_node* current = root->alternate;
    command_node* last_valid = NULL;
    
    int idx = 0;

    while(current && idx < ctx->token_count) {
        
        if(current->pfn) {
            if(current->pfn(current->argument, ctx->tokens[idx])) {
                last_valid = current;
                current = current->accept;
                idx++;
            } else {
                current = current->alternate;
            }
        } else {
            current = current->alternate;
        }
                 
    }

    // 从最后一个有效节点开始检查结束符
    current = last_valid;
    if (idx == ctx->token_count && current) {
        int last_cmd_len = strlen(ctx->tokens[idx-1]);
        // 如果当前所有节点都正确，查看是否需要补全
        if(current && current->pfn == keyword_action) {
            int current_len = strlen(((struct_keyword*)current->argument)->pname);
            if (last_cmd_len < current_len) {
                // 补全命令
                for (int i = last_cmd_len; i < current_len; i++) {
                    buf[cur_pos++] = ((struct_keyword*)current->argument)->pname[i];
                }
                buf[cur_pos++] = ' ';
                return cur_pos;
            }
            else if (buf[cur_pos-1] != ' ') {
                buf[cur_pos++] = ' ';
                return cur_pos;
            }
        } else if(current && current->pfn == string_action) {
            for (int i=0;i< 5;i++){
                if (strncmp(ctx->tokens[idx-1], player->pets[i].name,last_cmd_len) == 0) {
                    memcpy(buf + cur_pos, player->pets[i].name + last_cmd_len, MAX_NAME - last_cmd_len);
                    cur_pos += strlen(player->pets[i].name + last_cmd_len);
                    buf[cur_pos++] = ' ';
                    return cur_pos;
                }
            }
        }

    }
    return cur_pos;

}


// Process a user input command string in debug mode
void process_input_command(char *input) {
    if(strcmp(input, "REDRAW_ALL") == 0) {
        redraw_all();
        return;
    }
    cmd_ctx.token_count = 0;
    char* token = strtok(input, " ");
    while (token && cmd_ctx.token_count < 16) {
        int token_len = 127;
        memcpy(cmd_ctx.tokens[cmd_ctx.token_count], token, token_len);
        cmd_ctx.tokens[cmd_ctx.token_count++][token_len] = '\0';
        token = strtok(NULL, " ");
    }

    command_node *root = in_battle ? battle_cmd_tree : map_cmd_tree;
    command_context *ctx = &cmd_ctx;
    command_node* current = root->alternate;
    int idx = 0;
    // Traverse command tree with tokens
    while(current && idx < ctx->token_count) {
        if(current->pfn) {
            if(current->pfn(current->argument, ctx->tokens[idx])) {
                current = current->accept;
                idx++;
            } else {
                current = current->alternate;
            }
        } else {
            current = current->alternate;
        } 
    }
    if(idx == ctx->token_count && current ) {
        while (current && current->pfn != NULL) {
            current = current->alternate;
        }
        if (current == NULL) {
            add_log("Invalid command.");
            return;
        }
        // Reached end-of-line node successfully
        if (current->argument && ((struct_eol*)current->argument)->exec_func) {
            struct_eol* eol = (struct_eol*)current->argument;
            eol->exec_func(ctx);
            return;
        }
    } else {
        add_log("Invalid command.");
    }
    // After executing, refresh the map and stats display

}
