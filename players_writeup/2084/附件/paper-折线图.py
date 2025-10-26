import re
import math

path = """
m 33.553693,95.367731 3.427519,8.810729 3.427518,-16.558378 3.427518,9.251522 3.427519,27.353996 3.427518,-58.786197 3.427519,-23.761676 3.427518,52.171314 3.427519,-54.327234 3.427518,16.457832 3.427518,-30.067764 3.427519,78.266585 3.427518,4.22344 3.427519,-71.066594 3.427518,-11.423431 3.427519,86.600815 3.427518,2.68087 3.427518,-15.357522 3.427519,-4.468307 3.427518,-69.455856 3.427517,4.671441 3.42752,84.610244 3.42752,-21.344519 3.42752,-24.782512 3.42752,18.553553 3.42751,-37.608121 3.42752,66.504739 3.42752,-28.896618 3.42752,27.573478 3.42752,-15.357522 3.42752,-43.856399 3.42751,-1.963667 3.42752,-10.212063 3.42752,19.789414 3.42752,51.600237 3.42752,-6.79166 3.42752,-82.490025 3.42751,44.936706 3.42752,16.771501 3.42752,24.892608 3.42752,-79.645691 3.42752,56.334079 3.42752,-1.580996 3.42752,4.695158 3.42751,4.556364 3.42752,-61.754261 3.42752,28.47598 3.42752,51.600237 3.42752,-6.79166 3.42752,-82.490025 3.42751,86.600815 3.42752,2.68087 3.42752,-15.357522 3.42752,-62.500732 3.42752,-11.423431 3.42752,64.854148 3.42751,-25.32662 3.42752,-1.84608 3.42752,44.808577 3.42752,-13.034169 3.42752,-69.455856 3.42752,64.854148
h 3.42752
l 3.42751,3.083018 3.42752,-35.930436 3.42752,7.520798 3.42752,28.409638 3.42752,-1.533801 3.42752,17.46914 3.42752,-83.872505 3.42751,32.00673 3.42752,35.930436 3.42752,18.663649 3.42752,-48.919367 3.42752,63.118557
""".strip()

def parse_path_points(path_str):
    # Tokenize commands and numbers
    tokens = re.findall(r'[MLHVZmlhvz]|-?\d+(?:\.\d+)?', path_str)
    pts = []
    x = y = 0.0
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t in 'mMlLhHvV':
            cmd = t
            i += 1
            if cmd == 'm' or cmd == 'M':
                rel = (cmd == 'm')
                # first pair: move
                x1 = float(tokens[i]); y1 = float(tokens[i+1]); i += 2
                if rel:
                    x += x1; y += y1
                else:
                    x = x1; y = y1
                pts.append((x, y))
                # subsequent pairs: implicit lineto
                while i < len(tokens) and re.match(r'-?\d', tokens[i]):
                    dx = float(tokens[i]); dy = float(tokens[i+1]); i += 2
                    if rel:
                        x += dx; y += dy
                    else:
                        x = dx; y = dy
                    pts.append((x, y))
            elif cmd == 'l' or cmd == 'L':
                rel = (cmd == 'l')
                while i < len(tokens) and re.match(r'-?\d', tokens[i]):
                    dx = float(tokens[i]); dy = float(tokens[i+1]); i += 2
                    if rel:
                        x += dx; y += dy
                    else:
                        x = dx; y = dy
                    pts.append((x, y))
            elif cmd == 'h' or cmd == 'H':
                rel = (cmd == 'h')
                while i < len(tokens) and re.match(r'-?\d', tokens[i]):
                    dx = float(tokens[i]); i += 1
                    if rel:
                        x += dx
                    else:
                        x = dx
                    pts.append((x, y))
            elif cmd == 'v' or cmd == 'V':
                rel = (cmd == 'v')
                while i < len(tokens) and re.match(r'-?\d', tokens[i]):
                    dy = float(tokens[i]); i += 1
                    if rel:
                        y += dy
                    else:
                        y = dy
                    pts.append((x, y))
            else:
                # Z/z: closepath -> irrelevant here
                pass
        else:
            i += 1
    return pts

pts = parse_path_points(path)
ys = [y for _, y in pts]

# Known prefix for calibration
prefix = "flag{"
known_codes = [ord(c) for c in prefix]
known_logs = [math.log(c) for c in known_codes]
known_ys = ys[:len(prefix)]

# Linear regression y = A + B * log(ascii)
mx = sum(known_logs)/len(known_logs)
my = sum(known_ys)/len(known_ys)
cov = sum((x-mx)*(y-my) for x, y in zip(known_logs, known_ys))
var = sum((x-mx)**2 for x in known_logs)
B = cov / var
A = my - B * mx

def y_to_char(y):
    # invert the mapping: log_val = (y - A)/B, ascii = exp(log_val)
    code = int(round(math.exp((y - A) / B)))
    return chr(code)

decoded = ''.join(y_to_char(y) for y in ys)
print(decoded)
