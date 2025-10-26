#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "game.h"
#include "ui.h"
#include "battle.h"

Monster *current_monster = NULL;
bool battle_first_turn = true;
// External log function to record battle events
extern void add_log(const char *format, ...);

// Begin a battle with the given monster
void start_battle(Monster *monster) {
    in_battle = true;
    current_monster = monster;
    battle_first_turn = true;
    // Clear log for new battle and announce encounter
    clear_log();
    add_log("Encountered a %s!", monster_types[monster->type].name);
    // Set default active pets for battle (first two pets if not manually set)
    bool anyAssigned = false;
    for(int i = 0; i < player->pet_count; ++i) {
        if(player->pets[i].battle_pos != 0) {
            anyAssigned = true;
            // If assigned pet is dead, set to standby
            if(player->pets[i].currentHP <= 0) {
                player->pets[i].battle_pos = 0;
            }
        }
    }
    if(!anyAssigned) {
        // Assign first pet to slot 1, second pet to slot 2 by default (if available and alive)
        if(player->pet_count > 0 && player->pets[0].currentHP > 0) {
            player->pets[0].battle_pos = 1;
        }
        if(player->pet_count > 1 && player->pets[1].currentHP > 0) {
            player->pets[1].battle_pos = 2;
        }
    }
    draw_stats();
    draw_map();
}

// End the current battle and clean up state
void end_battle() {
    if(current_monster != NULL) {
        // If monster was defeated or captured, remove it from the map
        if(current_monster->currentHP <= 0) {
            for(int i = 0; i < MAP_HEIGHT; ++i) {
                for(int j = 0; j < MAP_WIDTH; ++j) {
                    if(monster_map[i][j] == current_monster) {
                        monster_map[i][j] = NULL;
                    }
                }
            }
            // Free monster memory if not the boss (boss will be freed at game end)
            if(current_monster->type != MONSTER_BOSS) {
                free(current_monster);
            }
        }
    }
    // Reset battle flags
    current_monster = NULL;
    in_battle = false;
    // Reset all pets to standby (remove battle_pos), remove dead pets from slots
    for(int i = 0; i < player->pet_count; ++i) {
        if(player->pets[i].currentHP == 0){
            player->pets[i].battle_pos = 0; // Dead pets cannot be in battle
            pet_free_by_id(i + 1); // Remove dead pet from collection
        }
        // If pet died (HP 0) during battle, it remains in list but at 0 HP
        // (User may revive later or free it if desired)
    }
    draw_stats();
    draw_map();
}

// Perform attacks by player and pets on the monster (one round of offense)
void player_attack(Monster *monster, Monster *pet1, Monster *pet2) {
    // Player attacks
    if(monster->currentHP > 0) {
        int dmg = player->atk - monster->def;
        if(dmg < 0) dmg = 0;
        monster->currentHP -= dmg;
        add_log("You attack the %s for %d damage, Monster HP: %d.", monster_types[monster->type].name, dmg, monster->currentHP);
    }
    // Pet1 attacks
    if(monster->currentHP > 0 && pet1 != NULL && pet1->currentHP > 0) {
        int dmg = pet1->atk - monster->def;
        if(dmg < 0) dmg = 0;
        monster->currentHP -= dmg;
        add_log("%s attacks for %d damage, Monster HP: %d.", monster_types[pet1->type].name, dmg, monster->currentHP);
    }
    // Pet2 attacks
    if(monster->currentHP > 0 && pet2 != NULL && pet2->currentHP > 0) {
        int dmg = pet2->atk - monster->def;
        if(dmg < 0) dmg = 0;
        monster->currentHP -= dmg;
        add_log("%s attacks for %d damage, Monster HP: %d.", monster_types[pet2->type].name, dmg, monster->currentHP);
    }
}

// Monster attacks one target (pets have priority)
void monster_attack(Monster *monster) {
    // Determine target priority: Pet1 -> Pet2 -> Player
    Monster *pet1 = NULL;
    Monster *pet2 = NULL;
    for(int i = 0; i < player->pet_count; ++i) {
        if(player->pets[i].battle_pos == 1 && player->pets[i].currentHP > 0) pet1 = &player->pets[i];
        if(player->pets[i].battle_pos == 2 && player->pets[i].currentHP > 0) pet2 = &player->pets[i];
    }
    if(pet1 != NULL) {
        int dmg = monster->atk - pet1->def;
        if(dmg < 0) dmg = 0;
        pet1->currentHP -= dmg;
        if(pet1->currentHP < 0) pet1->currentHP = 0;
        add_log("%s attacks your %s for %d damage.", monster_types[monster->type].name, monster_types[pet1->type].name, dmg);
        if(pet1->currentHP == 0) {
            add_log("Your %s has been defeated!", monster_types[pet1->type].name);
            pet1->battle_pos = 0; // Remove from battle if defeated
            pet1 = NULL; // Mark as dead
        }
    } else if(pet2 != NULL) {
        int dmg = monster->atk - pet2->def;
        if(dmg < 0) dmg = 0;
        pet2->currentHP -= dmg;
        if(pet2->currentHP < 0) pet2->currentHP = 0;
        add_log("%s attacks your %s for %d damage.", monster_types[monster->type].name, monster_types[pet2->type].name, dmg);
        if(pet2->currentHP == 0) {
            add_log("Your %s has been defeated!", monster_types[pet2->type].name);
            pet2->battle_pos = 0; // Remove from battle if defeated
            pet2 = NULL; // Mark as dead
        }
    } else {
        int dmg = monster->atk - player->def;
        if(dmg < 0) dmg = 0;
        player->currentHP -= dmg;
        if(player->currentHP < 0) player->currentHP = 0;
        add_log("%s attacks you for %d damage.", monster_types[monster->type].name, dmg);
    }
}

