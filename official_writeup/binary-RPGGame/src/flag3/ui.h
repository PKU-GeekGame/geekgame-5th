#ifndef UI_H
#define UI_H

#include <ncurses.h>

extern WINDOW *mapWin;
extern WINDOW *statsWin;
extern WINDOW *logWin;
extern WINDOW *inputWin;

// UI initialization and teardown
void init_ui();
void shutdown_ui();

void redraw_all();        // 强制整套 UI 立即重绘

// UI update functions
void draw_map();
void draw_stats();
void update_log();
void clear_log();
void add_log(const char *format, ...);

#endif
