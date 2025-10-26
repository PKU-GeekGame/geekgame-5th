# [Algorithm] 千年讲堂的方形轮子 II

- 命题人：debugger
- Level 1：150 分
- Level 2：200 分
- Level 3：300 分

## 题目描述

<p><a target="_blank" rel="noopener noreferrer" href="https://github.com/PKU-GeekGame/geekgame-0th/tree/3be9f9c37020e28c10f3cd29f0d42ee5d3235c1b/problemset#千年讲堂的方形轮子25024--25022oracle">上上上上上回书说道</a>，<span class="you-name">You 酱</span>受邀为兆京大学千年讲堂开发了一套在线购票系统，但是有黑客伪造出了假的电子票。在此之后，<span class="you-name">You 酱</span>对 CBC 酱和 ECB 酱失去了信心。</p>
<p>四年过去，正当 <span class="you-name">You 酱</span>在研究磁盘加密时，<a target="_blank" rel="noopener noreferrer" href="https://developer.aliyun.com/article/952937">XTS 酱</a>找到了她：</p>
<ul>
<li>XTS 酱：<span class="you-name">You 酱</span>！</li>
<li><span class="you-name">You 酱</span>：Hi！</li>
<li>XTS 酱：喜欢什么模式？</li>
<li><span class="you-name">You 酱</span>：ﾋ…比起 CBC 和 ECB 更喜欢 X・T・S・♡！</li>
</ul>
<p>就这样，<span class="you-name">You 酱</span>再度重拾信心，基于 <strong>AES-XTS</strong> 算法开发了一套新的在线购票系统。</p>
<p>有了 XTS 酱的帮助，还会有<ruby>黑客<rp>（</rp><rt>A.L.A.N</rt><rp>）</rp></ruby>伪造电子票吗？</p>
<div class="well">
<p><strong>第二阶段提示：</strong></p>
<ul>
<li>虽然XTS有密文窃取机制，但是前两个Flag并不需要你了解这个机制。</li>
<li>Flag 1：XTS模式除了最后两个分组，其他分组的加密结果只和该分组明文以及分组位置有关，和其他分组无关。于是你可以先生成多个ticket，再用它们拼凑成一个新ticket。注意JSON里面对象前后、字段间以及字段的key和value间的空格都是无关紧要的。</li>
<li>Flag 2：拼凑密文不仅可以伪造ticket，还可以把code泄露出来。此题用户名限制的是字符数量，一个字符经过JSON encode后可能变成多个字节。</li>
<li>Flag 3：<ul>
<li>在Python里面运行<code>{i: len(json.dumps(chr(i))) - 2 for i in range(0x30000) if chr(i).isdigit()}</code>，看看结果是什么。</li>
<li>题目“检票”实际上给了一个解密oracle，有时可以用于解密某个特定分组位置上的任意密文（也即16个字节）。</li>
<li>密文窃取机制会偷走倒数第二个分组的部分密文，想办法用解密oracle把倒数第二个分组密文还原回来。出题人的解法大约需要尝试3000次才能正确还原倒数第二个分组密文。</li>
<li>你能拿到倒数第二个分组的密文之后，你可以把最后一个分组丢掉，再拼上你想要的东西。</li>
</ul>
</li>
</ul>
</div>

**[【附件：下载题目源码（algo-oracle2.py）】](attachment/algo-oracle2.py)**

**【网页链接：访问题目网页】**

## 预期解法

### Level 1
Level 1里面不需要兑换码。所以只需要伪造出flag为true的ticket就行。例如exp1.py的实现如此（其中的竖线只是为了方便区分分组而添加，不是明文的一部分）：
```
{"stuid": "00000|00000", "name": |"xxxxx", "flag":| false, "timesta|mp": 1761451540}
{"stuid": "00000|00000", "name": |"\u554a\u554axxx|             tru|e", "flag": fals|e, "timestamp": |1761451661}
{"stuid": "00000|00000", "name": |"xxxxxxxxxxxxxxx|x", "flag": fals|e, "timestamp": |1761451734}
```
用这三个ticket可以拼出一个新ticket：
```
{"stuid": "00000|00000", "name": |"xxxxx", "flag":|             tru|e, "timestamp": |1761451734}
```
需要注意的是，除非明文长度是分组长度的整数倍，拼接的时候不能最后两个分组拆开，否则因为密文窃取机制的存在拼接结果会出错。

