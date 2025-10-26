#include <stdio.h>
#include <stdarg.h>
#include <string.h>
#include <locale.h>
#include "ui.h"
#include "game.h"
#include <wchar.h>   // 新增
#include <wctype.h>
#include <stdlib.h>
#include <ncurses.h>
#include <curses.h>
#include <ncursesw/ncurses.h>
#include <ncursesw/curses.h>


#define CELL_W 2
WINDOW *mapWin;
WINDOW *statsWin;
WINDOW *logWin;
WINDOW *inputWin;

// Log message buffer (circular for last 10 lines)
static char log_buffer[LOG_LINES][128];
static int log_count = 0;

void redraw_all() {
    // 逐窗绘制并刷新；确保首帧就把所有区域都画出来
    draw_map();
    draw_stats();
    update_log();

    // 调试输入窗口（即使不在 debug 模式，也画出空框，或者你愿意可直接 werase 隐藏）
    werase(inputWin);
    wborder_set(inputWin,
        WACS_VLINE, WACS_VLINE, WACS_HLINE, WACS_HLINE,
        WACS_ULCORNER, WACS_URCORNER, WACS_LLCORNER, WACS_LRCORNER);
    wrefresh(inputWin);

    // 刷新 stdscr，必要时合并刷新队列
    refresh();
    doupdate();
}


// ---------- 通用：绘制外框 ----------
static void draw_frame(WINDOW *win) {
    // 用宽字符边框，单线实线
    wborder_set(win,
        WACS_VLINE, WACS_VLINE, WACS_HLINE, WACS_HLINE,
        WACS_ULCORNER, WACS_URCORNER, WACS_LLCORNER, WACS_LRCORNER);
    wrefresh(win);
}

// ---------- 通用：在 win 内部 y 行画横线，并在左右边界连成“T” ----------
static void draw_inner_hline(WINDOW *win, int y) {
    int h, w; getmaxyx(win, h, w);
    if (y <= 0 || y >= h-1) return;
    // 左边界放 ├，右边界放 ┤，中间画 ─
    mvwadd_wch(win, y, 0, WACS_LTEE);
    mvwhline_set(win, y, 1, WACS_HLINE, w - 2);
    mvwadd_wch(win, y, w-1, WACS_RTEE);
}

// ---------- 状态区：把内部均分为 6 个矩形 ----------
static void draw_stats_grid_lines(WINDOW *stats) {
    int h, w; getmaxyx(stats, h, w);
    // 外框
    draw_frame(stats);

    // 内高度
    int innerH = h - 2;
    // 均分为 6 段：计算 5 条分隔线的位置（与外框共享边）
    for (int k = 1; k <= 5; ++k) {
        int y = 1 + (innerH * k) / 6;  // 均匀落点
        draw_inner_hline(stats, y);
    }
    wrefresh(stats);
}

// 把一段宽字符 glyph 打印成“恰好占 2 列”
// 宽度=2：直接打印；宽度=1：打印 glyph + 空格；空白：打印两个空格
static void put_cell2(WINDOW *win, int row, int col2, const wchar_t *glyph) {
    if (!glyph || glyph[0] == L'\0') {
        mvwaddwstr(win, row, col2, L"  ");
        return;
    }
    int w = wcswidth(glyph, -1);
    if (w >= 2) {
        mvwaddwstr(win, row, col2, glyph);      // 占 2 列
    } else {
        mvwaddwstr(win, row, col2, glyph);      // 占 1 列
        mvwaddwstr(win, row, col2 + 1, L" ");   // 补足到 2 列
    }
}

