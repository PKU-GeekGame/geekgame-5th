# GeekGame 2025 Writeup

License: [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/deed.zh-hans)

## 前言

又是新的一年，这是我参加的第三次 GeekGame，题目依旧有趣。依旧感谢 staff 的付出。本届官方 [资料存档](https://github.com/PKU-GeekGame/geekgame-5th) 会有更详细的解法。本 WP 只讲一下利用 trace 工具的「枚举高手的 bomblab 审判」的轮椅解法。

## 枚举高手的 bomblab 审判

展示一下 trace 家族魅力时刻：

**第一个问题：程序的反调试咋实现的？**

```sh
undef@undefbaka ~/ctf> strace ./binary-ffi
……
openat(AT_FDCWD, "/proc/self/status", O_RDONLY) = 3
newfstatat(3, "", {st_mode=S_IFREG|0444, st_size=0, ...}, AT_EMPTY_PATH) = 0
read(3, "Name:\tbinary-ffi\nUmask:\t0022\nSta"..., 1024) = 1024
close(3)                                = 0
exit(0)                                 = ?
+++ exited with 0 +++
```

截取了一下，不过一共输出也就六十多行，全部丢给 GPT 就会告诉你：

> 关键点分析
>
> 1️⃣ 打开 `/proc/self/status`
>
> `openat(AT_FDCWD, "/proc/self/status", O_RDONLY) = 3`
>
> `read(3, "Name:\tbinary-ffi\nUmask:\t0022\nSta"..., 1024) = 1024`
>
> **这是非常典型的反调试检测方式之一。**
>
> 在 Linux 下，每个进程都有 `/proc/self/status` 文件，其中有一行：
>
> `TracerPid: 0`
>
> 如果该进程被 ptrace（例如通过 gdb、strace、ltrace 等）跟踪，这个字段会变成：
>
> `TracerPid: <调试器的 PID>`
>
> 因此，程序可以通过读取 `/proc/self/status` 并查找 `TracerPid:` 行来判断自己是否被调试。

那其实思路就打开了：

1. 因为是启动时检测，我们可以在程序加载后再用 gdb attach 上去；
2. 也可以直接修改二进制，把检测部分替换掉；
3. 也可以用 `LD_PRELOAD` 劫持 `open` 或 `read` 函数。

这里我们直接把二进制里的 `/proc/self/status` 替换成 `a\x00` 就过了。其实本来以为它要检测文件里的 `TracePid` 为 0 才能通过，结果连文件内容都不用伪造就过了。

**第二个问题：程序的动态行为？**

那其实这也有很多思路：

1. 逆向程序逻辑；
2. gdb 动态调试。

这里我们一个也不用，我们用 trace 家族的 ltrace 来动态观察程序调用的库函数。直接跑一遍：

```sh
undef@undefbaka ~/ctf> ltrace ./binary-ffi
mprotect(0x55aaa872c000, 1699, 7, 1)                                      = 0
mprotect(0x55aaa872c000, 1699, 5, 1)                                      = 0
fopen("p", "r")                                                           = 0
puts("Enter your flag:"Enter your flag:
)                                                  = 17
fflush(0x7fc8d91a8780)                                                    = 0
fgets(123
"123\n", 256, 0x7fc8d91a7aa0)                                       = 0x55aaa872f060
strlen("123\n")                                                           = 4
strlen("in1T_Arr@y_1S_s0_E@sy")                                           = 21
strlen("flag{iN1T_ARR@Y_W1TH_Smc_@NTI_db"...)                             = 45
strlen("in1T_Arr@y_1S_s0_E@sy")                                           = 21
strlen("123")                                                             = 3
strlen("in1T_Arr@y_1S_s0_E@sy")                                           = 21
strcmp("1e08823348a0e1342898f036027c51f6"..., "b07110")                   = -49
strlen("123")                                                             = 3
puts("Incorrect!"Incorrect!
)                                                        = 11
+++ exited (status 0) +++
```

**可以发现 flag1 直接出了**。flag2 其实也有提示，注意到这里我们输入了 `123`，然后程序里有一段 `strcmp` 比较了两个字符串，一个是 `1e08823348a0e1342898f036027c51f6`，另一个是 `b07110`。很明显我们输入了三个字符，第二个字符串恰好是三个字节的十六进制表示。我们直接乱搞，输入 `flag{test}`，然后观察 `strcmp` 的结果：

```sh
fgets(flag{test}
"flag{test}\n", 256, 0x7f4b4e0b0aa0)                                = 
……
strcmp("1e08823348a0e1342898f036027c51f6"..., "1e08823348d4b8106810")     = -3
```

结果非常的 amazing 啊，**前五个字节直接匹配上了！那我们每次继续爆破一个字节就可以了**。脚本略。还真的就是枚举上了。这里要注意用 `ltrace -s 100 ./binary-ffi` 来调整一下上面打印字符串的长度限制，不然会被截断。