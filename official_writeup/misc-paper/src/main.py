import matplotlib
from matplotlib import pyplot as plt
import math
import subprocess
from pathlib import Path
import shutil

FLAGS = [
    ('flag{THeGoaLoFARtIFACTEvaLUaTionISTOawardBadgestOaRtiFactsoFACcEpTedpAPerS}', 'flag{\\documentclass[sigconf,review,anonymous,screen]}'),
    ('flag{THeGOAloFArtifACteVaLuatiONIStoAWarDbadgEStoArtiFAcTSofAccePTedpAPerS}', 'flag{\\documentclass[sigconf,review,screen,anonymous]}'),
    ('flag{THeGoAlofaRTiFACTeVaLuAtIONistOawaRDbADGEsToaRTifACtSOFACCEPtEDpAPerS}', 'flag{\\documentclass[sigconf,anonymous,review,screen]}'),
    ('flag{THegoaLOfArTiFacTEVAlUaTiONistoaWaRdbAdgESTOARtIfActSOfaccepTEDpAPerS}', 'flag{\\documentclass[sigconf,anonymous,screen,review]}'),
    ('flag{THegoAloFaRTIfACteVaLuaTIonISTOAWarDBADGestoARtIFactSOFAccePTeDpAPerS}', 'flag{\\documentclass[sigconf,screen,review,anonymous]}'),
    ('flag{THegoaloFARTIfAcTEvaluaTioNistOaWARDBAdgEStoartiFAcTSOFaCcePteDpAPerS}', 'flag{\\documentclass[sigconf,screen,anonymous,review]}'),
]

matplotlib.rcParams['pdf.fonttype'] = 3 # to make the label unselectable :)

def gen_figure(flag1, flag2):
    flag1_path = Path('tex/flag1.pdf')
    flag2_path = Path('tex/flag2.pdf')

    if flag1_path.is_file():
        flag1_path.unlink()
    if flag2_path.is_file():
        flag2_path.unlink()

    xs = []
    ys = []
    for ind, c in enumerate(flag1):
        xs.append(ind)
        ys.append(math.log(ord(c)))

    fig, ax = plt.subplots(figsize=(5, 2))
    ax.plot(xs, ys)
    ax.set_xlabel('ɪɴᴅᴇx ᴏꜰ ᴄʜᴀʀᴀᴄᴛᴇʀ')
    ax.set_ylabel(r'ʟᴏɢ(ᴀꜱᴄɪɪ)')
    ax.set_xticks([])
    ax.set_yticks([])
    fig.savefig(flag1_path, bbox_inches='tight')

    xs = []
    ys = []
    for ind, c in enumerate(flag2.encode().hex()):
        c = int(c, 16)
        xs.append(c % 4)
        ys.append(c // 4)

    fig, ax = plt.subplots(figsize=(4, 2))
    ax.scatter(xs, ys)
    ax.set_xlabel('ʟᴏᴡᴇʀ ᴛᴡᴏ ʙɪᴛꜱ')
    ax.set_ylabel('ʜɪɢʜᴇʀ ᴛᴡᴏ ʙɪᴛꜱ')
    fig.savefig(flag2_path, bbox_inches='tight')

def compile_tex(idx):
    tmp_path = Path('/tmp/tex')
    if tmp_path.is_dir():
        shutil.rmtree(tmp_path)
    shutil.copytree('tex', tmp_path)

    subprocess.check_call('bash build.sh', cwd=tmp_path, shell=True)
    shutil.copyfile(tmp_path/'main.pdf', f'/dst/pdf/{idx}.pdf')

for idx, (flag1, flag2) in enumerate(FLAGS):
    print('===', idx)
    gen_figure(flag1, flag2)
    compile_tex(idx)