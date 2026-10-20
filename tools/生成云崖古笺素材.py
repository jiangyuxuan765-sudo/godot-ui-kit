# -*- coding: utf-8 -*-
"""从零绘制云崖古笺：宣纸毛边、竹简、木刻牌与枯笔墨线。"""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]; DST=ROOT/'UI'/'云崖古笺'; DST.mkdir(exist_ok=True)
SIZES=json.load(open(ROOT/'tools/验收/尺寸契约-云崖古笺.json',encoding='utf8'))
INK,CHAR,SMOKE='#171A1B','#252A29','#536B6B'; PAPER,OCHRE,RED,OLIVE='#E8DFC7','#B58A52','#8E3F3C','#687C67'
def svg(w,h,b): return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">{b}</svg>'
def paper(w,h): return f'<path d="M3 5 L{w-8} 2 L{w-3} 7 L{w-5} {h-5} L{w-12} {h-2} L5 {h-5} L2 11 Z" fill="{CHAR}" stroke="{OCHRE}" stroke-width="2"/><path d="M18 19 L{w-20} 17" stroke="{PAPER}" opacity=".32"/><path d="M16 {h-18} Q{w*.42} {h-24} {w-17} {h-20}" stroke="{SMOKE}" stroke-width="2" fill="none"/>'
def plaque(w,h,accent=OCHRE): return f'<path d="M14 2 H{w-10} L{w-2} 10 V{h-10} L{w-12} {h-2} H12 L2 {h-12} V12 Z" fill="{CHAR}" stroke="{accent}" stroke-width="2"/><path d="M{w*.12:.1f} 8 H{w*.72:.1f} M{w*.2:.1f} {h-8} H{w*.86:.1f}" stroke="{SMOKE}" stroke-width="1"/><path d="M28 {h*.32:.1f} H{w-32}" stroke="{PAPER}" stroke-width="2" opacity=".35"/>'
def bamboo(w,h): return f'<rect x="2" y="2" width="{w-4}" height="{h-4}" fill="{CHAR}" stroke="{OCHRE}" stroke-width="2"/><path d="M12 2 V{h-2} M{w-12} 2 V{h-2}" stroke="{OLIVE}" stroke-width="3"/><path d="M12 {h*.22:.1f} H{w-12} M12 {h*.78:.1f} H{w-12}" stroke="{OCHRE}"/>'
def ink(w,h,vertical=False,color=SMOKE):
 if vertical: return f'<path d="M{w/2:.1f} 4 Q{w*.38:.1f} {h*.35:.1f} {w/2:.1f} {h*.55:.1f} T{w*.46:.1f} {h-4}" stroke="{color}" stroke-width="{max(3,w*.18):.1f}" fill="none"/><path d="M{w*.26:.1f} 6 V{h-6}" stroke="{OCHRE}"/>'
 return f'<path d="M4 {h*.55:.1f} Q{w*.30:.1f} {h*.38:.1f} {w*.56:.1f} {h*.57:.1f} T{w-4} {h*.44:.1f}" stroke="{color}" stroke-width="{max(3,h*.28):.1f}" fill="none"/><path d="M6 {h*.75:.1f} H{w-8}" stroke="{OCHRE}"/>'
def icon(w,h,mode='circle'):
 cx,cy=w/2,h/2
 if mode=='check': body=f'<path d="M{cx-18} {cy} L{cx-4} {cy+14} L{cx+21} {cy-16}" fill="none" stroke="{OLIVE}" stroke-width="5"/>'
 elif mode=='back': body=f'<path d="M{cx+15} {cy-18} L{cx-12} {cy} L{cx+15} {cy+18} M{cx-10} {cy} H{cx+21}" fill="none" stroke="{PAPER}" stroke-width="3"/>'
 else: body=f'<circle cx="{cx}" cy="{cy}" r="{min(w,h)*.28}" fill="none" stroke="{SMOKE}" stroke-width="3"/><path d="M{cx-8} {cy} H{cx+8} M{cx} {cy-8} V{cy+8}" stroke="{OCHRE}" stroke-width="2"/>'
 return f'<rect x="1" y="1" width="{w-2}" height="{h-2}" fill="{INK}" stroke="{SMOKE}" stroke-width="2"/>{body}'
for name,(w,h) in SIZES.items():
 if name in {'横导航栏背景','横导航栏选中框'}: body=bamboo(w,h)
 elif '实心按钮' in name or name=='白色描边按钮': body=plaque(w,h,RED if '红色' in name else OLIVE if '绿色' in name else OCHRE)
 elif '进度条' in name or name in {'滑块填充','滑块空槽','横滚动条空槽','横滚动条拖动键','竖滑块填充','竖滑块空槽','竖滚动条空槽','竖滚动条拖动键'}: body=ink(w,h,h>w,OLIVE if '填充绿' in name else OCHRE if '填充金' in name else SMOKE)
 elif '图标' in name or name in {'checkbox未选','checkbox选中','check按钮关','check按钮开','tree展开箭头','tree折叠箭头','取消图标','环形加载指示器','确定图标','设置图标','摇杆背景','摇杆键','步进指示器','步进指示器2'}: body=icon(w,h,'check' if '选中' in name or '开' in name else 'back' if '返回' in name else 'circle')
 elif name=='弹窗分界线': body=ink(w,h,False,OCHRE)
 else: body=paper(w,h)
 specks=''.join(f'<path d="M{(i*37)%max(10,w-4)+2} {((i*19)+7)%max(10,h-4)+2} l{3+i%4} 0" stroke="{PAPER}" opacity=".16"/>' for i in range(5))
 (DST/f'{name}.svg').write_text(svg(w,h,body+specks),encoding='utf8')
print('from-scratch generated',len(list(DST.glob('*.svg'))),'SVGs')
