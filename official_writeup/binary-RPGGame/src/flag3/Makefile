CC = gcc
CFLAGS = -Wall -Wextra -std=c11 -pedantic -g
# 开启宽字符支持
CPPFLAGS = -D_XOPEN_SOURCE_EXTENDED
# 关键：链接 ncursesw（不是 ncurses）
LDFLAGS = -lncursesw

OBJ = main.o game.o battle.o ui.o commands.o

rpg_game: $(OBJ)
	$(CC) $(OBJ) -o rpg_game $(LDFLAGS)

%.o: %.c
	$(CC) $(CFLAGS) $(CPPFLAGS) -c $< -o $@

clean:
	rm -f $(OBJ) rpg_game