// Manual battle command: fight (perform one round of attacks and counter-attack)
void battle_action_fight() {
    if(current_monster == NULL) return;
    // Determine active pets in battle
    Monster *pet1 = NULL, *pet2 = NULL;
    for(int i = 0; i < player->pet_count; ++i) {
        if(player->pets[i].battle_pos == 1 && player->pets[i].currentHP > 0) pet1 = &player->pets[i];
        if(player->pets[i].battle_pos == 2 && player->pets[i].currentHP > 0) pet2 = &player->pets[i];
    }
    // Player and pets attack monster
    player_attack(current_monster, pet1, pet2);
    // Check if monster was defeated by this attack round
    if(current_monster->currentHP <= 0) {
        add_log("The %s is defeated!", monster_types[current_monster->type].name);
        if(current_monster->type != MONSTER_BOSS) {
            gain_experience(current_monster->xp);
        }
        
        if(current_monster->type == MONSTER_NAMELESS_BOSS) {
            add_log("Congratulations! You have vanquished the Nameless Boss!");
            // game_over = true;
            rename_ability = true; // Unlock rename ability upon winning
        }
        // If final boss defeated, set game over (win)
        if(current_monster->type == MONSTER_BOSS) {
            add_log("Congratulations! You have defeated the Evil Dragon and won the game!");
            game_over = true;
        }
        end_battle();
        return;
    }
    // Monster survives, so it attacks back
    monster_attack(current_monster);
    // Check if player died from counter-attack
    if(player->currentHP <= 0) {
        add_log("You have been slain by the %s...", monster_types[current_monster->type].name);
        game_over = true;
        end_battle();
        return;
    }
    // Mark that a turn has passed (no longer first turn)
    battle_first_turn = false;
    draw_stats();
}

// Manual battle command: defense (double defense for this turn, no attack, then monster attacks)
void battle_action_defense() {
    if(current_monster == NULL) return;
    // Temporarily double defense stats
    int orig_player_def = player->def;
    player->def *= 2;
    int orig_pet_def[MAX_PETS];
    for(int i = 0; i < player->pet_count; ++i) {
        orig_pet_def[i] = player->pets[i].def;
        player->pets[i].def *= 2;
    }
    add_log("You brace yourself (defense up)!");
    // Monster attacks (player/pets don't attack this turn)
    monster_attack(current_monster);
    // Restore original defense values
    player->def = orig_player_def;
    for(int i = 0; i < player->pet_count; ++i) {
        player->pets[i].def = orig_pet_def[i];
    }
    // Check if player died from attack
    if(player->currentHP <= 0) {
        add_log("You were defeated while defending...");
        game_over = true;
        end_battle();
        return;
    }
    battle_first_turn = false;
    draw_stats();
}

// Manual battle command: catch (attempt to capture the monster as a pet)
void battle_action_catch() {
    if(current_monster == NULL) return;
    if(player->pet_count >= MAX_PETS) {
        add_log("Your pet slots are full! You cannot catch more.");
        return;
    }
    // Calculate potential damage from a full round of attacks (player + pets)
    int potential_damage = 0;
    int dmg = player->atk - current_monster->def;
    if(dmg < 0) dmg = 0;
    potential_damage += dmg;
    for(int i = 0; i < player->pet_count; ++i) {
        if(player->pets[i].battle_pos != 0 && player->pets[i].currentHP > 0) {
            dmg = player->pets[i].atk - current_monster->def;
            if(dmg < 0) dmg = 0;
            potential_damage += dmg;
        }
    }
    if(potential_damage >= current_monster->currentHP) {
        // Capture succeeds
        MonsterTypeID t = current_monster->type;
        if(t == MONSTER_BOSS) {
            // Boss cannot be captured
            add_log("You cannot capture the final boss!");
            return;
        }
        // Add monster as new pet at full health
        if(player->pet_count < MAX_PETS) {
            Monster *newpet = &player->pets[player->pet_count];
            newpet->type = t;
            newpet->maxHP = monster_types[t].maxHP;
            newpet->currentHP = newpet->maxHP;
            newpet->atk = monster_types[t].atk;
            newpet->def = monster_types[t].def;
            newpet->xp = monster_types[t].xp;
            newpet->battle_pos = 0;
            memcpy(newpet->name, monster_types[t].name, sizeof(newpet->name));
            player->pet_count++;
            add_log("You captured a %s as your pet!", monster_types[t].name);
        }
        // Award XP as if defeated
        if(current_monster->type != MONSTER_BOSS) {
            gain_experience(current_monster->xp);
        }
        end_battle();
    } else {
        // Capture fails
        add_log("Capture failed! The %s resists.", monster_types[current_monster->type].name);
        // No damage dealt; monster counter-attacks
        monster_attack(current_monster);
        if(player->currentHP <= 0) {
            add_log("You have been slain while trying to capture...");
            game_over = true;
            end_battle();
            return;
        }
    }
    battle_first_turn = false;
    draw_map();
    draw_stats();
}

