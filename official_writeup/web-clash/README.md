# [Web] 提权潜兵 · 新指导版

- 命题人：xmcp
- 清凉：200 分
- 炽热：300 分

## 题目描述

<div class="cow-container">
<p>你好啊，这关需要在 Linux 系统上从普通用户获取 root 权限，我来协助你提权。</p>
<p>我先问一下，你是不是第一次听说 <strong>Clash Verge Rev 的提权漏洞</strong>？
<span class="cow-asker">
<input type="radio" name="cow-asker-1" id="cow-asker-1-1" value="1"><label for="cow-asker-1-1">是</label><span>我估计你也不知道啥是 Clash Verge Rev，不过没事，这关我们用 FlClash。</span>
&ensp;
<input type="radio" name="cow-asker-1" id="cow-asker-1-2" value="2"><label for="cow-asker-1-2">否</label><span>那你是高手啊，用老漏洞没意思，我帮你把软件换成 FlClash。</span>
&ensp;
</span></p>
<p>欸，Linux 系统里普通用户叫啥名字来着？
<span class="cow-asker">
<input type="radio" name="cow-asker-2" id="cow-asker-2-1" value="1"><label for="cow-asker-2-1">ubuntu</label><span>这什么单词啊，没听说过。</span>
&ensp;
<input type="radio" name="cow-asker-2" id="cow-asker-2-2" value="2"><label for="cow-asker-2-2">nobody</label><span>说得太对了，这就是你待会要用的用户。</span>
&ensp;
</span></p>
<p>关卡会运行一个<strong>后台服务</strong>，不信你用 <code>ps -ef</code> 看一下。后台服务可以启动 Clash 内核。</p>
<p>我弄了个 Flag，免费帮你放在了 <code>/root</code> 目录。</p>
<p>我帮你给 FlClash 升级。
<span class="cow-asker">
<input type="radio" name="cow-asker-3" id="cow-asker-3-1" value="1"><label for="cow-asker-3-1">是</label><span>↑ v0.8.90</span>
&ensp;
<input type="radio" name="cow-asker-3" id="cow-asker-3-2" value="2"><label for="cow-asker-3-2">否</label><span>由不得你。</span>
&ensp;
</span></p>
<p>本关你没有读取 <code>/root</code> 的权限，这就意味着需要<strong>找到程序里的漏洞来提权</strong>。</p>
<p>对了，我知道 FlClash 有一个漏洞，要听吗？
<span class="cow-asker">
<input type="radio" name="cow-asker-4" id="cow-asker-4-1" value="1"><label for="cow-asker-4-1">是</label><span>我把漏洞原因写在题目源码的 fix.patch 补丁里了。哦对，我还帮你把补丁打上去了（限 Flag 2）。</span>
&ensp;
<input type="radio" name="cow-asker-4" id="cow-asker-4-2" value="2"><label for="cow-asker-4-2">否</label><span>你已经知道了啊，那我寻思你也用不上，直接帮你修了（限 Flag 2）。</span>
&ensp;
</span></p>
<p>为了方便从网上下载利用脚本，我帮你装 Python 和 requests。
<span class="cow-asker">
<input type="radio" name="cow-asker-5" id="cow-asker-5-1" value="1"><label for="cow-asker-5-1">是</label><span>安装成功。忘记说了，题目环境并没有网。</span>
&ensp;
<input type="radio" name="cow-asker-5" id="cow-asker-5-2" value="2"><label for="cow-asker-5-2">否</label><span>确实不用装，因为题目环境里已经有了。</span>
&ensp;
</span></p>
<p>我饿了，我把 Flag 文件名改成随机的尝尝咸淡。 </p>
<p>对了，我还知道 FlClash 有另一个漏洞，要听吗？
<span class="cow-asker">
<input type="radio" name="cow-asker-6" id="cow-asker-6-1" value="1"><label for="cow-asker-6-1">是</label><span>好，我写在出题人 Writeup 里了，比赛结束之后就可以看。</span>
&ensp;
<input type="radio" name="cow-asker-6" id="cow-asker-6-2" value="2"><label for="cow-asker-6-2">否</label><span>真没劲呐。</span>
&ensp;
</span></p>
<p>我帮你删除 Fla……
<span class="cow-asker">
<input type="radio" name="cow-asker-7" id="cow-asker-7-1" value="1"><label for="cow-asker-7-1">接招 ↑→↓↓↓</label><span>🚀💣💥 AUV!</span>
&ensp;
</span></p>
</div>
<p><small><em>光敏性癫痫警告：请不要在本页面按 ↑→↓↓↓</em></small></p>
<div class="well">
<p><strong>第二阶段提示：</strong></p>
<ul>
<li>Flag 1：指导在哪里？<a target="_blank" rel="noopener noreferrer" href="https://github.com/chen08209/FlClash/issues/1131#issuecomment-2848721177">指导在这里。</a></li>
<li>Flag 2：Clash Core 的 <code>external-controller</code> 提供了更多功能。比如，可以更改设置，然后通过 <code>/upgrade/ui</code> 替换掉 <code>/root/secure/FlClashCore</code> 文件。</li>
</ul>
</div>

