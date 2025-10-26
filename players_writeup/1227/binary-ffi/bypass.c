#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>
#include <unistd.h> // <-- 修复: 添加此头文件以使用 dprintf

// 文件读取的“状态”
static int status_index = 0;
static FILE *fake_proc_file = NULL;

// 1. 劫持 fopen
FILE *fopen(const char *pathname, const char *mode) {
    // 强制加载原始的 fopen 函数
    static FILE *(*original_fopen)(const char *, const char *) = NULL;
    if (!original_fopen) {
        original_fopen = (FILE *(*)(const char *, const char *))dlsym(RTLD_NEXT, "fopen");
    }

    // 检查是否在尝试打开 /proc/self/status
    if (strstr(pathname, "/proc/self/status")) {
        // 创建一个假的 FILE 结构体，用于标记和识别
        fake_proc_file = (FILE *)malloc(sizeof(FILE));
        // 使用 dprintf 绕过对全局 stderr 的依赖
        dprintf(2, "[LD_PRELOAD] Bypassed fopen for: %s\n", pathname); 
        // 重置状态索引，准备从头开始提供伪造内容
        status_index = 0; 
        return fake_proc_file;
    }

    // 调用原始的 fopen
    return original_fopen(pathname, mode);
}

// 2. 劫持 fgets
char *fgets(char *s, int size, FILE *stream) {
    // 强制加载原始的 fgets 函数
    static char *(*original_fgets)(char *, int, FILE *) = NULL;
    if (!original_fgets) {
        original_fgets = (char *(*)(char *, int, FILE *))dlsym(RTLD_NEXT, "fgets");
    }

    // 检查是否是我们在上面返回的假文件句柄
    if (stream == fake_proc_file) {
        const char *line_start = NULL;
        
        // 模拟按行读取
        switch (status_index) {
            case 0: line_start = "Name: binary-ffi\n"; break;
            case 1: line_start = "State: S (sleeping)\n"; break;
            case 2: line_start = "TracerPid:\t0\n"; break; // 关键行：TracerPid 设置为 0
            case 3: line_start = "Pid: 12345\n"; break;
            default:
                // 文件结束
                dprintf(2, "[LD_PRELOAD] Reached Bypassed EOF.\n"); // 使用 dprintf 
                return NULL;
        }

        // 复制内容到用户缓冲区
        strncpy(s, line_start, size - 1);
        s[size - 1] = '\0'; // 确保字符串以 \0 结束
        status_index++;
        return s;
    }

    // 调用原始的 fgets
    return original_fgets(s, size, stream);
}

// 3. 劫持 fclose
int fclose(FILE *fp) {
    // 强制加载原始的 fclose 函数
    static int (*original_fclose)(FILE *) = NULL;
    if (!original_fclose) {
        original_fclose = (int (*)(FILE *))dlsym(RTLD_NEXT, "fclose");
    }

    if (fp == fake_proc_file) {
        dprintf(2, "[LD_PRELOAD] Bypassed fclose.\n"); // 使用 dprintf
        free(fake_proc_file);
        fake_proc_file = NULL;
        return 0; // 成功关闭
    }

    return original_fclose(fp);
}