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
        if under:self.line([(left,y+size+5),(left+width,y+size+5)],dashed=under=='partial',width=1)
    def entity(self,x,y,w,title,rows,weak=False):
        height=58+len(rows)*38+16
        self.rect(x,y,w,height);self.rect(x,y,w,52,BLUE)
        if weak:
            inset=6
            self.line([(x+inset,y+inset),(x+w-inset,y+inset),(x+w-inset,y+height-inset),
                       (x+inset,y+height-inset),(x+inset,y+inset)])
        self.text(x+w/2,y+10,title,24,True,True)
        for i,row in enumerate(rows):
            s,key=row if isinstance(row,tuple) else (row,False)
            self.text(x+20,y+65+i*38,s,23,under=key)
        return height
    def polygon(self,pts,fill):
        self.svg.append('<polygon points="'+' '.join(f'{a},{b}' for a,b in pts)+f'" fill="{fill}" stroke="{EDGE}" stroke-width="2"/>')
        self.d.polygon([(a*2,b*2) for a,b in pts],fill=fill,outline=EDGE,width=4)
    def diamond(self,x,y,title,rx=95,ry=52,identifying=False):
        self.polygon([(x-rx,y),(x,y-ry),(x+rx,y),(x,y+ry)],'#f2f7f9')
        if identifying:
            self.polygon([(x-rx+12,y),(x,y-ry+6),(x+rx-12,y),(x,y+ry-6)],'#f2f7f9')
        self.text(x,y-17,title,23,center=True)
    def arrow(self,start,end):
        self.line([start,end])
        x,y=end; dx=x-start[0]; dy=y-start[1]; length=(dx*dx+dy*dy)**.5
        dx/=length; dy/=length
        self.polygon([end,(x-dx*15+dy*5,y-dy*15-dx*5),
                      (x-dx*15-dy*5,y-dy*15+dx*5)],EDGE)
    def save(self,name):
        OUT.mkdir(parents=True,exist_ok=True)
        (OUT/(name+'.svg')).write_text('\n'.join(self.svg)+ '\n</svg>',encoding='utf-8')
        self.im.save(OUT/(name+'.png'))


def conceptual():
    c=Canvas()
    c.text(70,35,'深圳地铁概念 E-R 图',36,True)
    c.text(70,95,'Lecture 7 表示法｜属性后的「←」标注 CSV 原列名',24,color=GRAY)
    c.entity(70,180,285,'行政区 District',[('district_id',True),'name_en ← District'])
    station_height=c.entity(620,180,565,'车站 Station',[('station_id',True),'name_zh ← Station Name / station_name',
                         'name_en ← Station Name EN / station_name_en','longitude ← latitude¹','latitude ← longitude¹'])
    c.entity(1430,180,320,'线路 MetroLine',[('line_id',True),'name_zh ← Line Chineses','name_en ← Line En'])
    c.diamond(500,263,'归属行政区',82,48)
    c.arrow((418,263),(355,263))
    c.line([(579,259),(620,259)]);c.line([(579,267),(620,267)])
    c.text(361,220,'0..*',22);c.text(575,220,'1..1',22)
    c.text(500,320,'1 : N',22,center=True)
    c.diamond(1307,300,'经过',69,48)
    c.line([(1185,300),(1238,300)]);c.line([(1376,300),(1430,300)])
    c.text(1191,257,'0..*',22);c.text(1382,257,'0..*',22)
    c.text(1325,360,'M : N',22)
    c.rect(1210,470,510,236)
    for i,s in enumerate(['position ← Num','status ← Status','opening_year ← Opening',
                          'first_train ← Start Time','last_train ← End Time']):c.text(1232,486+i*41,s,23)
    c.line([(1307,348),(1307,470)],dashed=True)
    c.diamond(885,579,'拥有',99,52,identifying=True)
    c.arrow((885,527),(885,180+station_height))
    c.text(909,475,'0..*',22)
    c.line([(881,629),(881,734)]);c.line([(889,629),(889,734)]);c.text(908,666,'1..1',22)
    c.text(1010,561,'1 : N',22)
    c.entity(635,734,500,'出口 StationExit（弱实体）',[('exit_code', 'partial'),'{ landmark_name } ← landmark'],weak=True)
    c.text(767,799,'← exit',23)
    c.text(70,445,'怎样识别一个出口？',26,True)
    c.text(70,495,'出口编号可跨站重复；同一站内唯一。',23)
    c.text(70,538,'完整标识 = 所属车站 ＋ 出口编号。',23)
    c.text(70,581,'「拥有」是识别联系，每个出口恰属一站。',23)
    c.text(70,655,'「经过」的站序与时刻取决于车站和线路。',23)
    c.text(70,698,'尚未编线的站与空线路都允许存在。',23)
    c.text(70,926,'¹ 源 CSV 的经纬度表头与数值范围相反，按数值含义映射；坐标可空。',23)
    c.text(70,967,'首末班时间可空；出口可以没有地标。',23)
    c.line([(70,1024),(1730,1024)],color='#cbd7dc',width=1)
    c.text(70,1047,'实线下划线＝主键；虚线下划线＝部分键；双矩形＝弱实体；双菱形＝识别联系。',23)
    c.text(70,1088,'箭头指向「一」端；双线＝全参与；实体侧 l..h＝参与次数；{ }＝多值属性。',23)
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