// ——墙体——
// 选择单元格的主字符（同你原来的 box_char 逻辑）
static const wchar_t* box_char(int x, int y) {
    int u = (x > 0 && wall[x-1][y]) ? 1 : 0;
    int d = (x < MAP_HEIGHT-1 && wall[x+1][y]) ? 1 : 0;
    int l = (y > 0 && wall[x][y-1]) ? 1 : 0;
    int r = (y < MAP_WIDTH-1 && wall[x][y+1]) ? 1 : 0;

    if (u && d && l && r) return L"┼";
    if (u && d && l && !r) return L"┤";
    if (u && d && !l && r) return L"├";
    if (u && !d && l && r) return L"┴";
    if (!u && d && l && r) return L"┬";
    if (u && d && !l && !r) return L"│";
    if (!u && !d && l && r) return L"─";
    if (u && !d && !l && r) return L"└";
    if (u && !d && l && !r) return L"┘";
    if (!u && d && !l && r) return L"┌";
    if (!u && d && l && !r) return L"┐";
    if (u || d) return L"│";
    if (l || r) return L"─";
    return L"█";
}

// 为“每格=2列”做横向补强：若该格右侧有横向连接，就把第二列填 '─'，否则填空格。
// 这样横线能变成“──”，拐角/三通/十字也能把水平方向连续起来。
static void put_wall2(WINDOW *win, int row, int col2, int mx, int my) {
    int r = (my < MAP_WIDTH-1 && wall[mx][my+1]) ? 1 : 0;
    const wchar_t *main = box_char(mx, my);
    // 打第一列：主字符
    mvwaddwstr(win, row, col2, main);
    // 打第二列：若右侧连通就画 '─'，否则留空
    if (r) {
        mvwaddwstr(win, row, col2 + 1, L"─");
    } else {
        mvwaddwstr(win, row, col2 + 1, L" ");
    }
}

void init_ui() {
    // Enable Unicode support for emoji characters
    setlocale(LC_ALL, "");
    initscr();
    noecho();
    cbreak();
    keypad(stdscr, TRUE);
    curs_set(0);
    // Create windows for map, stats, log, and input prompt
    mapWin   = newwin(VIEW_HEIGHT, VIEW_WIDTH, 0, 0);
    statsWin = newwin(VIEW_HEIGHT, STAT_WIDTH, 0, VIEW_WIDTH);
    logWin   = newwin(LOG_LINES, 128, VIEW_HEIGHT, 0);
    inputWin = newwin(1, 512, VIEW_HEIGHT + LOG_LINES, 0);
    // Initial draw of map and stats
    draw_map();
    draw_stats();
    wrefresh(mapWin);
    wrefresh(statsWin);
    // Initialize log buffer
    log_count = 0;
    for(int i = 0; i < LOG_LINES; ++i) {
        log_buffer[i][0] = '\0';
    }
    wrefresh(logWin);
    // Input window will be shown only in debug mode
}

void shutdown_ui() {
    // Destroy windows and end ncurses mode
    delwin(mapWin);
    delwin(statsWin);
    delwin(logWin);
    delwin(inputWin);
    endwin();
}

void draw_map() {
    int view_x = player_x - VIEW_HEIGHT / 2;
    int view_y = player_y - (VIEW_WIDTH / 2 / 2);    // VIEW_WIDTH 是屏幕列数
    if (view_x < 0) view_x = 0;
    if (view_y < 0) view_y = 0;
    if (view_x > MAP_HEIGHT - VIEW_HEIGHT / CELL_W) view_x = MAP_HEIGHT - VIEW_HEIGHT / 2;

    // 逻辑可视列数 = 屏幕列数 / 2
    int view_cols = VIEW_WIDTH / CELL_W ;
    if (view_y > MAP_WIDTH - view_cols) view_y = MAP_WIDTH - view_cols;

    werase(mapWin);

    for (int i = 0; i < VIEW_HEIGHT; ++i) {
        for (int j = 0; j < view_cols; ++j) {
            int mx = view_x + i;
            int my = view_y + j;
            int scr_col = j * CELL_W;

            if (mx < 0 || mx >= MAP_HEIGHT || my < 0 || my >= MAP_WIDTH) {
                mvwaddwstr(mapWin, i, scr_col, L"  ");
                continue;
            }

            if (wall[mx][my]) {
                put_wall2(mapWin, i, scr_col, mx, my);
            } else if (mx == player_x && my == player_y) {
                put_cell2(mapWin, i, scr_col, player->emoji); // 🧙 等 emoji：宽度=2
            } else if (monster_map[mx][my] != NULL) {
                Monster *m = monster_map[mx][my];
                put_cell2(mapWin, i, scr_col, monster_types[m->type].emoji);
            } else {
                // 地面也占 2 列：'.' + ' '（或换成 '· ' 更清晰）
                put_cell2(mapWin, i, scr_col, L".");
            }
        }
    }
    wrefresh(mapWin);
}


