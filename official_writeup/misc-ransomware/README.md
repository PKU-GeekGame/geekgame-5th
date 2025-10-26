# [Misc] 勒索病毒

- 命题人：ouuan
- 发现威胁：150 分
- 忽略威胁：200 分
- 支付比特币：250 分

## 题目描述

<p>——作为 GeekGame 的出题人，电脑里居然跑着一堆带有 n-day 漏洞的软件，并且直接连到公网暴露了端口……</p>
<p>当你正沾沾自喜，以为可以靠场外手段拿到 flag 时，忽然发现：你并不是第一个闯入这台机器的人——出题人的 <strong>Windows 系统</strong> 已经遭到 <strong>勒索病毒</strong> 的入侵，<strong>包含 flag 的文件</strong> 已被加密。</p>
<div class="well">
<p>面对被加密的 flag 文件，你的选择是……</p>
<p><label>
    <input type="radio" name="get-encrypted-flag" value="btcoin">
    向攻击者支付比特币
</label></p>
<p><label>
    <input type="radio" name="get-encrypted-flag" value="turing-award">
    挑战现代密码学，获得图灵奖
</label></p>
<p><label>
    <input type="radio" name="get-encrypted-flag" value="???">
    ？？？
</label></p>
</div>
<p><strong>补充说明：</strong></p>
<ul>
<li>本题附件包含真实的勒索信文本，该文本可能会被杀毒软件识别为可疑或恶意文件，但附件中不包含可执行的勒索病毒，是安全的。可以采取适当措施避免杀毒软件影响解题。</li>
<li>附件只是模拟了勒索病毒的加密行为，联系攻击者或支付比特币并不能解密本题附件中的文件。</li>
<li>在实际比赛中，通过攻击比赛平台、出题人电脑等方式获取 flag 是违规的，请勿模仿本题的背景故事。</li>
</ul>
<div class="well">
<p><strong>第二阶段提示：</strong></p>
<ul>
<li>Flag 1:<ul>
<li>勒索信中指明了该勒索软件为 DoNex，可以搜索到关于 DoNex 破解的资料，例如 <a target="_blank" rel="noopener noreferrer" href="https://cfp.recon.cx/recon2024/talk/LQ8B7H/">Cryptography is hard: Breaking the DoNex ransomware :: Recon 2024</a></li>
<li>题面表明出题人使用的是 Windows 系统，<a target="_blank" rel="noopener noreferrer" href="https://git-scm.com/book/en/v2/Customizing-Git-Git-Configuration#_core_autocrlf">默认使用 <code>\r\n</code> 作为换行符</a>；如果按照 LF（<code>\n</code>）进行解密，会发现 flag1-2-3.txt 的开头 16B 是可读的，这正好是 algo-gzip.py 第一行的长度，说明换行符处出了问题</li>
</ul>
</li>
<li>Flag 2: 学习一下 ZIP 文件的结构，根据已知信息，可以补全一些缺失的部分</li>
<li>Flag 3:<ul>
<li>学习一下 DEFLATE 压缩算法的结构，已知的部分提供了数据编码的方式</li>
<li>数据编码方式经过特殊构造，可以唯一确定整个数据流</li>
<li>注意利用 ZIP 字段提供的各项信息，思考一下数据编码前后长度之间的关系</li>
<li>DEFLATE 流的 EOF 后没有多余的垃圾数据</li>
</ul>
</li>
</ul>
</div>

**[【附件：下载题目附件（misc-ransomware.zip）】](attachment/misc-ransomware.zip)**

## 预期解法

