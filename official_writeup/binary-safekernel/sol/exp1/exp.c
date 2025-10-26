#include <unistd.h>
#include <fcntl.h>

int main(void)
{
	int buf[32];
	read(open("/flag1.txt", O_RDONLY), buf, sizeof(buf));
	write(STDOUT_FILENO, buf, sizeof(buf));

	return 0;
}
