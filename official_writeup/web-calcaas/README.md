# [Web] 小北的计算器

- 命题人：thezzisu
- 题目分值：350 分

## 题目描述

<p>小北在学习编译原理和 JavaScript 后实现了一个简单的计算器。</p>
<p>宁能攻破它，读取文件系统里的 <code>/flag</code> 吗？</p>
<p><strong>提示：</strong></p>
<ul>
<li>最终目标是执行 <code>Deno.readTextFileSync('/flag')</code> 并拿到返回值。</li>
<li>为了执行它，你需要在程序的限制内拿到一个类似于 <code>eval</code> 的可以执行代码的方法，代码也需要处理以满足限制。</li>
<li>为了拿到返回值，你可以多次与网页交互，把返回值输出到后续的响应中。比如这样：<code>Error.prototype.toString = function() { return Deno.readTextFileSync('/flag') }</code>。</li>
<li>为方便调试，此题的源码及线上环境进行了一些更新。不满足限制时会具体输出违反了哪条规则。</li>
</ul>
<div class="well">
<p><strong>第二阶段提示：</strong></p>
<ul>
<li>看看 <a target="_blank" rel="noopener noreferrer" href="https://eslint.org/docs/latest/rules/no-implied-eval">参考文献</a>。</li>
<li>正则表达式 <code>/xyz/</code> 可以隐式转换成字符串 <code>"/xyz/"</code>。你需要想办法：(1) 让前后的 <code>/</code> 不影响代码运行；(2) 将正则表达式内部出现的违反白名单的字符转义掉。</li>
</ul>
</div>

**【网页链接：访问题目网页】**

**[【附件：下载题目源码（web-calcaas-src.zip）】](attachment/web-calcaas-src.zip)**

## 预期解法

TODO