#include<stdio.h>
#include<string.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>
#include <time.h>
#include <stdbool.h>
//gcc yichu.c -o yichu -no-pie -fno-stack-protector
void initt()
	{
		setvbuf(stdin, 0LL, 1, 0LL);
		setvbuf(stdout, 0LL, 2, 0LL);
		return setvbuf(stderr, 0LL, 1, 0LL);
	}
void pwnn()
	{
        char password[16];
        char buf[64];
		char name[64];
        int size;
        FILE *fp = fopen("/dev/urandom", "r");
        if (fp == NULL) {
            puts("Failed to open /dev/urandom");
            return;
        }
        fread(password, 1, sizeof(password) , fp);
        fclose(fp);
        while(true) {
            puts("Please login to the Game World!!!");
            puts(">");
            read(0,name,0x40);
            puts("Please input your password:");
            puts(">");
            int s = read(0,buf,0x10);
            if(!strncmp(name,"designer",8)) {
                int i = 0;
                for(i= 0; i < s; i++) {
                    if(buf[i] != password[i]) {
                        puts("Wrong Password!");
                        break;
                    }
                }
                if(i == 16) {
                    puts("Welcome to the RPG game!");
                    puts("Please input the size of your payload:");
                    puts(">");
                    read(0, buf,0x10);
                    size = atoi(buf);
                    if(size >=64) {
                        puts("Size too large!");
                        continue;
                    }
                    memset(buf, 0, sizeof(buf));
                    puts("Please input your payload:");
                    puts(">");
                    read(0, buf, (uint32_t)(size));
                    // read(0, buf, size);
                    puts("Bye!");
                    return;
                    
                } else {
                    puts("Password Invalid!");
                    continue;
                }
            } else {
                puts("Welcome to the RPG game!");
                puts("Enjoy yourself!");
                break;
            }

        }
        
	}
int main()
{
	initt();
	pwnn();

}