**[【附件：下载题目源码（web-clash-src.7z）】](attachment/web-clash-src.7z)**

**【终端交互：连接到题目（Flag 1）】**

**【终端交互：连接到题目（Flag 2）】**

## 预期解法

### Flag 1

这个Flag 1给了patch作为提示。直接看一看，发现FlClash有一个helper程序，它监听了47889端口，可以运行任意程序，但是它会首先检测程序的SHA256与白名单是否相符。

但这种检查是无效的，因为攻击者完全可以在检测之后、运行之前替换程序内容，从而绕过白名单。这类问题被称为[TOCTOU](https://en.wikipedia.org/wiki/Time-of-check_to_time-of-use)。

所以exp就比较好写了：

- 首先调用 `http://127.0.0.1:47890/start`启动一个SHA256正确的程序。
- 然后不等请求完成，稍微sleep一会（等它读完文件），把程序替换成`/bin/sh`的内容。
- 然后helper就会运行`/bin/sh`，甚至还可以带一个参数来执行shell脚本，非常贴心。

可喜可贺。脚本详见[exp_flag1.py](sol/exp_flag1.py)。

另外有人可能会尝试用符号链接实现快速替换文件，然后发现/tmp下带符号链接的程序root执行不了。这是[Linux的一个安全机制](https://sysctl-explorer.net/fs/protected_symlinks/)，但是对此题来说不影响我们直接替换文件内容，只要速度足够快就行。如果怕写入文件不够快，直接准备两个版本的文件然后到时候直接重命名也可以。

### Flag 2

打了补丁之后，启动什么程序不再能控制了。我们还剩下的功能就是可以与启动的Clash内核通过socket交互。

这个Clash内核是FlClash修改版的，在原版基础上[增加了一些新的接口](https://github.com/chen08209/FlClash/blob/45b163184d87f5591602d2995f557ba972bb5097/core/action.go#L40-L189)，而且完全没做鉴权。有些接口看起来还挺危险的，比如deleteFile，但是这对我们拿Flag好像没什么帮助。我们需要的是以下三种功能之一：

- 能读取文件和列出目录，这样我们就能读到Flag
- 能运行程序，这样我们就能写个脚本来读Flag
- 能写入文件并设置setuid位，这样我们可以往/tmp里面放一个setuid的程序来读Flag
- 能写入文件，这样我们就能把`/root/secure/FlClashCore`替换掉，然后用它的helper启动我们写的脚本来读Flag

前两个好像不容易找到相关功能。

第三个曾经是可以用解压zip来做到的，但是这点被R3CTF考过，然后在最新版的Clash内核里就[被修了](https://github.com/chen08209/Clash.Meta/commit/63ad95e10f40ffc90ec93497aac562765af7a471)。

第四个比较好实现，比如Clash配置中的`external-ui-url`字段可以放一个zip，然后调用`/upgrade/ui`就会把zip的内容解压到`external-ui`目录下面的`external-ui-name`子目录。顺便Clash内核关于写入文件的路径也有强化过的检查，试一试就会发现，如果要写入到的目录[不在事先设置的SafePath里](https://github.com/chen08209/Clash.Meta/blob/96d1a49e5460f78b9b2b7b7b8bc493d9ff4c52ff/constant/path.go#L87-L100)（默认为Clash的HomeDir）就会直接报错。

但一个安全的内核拯救不了草台的FlClash：FlClash增加的`initClash`命令[恰巧允许我们随意设置HomeDir](https://github.com/chen08209/FlClash/blob/d3c3f040626e9b184f8ee7a86df344d036f88f7d/core/hub.go#L47)。这样攻击链就呼之欲出了：

- 调用`http://127.0.0.1:47890/start`启动内核，用socket连接上内核
- 用`initClash`命令把HomeDir设置成`/`绕过后续的路径检查
- 用`updateConfig`命令开启Clash原生的JSON RPC（`external-controller`），因为`updateConfig`只能改有限的配置，没有我们需要的`external-ui`系列配置
- 通过上一步打开的JSON RPC提供的`/configs`接口更改设置，把`external-ui`设为`/root`，把`external-ui-name`设为`secure`，把`external-ui-url`设为一个我们可以控制的HTTP服务器
- 继续调用JSON RPC的`/upgrade/ui`接口，触发强制更新
- 然后内核就会请求这个HTTP服务器，我们返回一个包含替换后的FlClashCore文件的压缩包，然后它就会替换掉`/root/secure/FlClashCore`
- 最后调用一下`http://127.0.0.1:47890/start`重启内核，就能执行我们的命令了

看起来挺复杂，但实际上全都是围绕着`external-ui-url`这个能写入文件的功能来布置的。建议在做题的时候弄个全自动的exp脚本，然后把log level开大一点，这样可以看到没成功的点是在哪里出错的，然后针对出错来完善exp。

最终的脚本详见[exp_flag2.py](sol/exp_flag2.py)。