[出题人博客](https://ouuan.moe/post/2025/10/geekgame-2025-graphauth-ransomware#勒索病毒)

完整脚本见 [sol.py](./sol/sol.py)

### Flag 1

根据勒索信可以搜到关于 DoNex 的资料，比如 decryptor，以及 [Cryptography is hard: Breaking the DoNex ransomware :: Recon 2024](https://cfp.recon.cx/recon2024/talk/LQ8B7H/)。

漏洞很简单，就是重用了流密码，所以把已知明文、对应的密文、另一个密文异或在一起就能得到另一个明文。被加密的文件中有上一届的 `algo-gzip.py`，就有了已知明文。

如果直接用 decryptor，可能会提示解密不了，这是因为长度不对，而长度不对是因为被加密的文件是 CRLF，而从 GitHub 下载的文件是 LF，需要转换一下。如果你注意力惊人，或者在 Windows 上采用默认 Git 配置 checkout 文件而非从 GitHub 网页下载，就能直接拿到 CRLF 的 `algo-gzip.py`。而如果你是自己写的异或解密而不是用的现成的 decryptor，没有先检查文件长度，你就会发现解密出来开头是 `This file contaiiZ#`，后面都是乱码，此时，结合 `algo-gzip.py` 第一行的长度，只需要不惊人的注意力就能意识到，可能是 CRLF 的问题。

### Flag 2

`algo-gzip.py` 只提供了开头一段密钥，继续解密需要更多的已知明文。附件里有一个声称没有存储 flag 的 ZIP 文件，而 ZIP 文件格式中很多信息会冗余存储，所以可以从不完整的 ZIP 文件中恢复一些缺失的部分（从 LFH 恢复 CDH 和 EOCD）。根据文件长度可以确定 ZIP 里没有第三个文件。可以搜一篇教程或者看 [APPNOTE.TXT](https://pkware.cachefly.net/webdocs/casestudies/APPNOTE.TXT) 学习一下 ZIP 文件结构。当然，也可以让 AI 写，或者用一些现成的工具。

CDH 中有一些 LFH 没有的字段，其中最难确定的是 external attributes，但我特意让 flag 从这个字段开始，如果设为 0 会得到 `fl\xe1f{`，把它修复为 `flag{`，后面也用相同的值就可以修复。当然，直接猜也是可以的，考察第三人称单数的使用，以及识别 `^T` 是一个字符还是两个字符。

### Flag 3

最后文件中未知的还有两段，一段是压缩数据，一段是超过 ZIP 文件长度的末尾，显然只有前者是能破解的（除非末尾的密钥能破解）；实际上我在 `gen.py` 里往后者塞了一个假 flag，但这对结果其实没有任何影响。

学习 DEFLATE 数据结构，然后解析一下已知的开头部分，可以发现它的动态 Huffman 树已经确定。观察编码可以发现，只有 6 个 literal 编码非零，长度分别为 1、2、3、4、14、15。而根据 ZIP 字段中记录的长度，这个 DEFLATE 是把 30 字节的原数据编码成了约 90 字节。从编码后长度中减去 DEFLATE header 的长度，再考虑到最后一个 byte 可能有 1\~8 个 bit，可以得到编码数据减去末尾 EOB 的长度可能为 440\~447。如果数据中包含编码长度为 1\~4 的 literal，编码后长度就会小于 440，而如果采用了 distance length pair，则会更短。因此，数据中只可能包含编码长度为 14、15 的 literal，具体来说是 3\~10 个编码长度为 14 的 literal，剩下的为编码长度为 15 的 literal。

于是，数据的构成就基本确定了，只需枚举 $5.3 \times 10^7$ 种排列组合。而 ZIP 字段中提供了 CRC32 校验和，可以用来校验哪个排列是正确的。后来才想到，除了 CRC32，还可以根据 flag 都是 ASCII 可见字符来筛选，这样有一些别的做法，但可能还更麻烦。

P.S. 感觉这题造 DEFLATE 编码以及对齐明文和 flag 的位置比做题难（在思路已知的前提下（

P.P.S. 各种排列组合的 CRC32 似乎都没有冲突（如果是随机的 32bit 则会有大量重复），我怀疑这是可以证明的，但我不懂这个，就造完数据后枚举一遍来保证唯一性了（
