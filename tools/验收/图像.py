# -*- coding: utf-8 -*-
"""PNG 解码与像素判定（不依赖 PIL）。

原先 check_shots.py 和 check_hue.py 各自抄了一份一模一样的 load_png，
改一处忘另一处就会出现「两个脚本对同一张图给出不同结论」。抽到这里。

Godot 的 Image.save_png() 出的是非交错 8bit RGB/RGBA，所以只处理这两种；
其它 coltype（灰度、调色板、16bit）直接报错而不是猜，猜错会静默算歪统计。
"""
import struct
import zlib


def 读PNG(path):
    """返回 (宽, 高, 通道数, 每行字节数组)。逐行反 filter，五种类型全支持。"""
    raw = open(path, "rb").read()
    if raw[:8] != b"\x89PNG\r\n\x1a\n":
        raise SystemExit("不是 PNG：%s" % path)
    pos, idat = 8, b""
    W = H = coltype = None
    while pos < len(raw):
        ln = struct.unpack(">I", raw[pos:pos + 4])[0]
        typ = raw[pos + 4:pos + 8]
        body = raw[pos + 8:pos + 8 + ln]
        if typ == b"IHDR":
            W, H, bitdepth, coltype = struct.unpack(">IIBB", body[:10])
            if bitdepth != 8:
                raise SystemExit("仅支持 8bit，实际 %dbit：%s" % (bitdepth, path))
        elif typ == b"IDAT":
            idat += body
        elif typ == b"IEND":
            break
        pos += 12 + ln
    if coltype not in (2, 6):
        raise SystemExit("仅支持 RGB/RGBA，实际 coltype=%s：%s" % (coltype, path))
    nch = 3 if coltype == 2 else 4
    data = zlib.decompress(idat)
    stride = W * nch
    rows, prev, p = [], bytearray(stride), 0
    for _y in range(H):
        ft = data[p]
        p += 1
        cur = bytearray(data[p:p + stride])
        p += stride
        if ft == 1:
            for i in range(nch, stride):
                cur[i] = (cur[i] + cur[i - nch]) & 0xFF
        elif ft == 2:
            for i in range(stride):
                cur[i] = (cur[i] + prev[i]) & 0xFF
        elif ft == 3:
            for i in range(stride):
                a = cur[i - nch] if i >= nch else 0
                cur[i] = (cur[i] + ((a + prev[i]) >> 1)) & 0xFF
        elif ft == 4:
            for i in range(stride):
                a = cur[i - nch] if i >= nch else 0
                b = prev[i]
                c = prev[i - nch] if i >= nch else 0
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                cur[i] = (cur[i] + pr) & 0xFF
        rows.append(cur)
        prev = cur
    return W, H, nch, rows


def 取像素器(nch, rows):
    """闭包比每次算偏移快，逐像素循环里差别明显。"""
    def px(x, y):
        o = x * nch
        r = rows[y]
        return r[o], r[o + 1], r[o + 2]
    return px


def 背景判定器(底色, 暗底上限=30, 容差=23):
    """按套别底色生成判定函数，留抗锯齿余量。

    两条分支，按底色本身选：

    近黑底（max ≤ 30，如义体裂界 #07070B）：判「够暗且够中性」。上限固定 30
    而不是由底色推导——第十一到十四套记录在规范里的占比数字全是按 30 量的，
    换成推导值（如 max(底色)+23=34）会把 31–34 那层暗中性像素划进背景，中性
    色块占比一下少二十多个百分点，与历史数字再也对不上。

    其它底色（如拓荒纪事的深棕皮革 rgb(103,81,60)）：判「与底色三通道各自
    接近」。这类底色既不够暗、也不够亮，套「够暗」那条会一个背景都判不出来，
    占比冲到 93% 并误报「拉伸失控」（拓荒纪事就是这么暴露的）。
    """
    br, bg, bb = 底色
    if max(底色) <= 暗底上限:
        # 色偏容差必须由底色自身的色偏推导，不能硬编码。原先写死 12（从义体裂界
        # #07070B 的 max-min=4 来的经验值），碰上星舰指令的靛蓝底 rgb(7,13,21)
        # 就崩了：它自身 max-min=14 > 12，底色自己都不被判成背景，75% 的纯底色
        # 像素全算成内容，占比冲到 99% 并误报「拉伸失控」。
        底色偏 = max(底色) - min(底色)
        色偏上限 = max(12, 底色偏 + 6)

        def is_bg(r, g, b):
            return max(r, g, b) <= 暗底上限 and (max(r, g, b) - min(r, g, b)) <= 色偏上限
    else:
        def is_bg(r, g, b):
            return (abs(r - br) <= 容差 and abs(g - bg) <= 容差
                    and abs(b - bb) <= 容差)
    return is_bg
