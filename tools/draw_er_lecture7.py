"""Generate editable SVG and matching PNG diagrams using Lecture 7 notation."""
from pathlib import Path
from html import escape
from PIL import Image, ImageDraw, ImageFont

OUT=Path(__file__).resolve().parents[1]/'docs/ER_lecture7'
W,H=1800,1160
INK='#233d4a'; BLUE='#dbeaf1'; EDGE='#476371'; GRAY='#617680'


class Canvas:
    def __init__(self):
        self.svg=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">','<rect width="100%" height="100%" fill="white"/>']
        self.im=Image.new('RGB',(W*2,H*2),'white'); self.d=ImageDraw.Draw(self.im)
    def line(self,points,dashed=False,color=EDGE,width=2):
        pts=' '.join(f'{x},{y}' for x,y in points)
        dash=' stroke-dasharray="7 5"' if dashed else ''
        self.svg.append(f'<polyline points="{pts}" fill="none" stroke="{color}" stroke-width="{width}"{dash}/>')
        for (x1,y1),(x2,y2) in zip(points,points[1:]):
            if dashed:
                import math
                length=math.hypot(x2-x1,y2-y1)
                for i in range(0,int(length),12):
                    a=i/length;b=min(i+7,length)/length
                    self.d.line([(2*(x1+(x2-x1)*a),2*(y1+(y2-y1)*a)),(2*(x1+(x2-x1)*b),2*(y1+(y2-y1)*b))],fill=color,width=width*2)
            else:self.d.line([(x1*2,y1*2),(x2*2,y2*2)],fill=color,width=width*2)
    def rect(self,x,y,w,h,fill='white',stroke=EDGE):
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')
        self.d.rectangle((x*2,y*2,(x+w)*2,(y+h)*2),fill=fill,outline=stroke,width=4)
    def text(self,x,y,s,size=23,bold=False,center=False,under=False,color=INK):
        font=ImageFont.truetype('C:/Windows/Fonts/msyhbd.ttc' if bold else 'C:/Windows/Fonts/msyh.ttc',size*2)
        width=self.d.textlength(s,font=font)/2
        left=x-width/2 if center else x
        self.svg.append(f'<text x="{left}" y="{y+size}" font-family="Microsoft YaHei, sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}">{escape(s)}</text>')
        self.d.text((left*2,y*2),s,font=font,fill=color,anchor='lt')
        if under:self.line([(left,y+size+5),(left+width,y+size+5)],width=1)
    def entity(self,x,y,w,title,rows):
        height=58+len(rows)*38+16
        self.rect(x,y,w,height);self.rect(x,y,w,52,BLUE)
        self.text(x+w/2,y+10,title,24,True,True)
        for i,row in enumerate(rows):
            s,key=row if isinstance(row,tuple) else (row,False)
            self.text(x+20,y+65+i*38,s,23,under=key)
        return height
    def diamond(self,x,y,title,rx=95,ry=52):
        pts=[(x-rx,y),(x,y-ry),(x+rx,y),(x,y+ry),(x-rx,y)]
        self.svg.append('<polygon points="'+' '.join(f'{a},{b}' for a,b in pts[:-1])+f'" fill="#f2f7f9" stroke="{EDGE}" stroke-width="2"/>')
        self.d.polygon([(a*2,b*2) for a,b in pts[:-1]],fill='#f2f7f9',outline=EDGE,width=4)
        self.text(x,y-17,title,23,center=True)
    def save(self,name):
        OUT.mkdir(parents=True,exist_ok=True)
        (OUT/(name+'.svg')).write_text('\n'.join(self.svg)+ '\n</svg>',encoding='utf-8')
        self.im.save(OUT/(name+'.png'))


