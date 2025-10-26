#ifndef COMMANDS_H
#define COMMANDS_H

void init_commands();
void process_input_command(char *input);
int handle_tab(char *buf, int buf_sz, int cur_pos);

#endif
