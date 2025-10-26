import fitz
doc = fitz.open("misc-paper.pdf")
page = doc.load_page(0)
a = page.get_drawings()
#同样的，这些数据是开始随机，发现我们想用的之后改上去的
for i in range(106):
    c = ""
    b = a[len(a)-175+i]["items"][0][2]
    match b[1]:
        case 231.93435668945312:
            c = c + "11"
        case 250.2376251220703:
            c = c + "10"
        case 268.5408935546875:
            c = c + "01"
        case 286.8441467285156:
            c = c + "00"
    match b[0]:
        case 389.49017333984375:
            c = c + "00"
        case 426.33441162109375:
            c = c + "01"
        case 463.17864990234375:
            c = c + "10"
        case 500.02288818359375:
            c = c + "11"
    print(c)