### Level 2
除了伪造ticket之外还要把code泄露出来。先生成以下4个ticket，其中前三个原理和Level 1相同（里面的code和timestamp仅为举例，实际上code是随机的）：
```
{"stuid": "00000|00000", "name": |"xxxxx", "flag":| false, "code": |"6crm6tffs3frco1|n", "timestamp":| 1761452186}
{"stuid": "00000|00000", "name": |"\u554a\u554axxx|             tru|e", "flag": fals|e, "code": "89vh|96upwf0ol09g", "|timestamp": 1761|452248}
{"stuid": "00000|00000", "name": |"xxxxxxxxxxxxxxx|x", "flag": fals|e, "code": "y5m0|4r9zoipawlj3", "|timestamp": 1761|452285}
{"stuid": "00000|00000", "name": |"\u554a\u554a\u5|54a\u554a\u554a\|u554a\u554axxxxx|", "flag": false|, "code": "1u12d|1hwo928agfs", "t|imestamp": 17614|52320}
```
然后和Level 1一样，可以伪造出一个Ticket：
```
{"stuid": "00000|00000", "name": |"xxxxx", "flag":|             tru|e, "code": "y5m0|4r9zoipawlj3", "|timestamp": 1761|452285}
```
接着要把code泄露出来，把第三个ticket的后面部分和第四个ticket的前面部分拼接：
```
{"stuid": "00000|00000", "name": |"\u554a\u554a\u5|54a\u554a\u554a\|u554a\u554axxxxx|4r9zoipawlj3", "|timestamp": 1761|452285}
```
把这个伪造的ticket丢到query-ticket，就能从name字段读出code的后12个字符。而code的前4个字符是已知的，所以能恢复整个code。注意这里第二个和第三个ticket的true和false的最后一个字母都在另一个分组，这样query-ticket就能code的后12个（而不是11个）字符。

### Level 3
JSON里面会先把字符用UTF-16编码，此时一个字符会变成一个或两个字符。接着非ASCII的字符会转义成6个字符，于是一个原始字符可以转义成6个或12个字符。

Level 3的flag字段在最后面，因此需要攻击密文窃取机制。首先先生成如此ticket：
```
{"stuid": "0\uff|10\uff10\uff10\u|ff10\uff10\uff10|\uff10\uff10\ud8|3e\udff0", "code|": "2pslkkzp43lf|jpp6", "name": "|aaaaaaaaaaaaaaaa|", "flag": false|}
```
再生成另一个ticket（里面的jhlfswg是可以变化的随机字符串）
```
{"stuid": "00000|00\uff10\ud83e\u|dff0\ud83e\udff0|", "code": "w4ee|1ilps2oejtbe", "|name": "aaaaaaaa|jhlfswg", "flag"|: false}
   <Block 1>    |   <Block 2>    |   <Block 3>    |   <Block 4>    |   <Block 5>    |   <Block 6>    |   <Block 7>    |   <Block 8>    |
```
密文窃取机制做了这些事：
* 把Block 7用Block 7的key加密，生成Ciphertext 7
* 取Ciphertext 7的后8个字节拼到Block 8后面，再用Block 8的key加密
* 加密的结果会放到第7个Block，而原来的Ciphertext 7的前8字节会放到第8个Block

于是，如果你用第7个Block的密文替换第一个ticket的第8个Block的密文，再去query-ticket查询，这样就可能能得到该Block的明文（也即Ciphertext 7的后8个字节和Block 8）。但是：（1）如果明文有引号或者无效的转义序列，那么json.decode会出错；（2）如果有不合法的UTF-8序列，decode('utf-8', 'ignore')会把这些序列删掉。可以反复用不同的随机字符串尝试直到Ciphertext 7的后8个字节都是有效字符为止，其概率为(93/256)^8约为1/3297。

拿到了Ciphertext 7之后，就可以继续拼接了。再生成以下ticket（注意第一个ticket的name里面本来只有一个反斜杠，会被JSON转义成两个）：
```
{"stuid": "00000|00000", "code": |"2uqu7dsx1ulxkh1|l", "name": "\\a|aaaaaaaaaaaaaaa"|, "flag": false}
{"stuid": "00000|00\uff10\uff10\u|ff10", "code": "|jbfqpcoea0d3udu7|", "name": "\u55|4aaaaaaaaaaaaaaa|", "flag": false|}
{"stuid": "00\uf|f10\uff10\uff10\|uff10\uff10\uff1|0\uff10\uff10", |"code": "gk0oqbr|bsmyyg5yd", "nam|e": "\u554aaaaaa|aaaaaa", "flag":| false}
{"stuid": "0\uff|10\uff10\uff10\u|ff10\uff10\uff10|\uff10\uff10\ud8|3e\udff0", "code|": "uccumrnlcf9b|c6nf", "name": "|: true}         |", "flag": false|}
```
先把code偷出来：
```
{"stuid": "00000|00000", "code": |"2uqu7dsx1ulxkh1|l", "name": "\\a|1ilps2oejtbe", "|4aaaaaaaaaaaaaaa|e": "\u554aaaaaa|aaaaaa", "flag":| false}
```
同样拿到code的后12个字符和直接query-ticket能得到的4个字符组合就能还原code。

再伪造一个有效的ticket（注意下面的ticket中最后一个block是完整的16字节，在源ticket里面也不是最后一个或倒数第二个block，所以不会涉及密文窃取机制）：
```
{"stuid": "00000|00\uff10\ud83e\u|dff0\ud83e\udff0|", "code": "w4ee|1ilps2oejtbe", "|name": "aaaaaaaa|jhlfswg", "flag"|: true}
```
用上面的ticket和code就能拿到flag。