// Draw player and pet stats in the side panel
void draw_stats() {
    werase(statsWin);
    // Player stats (top segment)
    mvwaddwstr(statsWin, 0, 0, player->emoji);
    wprintw(statsWin, " %s", player->name);
    mvwprintw(statsWin, 1, 0, "HP: %d/%d", player->currentHP, player->maxHP);
    mvwprintw(statsWin, 2, 0, "ATK: %d", player->atk);
    mvwprintw(statsWin, 3, 0, "DEF: %d", player->def);
    mvwprintw(statsWin, 4, 0, "Potions: %d", player->potions);
    // Pet stats (5 panels of 5 lines each)
    for(int p = 0; p < MAX_PETS; ++p) {
        int line = 5 + p * 5;
        if(p < player->pet_count) {
            Monster *pet = &player->pets[p];
            mvwaddwstr(statsWin, line + 0, 0, monster_types[pet->type].emoji);
            wprintw(statsWin, " Pet%d: %s", p+1, pet->name);
            mvwprintw(statsWin, line + 1, 0, "HP: %d/%d", pet->currentHP, pet->maxHP);
            mvwprintw(statsWin, line + 2, 0, "ATK: %d", pet->atk);
            mvwprintw(statsWin, line + 3, 0, "DEF: %d", pet->def);
            mvwprintw(statsWin, line + 4, 0, "Pos: %d", pet->battle_pos);
        } else {
            // Empty pet slot
            mvwprintw(statsWin, line + 0, 0, "Pet%d: [Empty]", p+1);
            mvwprintw(statsWin, line + 1, 0, " ");
            mvwprintw(statsWin, line + 2, 0, " ");
            mvwprintw(statsWin, line + 3, 0, " ");
            mvwprintw(statsWin, line + 4, 0, " ");
        }
    }
    wrefresh(statsWin);
}

// Update the log window with current log buffer contents
void update_log() {
    werase(logWin);
    int start_line = (log_count < LOG_LINES) ? 0 : log_count - LOG_LINES;
    int line_index = 0;
    for(int i = (start_line < 0 ? 0 : start_line); i < log_count; ++i) {
        mvwprintw(logWin, line_index++, 0, "%s", log_buffer[i % LOG_LINES]);
    }
    wrefresh(logWin);
}

// Clear the log buffer and window
void clear_log() {
    log_count = 0;
    for(int i = 0; i < LOG_LINES; ++i) {
        log_buffer[i][0] = '\0';
    }
    werase(logWin);
    wrefresh(logWin);
}

// Add a formatted message to the log buffer
void add_log(const char *format, ...) {
    char buf[1024];
    va_list args;
    va_start(args, format);
    vsnprintf(buf, sizeof(buf), format, args);
    va_end(args);
    // Append new message to log buffer (keep last LOG_LINES messages)
    if(log_count < LOG_LINES) {
        strcpy(log_buffer[log_count], buf);
        log_count++;
    } else {
        // Shift buffer up by one
        for(int i = 1; i < LOG_LINES; ++i) {
            strcpy(log_buffer[i-1], log_buffer[i]);
        }
        strcpy(log_buffer[LOG_LINES-1], buf);
        log_count = LOG_LINES;
    }
    update_log();
}
