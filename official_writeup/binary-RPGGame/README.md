# [Binary] RPGGame

- 命题人：k4ra5u
- CLI：250 分
- TUI：400 分

## 题目描述

<p>命令行游戏里一定要有图形化！！！✋😭🤚✋😭🤚✍✍✍✍✍✍✍✍</p>
<p>请找出 GM 留下的后门并利用漏洞，获取文件系统中的 <code>/flag</code>。</p>
<div class="well">
<p><strong>界面操作说明：</strong></p>
<p>RPGGame（TUI）程序通过 <code>ncurses</code> 绘制用户界面，直接用 nc 连接会出现乱码，无法正常使用。在一个完整的 Linux 终端中输入以下命令可以连接到题目并正确显示用户界面：</p>
<p><code>stty raw -echo; nc prob17.geekgame.pku.edu.cn 10017</code></p>
<p>要求输入 Token 时，<strong>粘贴你的 Token（不会回显到屏幕上）然后按 Ctrl+J</strong>。程序退出后 <code>nc</code> 可能不会退出，终端操作可能也会变得奇怪。非常遗憾，建议直接重开终端解决。</p>
<p>网页终端已经进行了上述操作，而且会自动输入 Token，无需额外配置。但作为 Pwn 题，你显然无法全程使用网页终端解题。</p>
</div>
<p><strong>补充说明：</strong> 补充了关于题目环境的附件。题目的 GLIBC 版本为 2.39-0ubuntu8.5，Docker image digest 为 e0f16e6366fef4e695b9f8788819849d265cde40eb84300c0147a6e5261d2750。</p>
<div class="well">
<p><strong>第二阶段提示：</strong></p>
<ul>
<li>flag1使用到的2个可用gadgets，第一个gadget可以控制rax，第二个gadget可以调用puts并回到主程序逻辑：<ul>
<li><code>0x00000000004011a8 : pop rax ; add dil, dil ; loopne 0x401215 ; nop ; ret</code></li>
<li><code>0x00000000004014bb : mov rdi, rax ; call _puts ; jmp short loc_4014E5 ; jmp short loc_40130A ; ...</code></li>
</ul>
</li>
<li>flag2存在3个漏洞：<ol>
<li><code>string_action</code>中<code>add_log</code>函数存在格式化字符串，只要是debug命令下name相关的参数都会触发</li>
<li><code>init_commands</code>函数中构建的树形图存在环路，free id &lt;num&gt; 后可以接 {name &lt;string&gt;} 无限循环</li>
<li><code>handle_tab</code>函数存在堆溢出漏洞，重合大于2个字符的情况下可以通过tab补全命令，此时没有做边界检查，会造成堆溢出</li>
</ol>
</li>
<li>flag2简要利用概述：<ol>
<li>角色10级之后才能打败隐藏boss，此前需要玩家自己玩/利用catch后怪不会消失机制刷怪</li>
<li>击败隐藏boss后获得给宠物改名的能力，名字最多127字节，考虑到最多抓5个宠物，足以实现堆溢出</li>
<li>堆溢出后直接覆盖命令树中的pfn，即可获得shell</li>
<li>注意某些转义字符会导致命令/连接断开：<code># 0x3 0x8 0x9 0xa 0xd 0x11 0x13 0x1a 0x1c 0x7f</code>,利用时出现这些字符建议重开</li>
</ol>
</li>
<li>提供一个同时自己玩+脚本自动化的方法：<ol>
<li>tmux启动一个执行socat的窗口：<code>tmux new-session -s rpg -d -x 220 -y 48 "socat -,raw,echo=0,cs8,parenb=0,istrip=0 TCP:prob17.geekgame.pku.edu.cn:10017" ; tmux attach -t rpg</code></li>
<li>将 rpg会话的输出内容实时保存到日志文件：<code>tmux pipe-pane -o -t rpg:0.0 'cat &gt; /tmp/rpg_screen.log'</code>,</li>
<li>python交互函数：</li>
</ol>
</li>
</ul>
<div class="codehilite" style="background: #f8f8f8"><pre style="line-height: 125%;"><span></span><code><span style="color: #008000; font-weight: bold">def</span><span style="color: #BBB"> </span><span style="color: #00F">tmux_send_bytes</span>( data: <span style="color: #008000">bytes</span>, bufname<span style="color: #666">=</span><span style="color: #BA2121">&#39;injbuf&#39;</span>):
    <span style="color: #3D7B7B; font-style: italic"># 把 data（二进制，允许 \x00）注入 pane</span>
    p <span style="color: #666">=</span> subprocess<span style="color: #666">.</span>Popen([<span style="color: #BA2121">&#39;tmux&#39;</span>, <span style="color: #BA2121">&#39;load-buffer&#39;</span>, <span style="color: #BA2121">&#39;-b&#39;</span>, bufname, <span style="color: #BA2121">&#39;-&#39;</span>],
                         stdin<span style="color: #666">=</span>subprocess<span style="color: #666">.</span>PIPE)
    p<span style="color: #666">.</span>communicate(data)     <span style="color: #3D7B7B; font-style: italic"># data 可以包含 \x00</span>
    subprocess<span style="color: #666">.</span>run([<span style="color: #BA2121">&#39;tmux&#39;</span>, <span style="color: #BA2121">&#39;paste-buffer&#39;</span>, <span style="color: #BA2121">&#39;-t&#39;</span>, <span style="color: #BA2121">&#39;rpg:0.0&#39;</span>, <span style="color: #BA2121">&#39;-b&#39;</span>, bufname],
                   check<span style="color: #666">=</span><span style="color: #008000; font-weight: bold">True</span>)
</code></pre></div>

</div>

**[【附件：下载题目附件（binary-RPGGame.zip）】](attachment/binary-RPGGame.zip)**

**[【附件：下载题目环境补充附件（binary-RPGGame-env.zip）】](attachment/binary-RPGGame-env.zip)**

**【终端交互：连接到 RPGGame（CLI）】**

**【终端交互：连接到 RPGGame（TUI）】**

## 预期解法

### flag1
- 本题模拟了RPGGame里创建角色的部分，创建角色成功后反馈结果，并退出程序。
- 题目中预置了2个漏洞，一个是当用户名为designer时，会触发到密码验证的逻辑，另一个漏洞是当选手猜对了designer的密码后，会给一个由于整数溢出而导致的栈溢出。
- 对于第一个漏洞，可以发现密码长度固定为0x10，当密码存在不正确的位时，会输出：`Wrong Password!`和`Password Invalid!`，当密码部分正确，但没有达到16个字节时，只会输出：`Password Invalid!`，通过此测信道可以完整的爆破出全部的16字节密码，并通过整形溢出做栈溢出。
- 对于后续的利用，本题特意控制代码长度，保证无法通过常规的`pop rdi`的形式进行漏洞利用，我们使用ROPGadget工具并用depth指定探索深度：` ROPgadget --binary ./pwn --depth=50  > rop.txt` ,发现只有2个pop指令：`pop rax`和`pop rbp`,rbp不需要pop直接可用，rax可控后，我们发现程序逻辑里调用puts都是通过mov rdi, rax的形式进行调用的，因此我们控制puts的参数，从而泄露libc地址，计算出system和/bin/sh的地址后，再次利用栈溢出调用system("/bin/sh")即可获得shell。
### flag2
#### 游戏概述
- flag2是模拟了一个TUI的升级打怪游戏，每次启动会随机生成一个40*60的游戏地图，玩家操控小人上下左右来战斗、升级、打Boss（以防大家没看到Boss，人家在地图右下角，游戏视角会随主角移动）。
- 简单对程序进行逆向分析会发现，除了上下左右打怪外，游戏可以通过debug模式解锁更细粒度战斗操作和宠物玩法。主角在战斗状态下，可以通过catch指令抓怪物当宠物。出战的宠物可以和主角一起攻击或帮主角挡刀。主角在探索状态下，可以通过move命令簇进行移动，通过pet命令簇进行宠物管理，通过heal命令来给自己或宠物回血，更多关于宠物的操作请看源码或自己玩玩。另外战斗状态下还可以通过skip命令来跳过某一个现阶段很强力打不过的怪。
- debug模式的命令是通过命令树来实现的，这是一个兄弟儿子表示法的树形结构，每个节点包含节点属性（keyword，数字，字符串，eol等），对节点属性的检查函数，下一个可接受的节点，以及可以替代的下一个参数。init_commands函数中完成了对整个命令树的构建。keyword和string节点还有一个mini_match参数，这是用来做自动补全的最小匹配长度，比如有个宠物名字叫 BLABLABLA，`pet bring name BLABLABLA 1`可以简写成`pet br<TAB> na<TAB> BL<TAB> 1`。
- 出生点门口有一个血牛隐藏boss:???，10级之后可以打败它，并获得改名的能力。
#### 漏洞分析
经过分析，程序中存在3（4）个漏洞：
1. 格式化字符串：`string_action`函数存在格式化字符串。只要是debug命令下name相关的参数在进行tab补全或者回车输入时，都会使用`string_action`函数来进行参数格式检查，并触发该漏洞。
2. 命令树环路：`init_commands` 函数中构建的树形图存在环路，`free id <num>` 后可以接 `name <string>` 无限循环，因此可以写出超长命令。
3. 堆溢出：debug模式下的输入框是malloc的512字节空间，正常输入会严格限制在512字节内，`handle_tab`函数可以通过tab补全命令突破边界检查，会造成堆溢出。
4. 怪物被catch后不会消失：实现过程中产生的bug，会导致角色可以反复抓怪，并吃经验升级。然而自己做题的时候发现，封堵这个bug后，会导致每次漏洞利用都要非常极限操作来打怪到10级。为了方便选手进行调试 ~~（避免被选手亲切问候）~~ ，在题目环境中保留了这个bug。

#### 利用思路
1. 格式化字符串 可以使用`%43$p`和`%45$p`来精准泄露debug命令的堆地址和`__libc_start_call_main`的地址，并计算出system和`/bin/sh`的地址。
2. 刷怪到10级，并打败隐藏boss，获得给宠物改名的能力。
3. 随便抓5个宠物，将其命名为前缀不同的名字，然后通过`pet free name <name1> name <name2> name <name3> name <name4> name <name5>`的形式，精准计算好偏移后，使用TAB对name5补全，可以覆盖命令树中的pfn指针，回车完成漏洞利用。