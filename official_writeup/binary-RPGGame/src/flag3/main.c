#include <stdio.h>
#include <ncurses.h>
#include "game.h"
#include "ui.h"
#include "commands.h"
#include <locale.h>


int read_line_with_completion(WINDOW *win, const char *prompt, char *out, int out_sz)
{
    keypad(win, TRUE);
    // 注意：外部应已调用 cbreak(); noecho();
    // 这里确保第一次渲染
    int cur_pos = 0;
    werase(win);
    mvwprintw(win, 0, 0, "%s%s", prompt, out);
    // 光标放到末尾
    wmove(win, 0, (int)strlen(prompt) + (int)strlen(out));
    for (;;) {
        int ch = wgetch(win);
        if (ch == ERR) continue;


        if (ch == '\n' || ch == '\r') {
            // 完成
            return 0;
        } else if (ch == KEY_BACKSPACE || ch == 127 || ch == 8) {
            out[cur_pos > 0 ? --cur_pos : 0] = '\0';
        } else if (ch == '\t' || ch == 9) {
            cur_pos = handle_tab(out, out_sz, cur_pos);
            out[cur_pos] = '\0';
        } else  {
            if (cur_pos + 1 < out_sz) {
                out[cur_pos++] = (char)ch;
                out[cur_pos] = '\0';
            } else {
                beep();
            }
        } 
        werase(win);
        mvwprintw(win, 0, 0, "%s%s", prompt, out);
        // 光标放到末尾
        wmove(win, 0, (int)strlen(prompt) + (int)strlen(out));
    }
}




int main() {
    setlocale(LC_ALL, "");
    // Initialize game state, UI, and command parser

    init_game();
    init_ui();
    char *input_line = malloc(512);

    init_commands();
    // 关键：启动即输出一条欢迎日志，并强制全量重绘一次
    redraw_all();
    // Initial UI draw and message
    draw_map();
    draw_stats();
    add_log("Explore the maze and defeat the Evil Dragon!");
    update_log();
    // Main loop
    
    while(!game_over) {
        if(debug_mode) {
            memset(input_line, 0, 512);
            curs_set(1);
            // Debug/command mode: show prompt and read input
            werase(inputWin);
            mvwprintw(inputWin, 0, 0, "> ");
            wrefresh(inputWin);
            cbreak();
            noecho();
            // box(inputWin, 0, 0); // 只是示意：画个边框
            wmove(inputWin, 0, 0);
            wrefresh(inputWin);

            // 读取一行（带 Tab 补全）
            int rc = read_line_with_completion(inputWin, "> ",
                                            input_line, 512);
            if (rc != 0) continue;;
            // 回显到主屏
            if(strcmp(input_line, "`") == 0) {
                debug_mode = false;
                curs_set(0);
                werase(inputWin);
                wrefresh(inputWin);
                continue;
                
            }
            // for (int i=0;i<strlen(input_line);i++){
            //     add_log("logs:0x%02x",(uint8_t)input_line[i]);
            // } 
            
            process_input_command(input_line);
            draw_map();
            draw_stats();
            update_log();


            // If backtick pressed as sole input, exit debug mode

            // Process the debug command
            
            continue;  // loop again (avoid moving in debug mode)
        }
        if(in_battle && !debug_mode) {
            // Automatic battle mode: perform rounds every 0.5s
            battle_action_fight();   // execute a fight round automatically
            if(!in_battle) {
                // Battle ended (monster defeated or run away)
                continue;
            }
            // After one round, pause briefly or until user toggles debug mode
            halfdelay(5); // half-delay: wait up to 0.5 second for input
            int ch = getch();
            nocbreak();
            cbreak();
            if(ch == '`') {
                debug_mode = true;
                continue;
            }
            // Otherwise, no user intervention, loop will continue next round
            continue;
        }
        // Map exploration mode: wait for movement input
        int ch = getch();
        if(ch == '`') {
            debug_mode = true;
            continue;
        }
        // Translate arrow keys to movement
        int dx = 0, dy = 0;
        switch(ch) {
            case KEY_UP:    dx = -1; dy = 0; break;
            case KEY_DOWN:  dx =  1; dy = 0; break;
            case KEY_LEFT:  dx =  0; dy = -1; break;
            case KEY_RIGHT: dx =  0; dy =  1; break;
            default: dx = 0; dy = 0;
        }
        if(dx != 0 || dy != 0) {
            bool entered_battle = move_player(dx, dy, false);
            draw_map();
            draw_stats();
            if(entered_battle) {
                // Battle triggered, loop will handle in_battle branch
                continue;
            }
        }
        // Check if player died (game_over) or boss defeated (game_over) after any action
        if(game_over) break;
    }
    // Print final outcome
    if(game_over) {
        if(player->currentHP <= 0) {
            add_log("Game Over. You have perished.");
        } else if(boss_monster && boss_monster->currentHP <= 0) {
            add_log("Victory! The Evil Dragon is no more.");
        }
        update_log();
    }
    // Wait for key press before exit
    nodelay(stdscr, FALSE);
    getch();
    shutdown_ui();
    return 0;
}