def conceptual():
    c=Canvas()
    c.text(70,35,'深圳地铁概念 E-R 图',36,True)
    c.text(70,95,'Lecture 7 表示法｜概念实体、联系与属性｜与当前六表实现保持一致',23,color=GRAY)
    c.entity(80,245,300,'行政区 District',[('district_id',True),'name_en'])
    c.entity(740,245,320,'车站 Station',[('station_id',True),'name_zh','name_en','lon_mdeg [可空]','lat_mdeg [可空]'])
    c.entity(1400,245,310,'线路 MetroLine',[('line_id',True),'name_zh','name_en'])
    c.diamond(545,325,'位于')
    c.line([(380,325),(450,325)])
    c.line([(640,321),(740,321)]);c.line([(640,329),(740,329)])
    c.text(390,285,'0..*',22);c.text(662,285,'1..1',22)
    c.diamond(1230,365,'经过')
    c.line([(1060,365),(1135,365)]);c.line([(1325,365),(1400,365)])
    c.text(1068,324,'0..*',22);c.text(1338,324,'0..*',22)
    c.rect(1120,535,330,230)
    for i,s in enumerate(['position','status','opening_year','first_train [可空]','last_train [可空]']):c.text(1140,550+i*39,s,23)
    c.line([(1230,417),(1230,535)],dashed=True)
    c.text(1480,553,'关系属性',23,True)
    c.text(1480,600,'不含 station_id',21,color=GRAY)
    c.text(1480,637,'或 line_id',21,color=GRAY)
    c.text(1480,690,'它们在映射成表时引入',19,color=GRAY)
    c.diamond(900,640,'属于 / 拥有',110,52)
    c.line([(900,509),(900,588)]);c.text(922,540,'0..*',22)
    c.line([(896,692),(896,795)]);c.line([(904,692),(904,795)]);c.text(925,733,'1..1',22)
    c.entity(740,795,420,'出口 StationExit',[('exit_id',True),'exit_code','{ landmark_name }'])
    c.text(90,520,'业务唯一性（映射后由约束落实）',23,True)
    for i,s in enumerate(['District.name_en 唯一','Station：name_zh + 所属行政区唯一','MetroLine：中英文名称分别唯一','StationExit：所属车站 + exit_code 唯一','经过：车站 + 线路唯一；线路 + position 唯一']):c.text(90,569+i*42,s,21)
    c.text(90,826,'出口采用全局 exit_id，因此画普通实体。',21,color=GRAY)
    c.text(90,868,'地标在当前范围内仅有名称，作为多值属性。',21,color=GRAY)
    c.text(90,910,'可空值与多值集合允许为空，二者含义不同。',21,color=GRAY)
    c.line([(70,1045),(1730,1045)],color='#cbd7dc',width=1)
    c.text(70,1060,'图例：下划线=主键；菱形=联系；虚线连接属性框；{ }=多值属性；双线=全参与。',21)
    c.text(70,1100,'l..h 标在实体侧，表示该实体参与该联系的次数（Lecture 7 p.35）；0..* 保留新增空线路/未编线站点。',20,color=GRAY)
    c.save('概念ER图_Lecture7')


def relational():
    c=Canvas();c.text(65,30,'六表关系模式与外键图',36,True)
    c.text(65,88,'映射说明图｜不是 DataGrip 实库自动生成截图｜箭头从外键引用表指向被引用表',23,color=GRAY)
    # Edges first to keep them behind table boxes. Route on unoccupied lanes.
    edges=[[(730,250),(420,250)],[(1270,250),(1160,250)],
           [(730,875),(650,875),(650,345),(730,345)],[(1270,880),(1160,880)]]
    for pts in edges:
        c.line(pts)
        x,y=pts[-1];px,py=pts[-2]
        dx=1 if x>px else -1 if x<px else 0;dy=1 if y>py else -1 if y<py else 0
        c.line([(x-dx*12+dy*6,y-dy*12-dx*6),(x,y),(x-dx*12-dy*6,y-dy*12+dx*6)])
    c.entity(80,170,340,'district',[('district_id PK',True),'name_en UQ NN'])
    c.entity(730,170,430,'station',[('station_id PK',True),'district_id FK NN','name_zh NN','name_en NN','lon_mdeg NULL','lat_mdeg NULL'])
    c.entity(730,565,430,'metro_line',[('line_id PK',True),'name_zh UQ NN','name_en UQ NN'])
    # Fix edge for line_station.line_id to actual metro_line box, avoiding table bodies.
    # Additional independent lane to its top-right corner.
    c.line([(1700,250),(1740,250),(1740,540),(1020,540),(1020,565)])
    c.line([(1014,553),(1020,565),(1026,553)])
    c.entity(1270,170,430,'line_station',[('line_id PK, FK',True),('station_id PK, FK',True),'position NN','status NN','opening_year NN','first_train NULL','last_train NULL'])
    c.entity(730,800,430,'station_exit',[('exit_id PK',True),'station_id FK NN','exit_code NN'])
    c.entity(1270,800,430,'exit_landmark',[('exit_id PK, FK',True),('landmark_name PK',True)])
    c.text(80,580,'复合约束',25,True)
    notes=['station: UQ(name_zh, district_id)','line_station: PK(line_id, station_id)','line_station: UQ(line_id, position)','station_exit: UQ(station_id, exit_code)','exit_landmark: PK(exit_id, landmark_name)']
    for i,s in enumerate(notes):c.text(80,635+i*44,s,19)
    c.text(80,940,'PK=主键；FK=外键；UQ=唯一；NN=非空',21,color=GRAY)
    c.text(80,1080,'外键有向图无环：exit_landmark → station_exit → station → district；line_station → station / metro_line。',21)
    c.save('六表关系映射图')


if __name__=='__main__':
    conceptual()
    # Logical diagram is rendered separately; no change to SQL/database.
    relational()
    print(OUT)
