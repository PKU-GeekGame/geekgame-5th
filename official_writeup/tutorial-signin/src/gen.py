from pylibdmtx.pylibdmtx import encode
from PIL import Image
from pathlib import Path

SIZE = 250
PAD = 50
COLS = 4
ROWS = 2
LEN = COLS * ROWS

duration = [1000 - 60*LEN] + [60]*LEN
disposal = [0] + [3]*LEN

bg = Image.open('bg.gif')
x_base = (bg.width - COLS * SIZE - (COLS-1) * PAD) // 2
y_base = (bg.height - ROWS * SIZE - (ROWS-1) * PAD) // 2

p_img = Image.new('P', (1, 1))
p_img.putpalette([255, 255, 255, 0, 0, 0])

def get_dm(s):
    encoded = encode(s.encode('utf8'))
    img = (
        Image.frombytes('RGB', (encoded.width, encoded.height), encoded.pixels)
    ).quantize(palette=p_img, dither=Image.Dither.NONE)

    img.info['transparency'] = 0
    img = img.resize((SIZE, SIZE), Image.Resampling.NEAREST)
    return img

def gen_flag(outp, flag):
    flag_pieces = []
    str_len = len(flag)
    for i in range(LEN):
        flag_pieces.append(flag[i*str_len//LEN : (i+1)*str_len//LEN])
    #print(flag_pieces)

    covers = [Image.new('P', (bg.width, bg.height)) for _ in range(LEN)]

    for ind, flag in enumerate(flag_pieces):
        x = x_base + (SIZE+PAD) * (ind%COLS)
        y = y_base + (SIZE+PAD) * (ind//COLS)
        dm = get_dm(flag)
        covers[ind].paste(dm, (x, y))
        covers[ind].putpalette([255, 255, 255, 0, 0, 0])
        covers[ind].info['transparency'] = 0

    covers = [covers[i] for i in [2, 7, 5, 0, 4, 6, 3, 1]]

    bg.save(outp, save_all=True, append_images=covers, duration=duration, loop=0, disposal=disposal, optimize=False, interlace=False)

def gen(user, ch) -> Path:
    flag = ch.flags[0].correct_flag(user)

    dst_path = Path('_gen').resolve() / str(user._store.id)
    dst_path.mkdir(exist_ok=True, parents=True)

    out_path = dst_path / 'out.gif'
    gen_flag(out_path, flag)
    return out_path
