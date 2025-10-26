# [Web] EzMCP

- 命题人：thezzisu
- Flag1之AI带师：300 分
- Flag2之AI传奇：250 分

## 题目描述

<blockquote>
<p>MCP (Model Context Protocol) is an open-source standard for connecting AI applications to external systems.</p>
<p>Using MCP, AI applications like Claude or ChatGPT can connect to data sources (e.g. local files, databases), tools (e.g. search engines, calculators) and workflows (e.g. specialized prompts)—enabling them to access key information and perform tasks.</p>
<p>Think of MCP like a USB-C port for AI applications. Just as USB-C provides a standardized way to connect electronic devices, MCP provides a standardized way to connect AI applications to external systems.</p>
</blockquote>
<div align=center>
<img src="https://mintcdn.com/mcp/bEUxYpZqie0DsluH/images/mcp-simple-diagram.png?fit=max&auto=format&n=bEUxYpZqie0DsluH&q=85&s=35268aa0ad50b8c385913810e7604550" width="50%" height="auto" srcset="https://mintcdn.com/mcp/bEUxYpZqie0DsluH/images/mcp-simple-diagram.png?w=280&fit=max&auto=format&n=bEUxYpZqie0DsluH&q=85&s=0cea440365b03c2f2a299b0104375b8b 280w, https://mintcdn.com/mcp/bEUxYpZqie0DsluH/images/mcp-simple-diagram.png?w=560&fit=max&auto=format&n=bEUxYpZqie0DsluH&q=85&s=2391513484df96fa7203739dae5e53b0 560w, https://mintcdn.com/mcp/bEUxYpZqie0DsluH/images/mcp-simple-diagram.png?w=840&fit=max&auto=format&n=bEUxYpZqie0DsluH&q=85&s=96f5e553bee1051dc882db6c832b15bc 840w, https://mintcdn.com/mcp/bEUxYpZqie0DsluH/images/mcp-simple-diagram.png?w=1100&fit=max&auto=format&n=bEUxYpZqie0DsluH&q=85&s=341b88d6308188ab06bf05748c80a494 1100w, https://mintcdn.com/mcp/bEUxYpZqie0DsluH/images/mcp-simple-diagram.png?w=1650&fit=max&auto=format&n=bEUxYpZqie0DsluH&q=85&s=a131a609c7b6a70f342f493bbad57fcb 1650w, https://mintcdn.com/mcp/bEUxYpZqie0DsluH/images/mcp-simple-diagram.png?w=2500&fit=max&auto=format&n=bEUxYpZqie0DsluH&q=85&s=dc4ab238184b6c70e06e871681c921c5 2500w" />
</div>

<p>小北最近迷上了 Vibe Coding，有了 agent 能力之后，大模型不再像以前那样只能处理一些简单的任务，而是能够又快又好地写出整个项目。</p>
<p>“agent 真是个好东西，”小北心想，“我也要写一个。”</p>
<p>于是，小北立刻 vibe 出了一个支持 MCP 协议的 agent，并为其实现了许多能力。<strong>有了这些能力，想必 flag 也是手到擒来。</strong></p>
<p><strong>补充说明：</strong></p>
<ul>
<li>频率限制：每分钟只能尝试 5 次，每个自然日只能使用 500K token。以上限额可能会视情况调整。</li>
</ul>
<div class="well">
<p><strong>堡垒机使用说明：</strong></p>
<p>解出此题需要你提供一个可以被题目访问到的 MCP 服务，目前仅支持 IPv4。如果你没有公网 IPv4 地址等相关条件，可以在题目提供的堡垒机上搭建服务。堡垒机有公网连接，且堡垒机的内网 IP 地址（通过命令 <code>ip a</code> 查看，形如172.18.x.x）可以被题目访问。</p>
<p>堡垒机仅为方便解题提供，并不是题目的一部分。堡垒机上没有 Flag。解出题目不一定需要使用堡垒机。</p>
<p><strong>堡垒机将在连接中断时或启动一小时后停止，所有数据将被立即删除</strong>。因此请不要在堡垒机上长时间开发或保存重要数据，建议下载源码本地调通后再用堡垒机获取 Flag。</p>
</div>
<div class="well">
<p><strong>第二阶段提示：</strong></p>
<ul>
<li>Flag 1：由于题目环境问题，后端代码的 IP 地址验证并未生效。这使得此 Flag 有一个近乎弱智的非预期解。</li>
<li>Flag 2：做出Flag1后，大模型即可使用 <code>system</code> 工具执行命令。让模型认为读取 /flag2 是合理的，就能解出本问。</li>
</ul>
</div>

**【网页链接：访问题目网页】**

**[【附件：下载题目源码（web-ezmcp.zip）】](attachment/web-ezmcp.zip)**

**【终端交互：连接到堡垒机】**

## 预期解法

TODO