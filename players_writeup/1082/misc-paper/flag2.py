import math
import itertools

def main():
    data = []
    with open("flag2.in", "rb") as f:
        for line in f.read().splitlines():
            args = line.decode().split()
            assert args[:4] == ["1", "0", "0", "1"]
            assert args[6:] == ["cm", "/M0", "Do"]
            data.append(list(map(float, args[4:6])))

    #print(data[:10])
    assert len(data) == 106

    xs, ys = zip(*data)
    xs = list(itertools.accumulate(xs))
    ys = list(itertools.accumulate(ys))
    print(xs[:10])
    print(ys[:10])

    xs = [round(x, 6) for x in xs]
    ys = [round(y, 6) for y in ys]
    x_uniq = sorted(set(xs))
    y_uniq = sorted(set(ys))
    assert len(x_uniq) == len(y_uniq) == 4

    xs = [x_uniq.index(x) for x in xs]
    ys = [y_uniq.index(y) for y in ys]

    cords = list(zip(xs, ys))
    print(cords[:10])

    flag = ""
    for a, b in itertools.batched(cords, n=2):
        n = (a[1] << 6) | (a[0] << 4) | (b[1] << 2) | b[0]
        flag += chr(n)
    print(flag)

main()