// Manual battle command: run (attempt to flee from battle)
void battle_action_run() {
    if(current_monster == NULL) return;
    if(current_monster->type == MONSTER_BOSS) {
        add_log("You cannot run from the final boss!");
        return;
    }
    if(battle_first_turn) {
        // Free escape on first turn
        add_log("You fled from the %s successfully.", monster_types[current_monster->type].name);
        end_battle();
    } else {
        // Monster gets a parting shot (double damage)
        Monster *pet1 = NULL;
        Monster *pet2 = NULL;
        for(int i = 0; i < player->pet_count; ++i) {
            if(player->pets[i].battle_pos == 1 && player->pets[i].currentHP > 0) pet1 = &player->pets[i];
            if(player->pets[i].battle_pos == 2 && player->pets[i].currentHP > 0) pet2 = &player->pets[i];
        }
        if(pet1 != NULL) {
            int dmg = current_monster->atk - pet1->def;
            if(dmg < 0) dmg = 0;
            dmg *= 2;
            pet1->currentHP -= dmg;
            if(pet1->currentHP < 0) pet1->currentHP = 0;
            add_log("While fleeing, %s hits your %s for %d damage!", monster_types[current_monster->type].name, monster_types[pet1->type].name, dmg);
        } else if(pet2 != NULL) {
            int dmg = current_monster->atk - pet2->def;
            if(dmg < 0) dmg = 0;
            dmg *= 2;
            pet2->currentHP -= dmg;
            if(pet2->currentHP < 0) pet2->currentHP = 0;
            add_log("While fleeing, %s hits your %s for %d damage!", monster_types[current_monster->type].name, monster_types[pet2->type].name, dmg);
        } else {
            int dmg = current_monster->atk - player->def;
            if(dmg < 0) dmg = 0;
            dmg *= 2;
            player->currentHP -= dmg;
            if(player->currentHP < 0) player->currentHP = 0;
            add_log("While fleeing, %s hits you for %d damage!", monster_types[current_monster->type].name, dmg);
        }
        if(player->currentHP <= 0) {
            add_log("You were mortally wounded while running away...");
            game_over = true;
        } else {
            add_log("You manage to escape the battle.");
        }
        end_battle();
    }
}

// Manual battle command: skip (sacrifice pet or take damage to swap places with monster)
void battle_action_skip() {
    if(current_monster == NULL) return;
    // Determine if any pet is available to sacrifice
    Monster *pet1 = NULL;
    Monster *pet2 = NULL;
    for(int i = 0; i < player->pet_count; ++i) {
        if(player->pets[i].battle_pos == 1 && player->pets[i].currentHP > 0) pet1 = &player->pets[i];
        if(player->pets[i].battle_pos == 2 && player->pets[i].currentHP > 0) pet2 = &player->pets[i];
    }
    if(pet1 != NULL) {
        // Sacrifice the first pet
        add_log("You sacrifice your %s to distract the enemy.", monster_types[pet1->type].name);
        // Remove pet1 from party
        int idx = pet1 - player->pets;  // index of pet1
        for(int j = idx; j < player->pet_count - 1; ++j) {
            player->pets[j] = player->pets[j+1];
        }
        player->pet_count--;
    } else {
        // No pet to sacrifice, player takes heavy damage
        int dmg = current_monster->atk - player->def;
        if(dmg < 0) dmg = 0;
        dmg *= 2;
        player->currentHP -= dmg;
        if(player->currentHP < 0) player->currentHP = 0;
        add_log("You take %d damage to skip past the fight.", dmg);
        if(player->currentHP <= 0) {
            add_log("You collapsed while attempting to escape...");
            game_over = true;
            end_battle();
            return;
        }
    }
    // Swap positions: player and monster exchange places on the map
    int mon_x = -1, mon_y = -1;
    for(int i = 0; i < MAP_HEIGHT; ++i) {
        for(int j = 0; j < MAP_WIDTH; ++j) {
            if(monster_map[i][j] == current_monster) {
                mon_x = i;
                mon_y = j;
                break;
            }
        }
        if(mon_x != -1) break;
    }
    if(mon_x != -1) {
        int old_px = player_x;
        int old_py = player_y;
        // Place monster at player's old position
        monster_map[old_px][old_py] = current_monster;
        // Move player to monster's old position
        player_x = mon_x;
        player_y = mon_y;
        monster_map[mon_x][mon_y] = NULL;
        add_log("You skipped past the %s, swapping places!", monster_types[current_monster->type].name);
    }
    end_battle();
}


