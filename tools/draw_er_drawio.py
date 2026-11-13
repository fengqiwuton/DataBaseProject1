"""Generate the conceptual E-R diagram in the form used on Lecture 7, slide 5.

    docs/ER_lecture7/概念ER图_drawio.drawio   draw.io (diagrams.net) native source
    docs/ER_lecture7/概念E-R图_drawio.png      exported by the diagrams.net viewer

Form copied from ZQ_Fall2026_CS307_Lecture7.pdf page 5 ("The New Running Example"):

  * entity set   = box with a light blue title band, italic attribute list underneath,
                   primary key underlined
  * relationship = light blue rhombus with an italic lower-case name
  * arrow        = at most one on that side (functional / many-to-one)
  * double line  = total participation
  * dashed line  = attaches the relationship's descriptive attributes in a plain box
  * braces       = multi-valued attribute; no l..h labels, no legend, no title inside

Every connector is strictly horizontal or vertical (orthogonal): only the rhombus
edges themselves are slanted. check_orthogonal() fails the build if that stops being
true, so a layout edit cannot silently introduce a diagonal line.

    python tools/draw_er_drawio.py
"""
import base64
import math
import pathlib
import subprocess
import urllib.parse
import xml.sax.saxutils as sax
import zlib

from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs' / 'ER_lecture7'
DRAWIO = OUT / '概念ER图_drawio.drawio'
PNG = OUT / 'E-R_project1.png'

W, H = 0, 0                     # fitted to the drawing by fit_page()
MARGIN = 36
SCALE = 3
HEAD_H, ROW_H, PAD = 36, 26, 8
SERIF = pathlib.Path('C:/Windows/Fonts')
INK = '#231f20'
HEAD_FILL = '#cdeefb'
DIAMOND_FILL = '#edf9fc'

DIAMOND_W, DIAMOND_H = 215, 96
WEAK_FRAME = 4          # 弱实体双矩形之间的间距
ROW_FONT = 12.5         # 属性行字号（含 CSV 列名标注）

# --- layout (draw.io pixels) ----------------------------------------------------------------
# Coordinates are chosen so that every connection is axis-aligned: entity attach points sit
# at the same y as the rhombus centre (horizontal runs) or the same x (vertical runs).
ENTITIES = [
    dict(id='district', title='district', x=120, y=300, w=200,
         attrs=[('district_id', 'pk', ''), ('name_en', '', 'District')]),
    dict(id='station', title='station', x=650, y=250, w=290,
         attrs=[('station_id', 'pk', ''),
                ('name_zh', '', 'Station Name / station_name'),
                ('name_en', '', 'Station Name EN / station_name_en'),
                ('lon_mdeg', '', 'latitude'), ('lat_mdeg', '', 'longitude')]),
    dict(id='line', title='line', x=1250, y=279, w=200,
         attrs=[('line_id', 'pk', ''), ('name_zh', '', 'Line Chineses'),
                ('name_en', '', 'Line En')]),
    dict(id='exit', title='exit', x=687.5, y=690, w=215,
         attrs=[('exit_code', 'partial', 'exit'), ('{landmark_name}', '', 'landmark')], weak=True),
]

DIAMONDS = [
    dict(id='station_district', title='station_district', cx=470, cy=348, w=DIAMOND_W, h=DIAMOND_H),
    dict(id='line_station', title='line_station', cx=1075, cy=340, w=DIAMOND_W, h=DIAMOND_H),
    dict(id='exit_station', title='exit_station', cx=795, cy=560, w=DIAMOND_W, h=DIAMOND_H, identifying=True),
]

REL_ATTRS = dict(id='rel_attrs', x=967.5, y=470, w=215,
                 attrs=[('position', 'Num'), ('status', 'Status'),
                        ('opening_year', 'Opening'), ('first_train', 'Start Time'),
                        ('last_train', 'End Time')])

# Endpoints are named page points from connection_points(); pair=True = total participation,
# arrow=True = "at most one" on the target side, dashed=True = relationship attributes.
EDGES = [
    dict(source='station', target='station_district',
         points=('station_left', 'station_district_right'), pair=True),
    dict(source='station_district', target='district',
         points=('station_district_left', 'district_right'), arrow=True),
    dict(source='station', target='line_station',
         points=('station_right', 'line_station_left')),
    dict(source='line_station', target='line',
         points=('line_station_right', 'line_left')),
    dict(source='exit', target='exit_station', points=('exit_top', 'exit_station_bottom'),
         pair=True),
    dict(source='exit_station', target='station',
         points=('exit_station_top', 'station_bottom'), arrow=True),
    dict(source='line_station', target='rel_attrs', points=('line_station_bottom', 'attrs_top'),
         dashed=True),
]


def geometry():
    boxes = {}
    for entity in ENTITIES:
        body_h = PAD * 2 + ROW_H * len(entity['attrs'])
        boxes[entity['id']] = dict(x=entity['x'], y=entity['y'], w=entity['w'],
                                   h=HEAD_H + body_h, head=HEAD_H, entity=entity)
    for diamond in DIAMONDS:
        boxes[diamond['id']] = dict(x=diamond['cx'] - diamond['w'] / 2,
                                    y=diamond['cy'] - diamond['h'] / 2,
                                    w=diamond['w'], h=diamond['h'], diamond=diamond)
    boxes[REL_ATTRS['id']] = dict(x=REL_ATTRS['x'], y=REL_ATTRS['y'], w=REL_ATTRS['w'],
                                  h=PAD * 2 + ROW_H * len(REL_ATTRS['attrs']), head=0)
    return boxes


def centre_x(box):
    return box['x'] + box['w'] / 2


def centre_y(box):
    return box['y'] + box['h'] / 2


def connection_points(boxes):
    """All connector endpoints, expressed once so the drawing cannot drift out of alignment."""
    district, station, line, exit_ = (boxes['district'], boxes['station'],
                                      boxes['line'], boxes['exit'])
    sd, ls, es = boxes['station_district'], boxes['line_station'], boxes['exit_station']
    attrs = boxes['rel_attrs']
    return {
        'district_right': (district['x'] + district['w'], centre_y(sd)),
        'station_district_left': (sd['x'], centre_y(sd)),
        'station_district_right': (sd['x'] + sd['w'], centre_y(sd)),
        'station_left': (station['x'], centre_y(sd)),
        'station_right': (station['x'] + station['w'], centre_y(ls)),
        'line_station_left': (ls['x'], centre_y(ls)),
        'line_station_right': (ls['x'] + ls['w'], centre_y(ls)),
        'line_left': (line['x'], centre_y(ls)),
        'station_bottom': (centre_x(station), station['y'] + station['h']),
        'exit_station_top': (centre_x(es), es['y']),
        'exit_station_bottom': (centre_x(es), es['y'] + es['h']),
                # 弱实体的连线接到外圈，而不是内框
        'exit_top': (centre_x(exit_), exit_['y'] - WEAK_FRAME),
        'line_station_bottom': (centre_x(ls), ls['y'] + ls['h']),
        'attrs_top': (centre_x(attrs), attrs['y']),
    }


def check_orthogonal(points):
    """Fail loudly if any connector ceased to be horizontal or vertical."""
    problems = []
    for edge in EDGES:
        start, end = points[edge['points'][0]], points[edge['points'][1]]
        horizontal = abs(start[1] - end[1]) < 1e-6
        vertical = abs(start[0] - end[0]) < 1e-6
        if not (horizontal or vertical):
            problems.append(f"{edge['points'][0]} -> {edge['points'][1]}: "
                            f"{start} -> {end} is diagonal")
    if problems:
        raise ValueError('Connectors must be horizontal or vertical:\n  ' + '\n  '.join(problems))


def fit_page(margin=MARGIN):
    """Translate the layout to the origin and size the page to the drawing."""
    global W, H
    boxes = geometry()
    min_x = min(b['x'] for b in boxes.values())
    min_y = min(b['y'] for b in boxes.values())
    max_x = max(b['x'] + b['w'] for b in boxes.values())
    max_y = max(b['y'] + b['h'] for b in boxes.values())
    dx, dy = margin - min_x, margin - min_y
    for entity in ENTITIES:
        entity['x'] += dx
        entity['y'] += dy
    for diamond in DIAMONDS:
        diamond['cx'] += dx
        diamond['cy'] += dy
    REL_ATTRS['x'] += dx
    REL_ATTRS['y'] += dy
    W = int(round(max_x - min_x + 2 * margin))
    H = int(round(max_y - min_y + 2 * margin))
    return W, H


def diamond_points(box):
    return [(box['x'] + box['w'] / 2, box['y']), (box['x'] + box['w'], box['y'] + box['h'] / 2),
            (box['x'] + box['w'] / 2, box['y'] + box['h']), (box['x'], box['y'] + box['h'] / 2)]


def segment_polygon_hit(a, b, polygon):
    """Point where segment a->b leaves the polygon (closest to b), else b itself."""
    best, best_t = b, 0.0
    for i in range(len(polygon)):
        p, q = polygon[i], polygon[(i + 1) % len(polygon)]
        rx, ry = b[0] - a[0], b[1] - a[1]
        sx, sy = q[0] - p[0], q[1] - p[1]
        denominator = rx * sy - ry * sx
        if abs(denominator) < 1e-9:
            continue
        t = ((p[0] - a[0]) * sy - (p[1] - a[1]) * sx) / denominator
        u = ((p[0] - a[0]) * ry - (p[1] - a[1]) * rx) / denominator
        if 0 <= t <= 1 and 0 <= u <= 1 and t > best_t:
            best, best_t = (a[0] + rx * t, a[1] + ry * t), t
    return best


def edge_segments(boxes, points, edge):
    """Concrete page segments: one connector, or two parallel ones for total participation."""
    start, end = points[edge['points'][0]], points[edge['points'][1]]
    if not edge.get('pair'):
        return [(start, end)]
    vertical = abs(start[0] - end[0]) < 1e-6
    offsets = [(-4, 0), (4, 0)] if vertical else [(0, -4), (0, 4)]
    segments = []
    target = boxes[edge['target']]
    for dx, dy in offsets:
        a = (start[0] + dx, start[1] + dy)
        b = (end[0] + dx, end[1] + dy)
        if 'diamond' in target:
            b = segment_polygon_hit(a, b, diamond_points(target))
        segments.append((a, b))
    return segments


def point_ref(boxes, element_id, point):
    """draw.io needs a fraction of the concrete cell that owns this page point."""
    box = boxes[element_id]
    if 'entity' in box and point[1] >= box['y'] + HEAD_H:
        half = dict(x=box['x'], y=box['y'] + HEAD_H, w=box['w'], h=box['h'] - HEAD_H)
        cell_id = element_id + '_body'
    elif 'entity' in box:
        half = dict(x=box['x'], y=box['y'], w=box['w'], h=HEAD_H)
        cell_id = element_id + '_head'
    else:
        half, cell_id = box, element_id
    return cell_id, ((point[0] - half['x']) / half['w'], (point[1] - half['y']) / half['h'])


# --- draw.io document ----------------------------------------------------------------------
def number(value):
    """Keep fractional geometry: rhombus centres fall on .5 px, and rounding them would
    shift the shape away from the connector endpoints computed from the exact layout."""
    text = f'{value:.4f}'.rstrip('0').rstrip('.')
    return text if text not in ('', '-0') else '0'


def cell(cell_id, value, style, x, y, w, h):
    return (f'        <mxCell id="{cell_id}" value="{sax.escape(value, {chr(34): "&quot;"})}" '
            f'style="{style}" vertex="1" parent="1">\n'
            f'          <mxGeometry x="{number(x)}" y="{number(y)}" width="{number(w)}" '
            f'height="{number(h)}" as="geometry"/>\n'
            f'        </mxCell>\n')


def drawio_xml():
    head_style = (f'rounded=0;whiteSpace=wrap;html=1;fillColor={HEAD_FILL};strokeColor={INK};'
                  'fontFamily=Times New Roman;fontStyle=2;fontSize=14;verticalAlign=middle;align=center;')
    body_style = f'rounded=0;whiteSpace=wrap;html=1;fillColor=#ffffff;strokeColor={INK};'
    row_style = (f'text;html=1;strokeColor=none;fillColor=none;align=left;verticalAlign=middle;'
                 f'fontFamily=Times New Roman;fontStyle=2;fontSize={ROW_FONT};spacingLeft=4;')
    diamond_style = (f'rhombus;whiteSpace=wrap;html=1;fillColor={DIAMOND_FILL};strokeColor={INK};'
                     'fontFamily=Times New Roman;fontStyle=2;fontSize=13;verticalAlign=middle;')

    body = []
    for entity in ENTITIES:
        if entity.get('weak'):
            # 弱实体：外套一圈无填充矩形，与实体自身的边框构成双矩形
            # （draw.io 的 double=1 只对菱形生效，矩形需要这样画）
            body.append(cell(entity['id'] + '_frame', '',
                             f'rounded=0;html=1;fillColor=none;strokeColor={INK};',
                             entity['x'] - WEAK_FRAME, entity['y'] - WEAK_FRAME,
                             entity['w'] + 2 * WEAK_FRAME,
                             HEAD_H + PAD * 2 + ROW_H * len(entity['attrs']) + 2 * WEAK_FRAME))
        body.append(cell(entity['id'] + '_head', entity['title'], head_style,
                         entity['x'], entity['y'], entity['w'], HEAD_H))
        body_h = PAD * 2 + ROW_H * len(entity['attrs'])
        body.append(cell(entity['id'] + '_body', '', body_style,
                         entity['x'], entity['y'] + HEAD_H, entity['w'], body_h))
        for index, (name, mark, csv) in enumerate(entity['attrs']):
            if mark == 'pk':
                core = f'<u>{name}</u>'                        # 主键：实线下划线
            elif mark == 'partial':
                # 弱实体的部分键：虚线下划线（HTML 标签内联样式）
                core = f'<span style="border-bottom:1px dashed {INK};">{name}</span>'
            else:
                core = name
            # 列名后标注该列的 CSV 来源列（灰色），满足"CSV 列要体现在 ER 图里"
            label = core + (f'<span style="color:#5b6f7a;">（{csv}）</span>' if csv else '')
            body.append(cell(f'{entity["id"]}_attr_{index + 1}', label, row_style,
                             entity['x'] + 6, entity['y'] + HEAD_H + PAD + ROW_H * index,
                             entity['w'] - 12, ROW_H))

    for diamond in DIAMONDS:
        # 识别联系用双菱形
        double = 'double=1;' if diamond.get('identifying') else ''
        body.append(cell(diamond['id'], diamond['title'], double + diamond_style,
                         diamond['cx'] - diamond['w'] / 2, diamond['cy'] - diamond['h'] / 2,
                         diamond['w'], diamond['h']))

    body.append(cell('rel_attrs', '', body_style, REL_ATTRS['x'], REL_ATTRS['y'], REL_ATTRS['w'],
                     PAD * 2 + ROW_H * len(REL_ATTRS['attrs'])))
    for index, (name, csv) in enumerate(REL_ATTRS['attrs']):
        body.append(cell(f'rel_attr_{index + 1}',
                         name + f'<span style="color:#5b6f7a;">（{csv}）</span>', row_style,
                         REL_ATTRS['x'] + 6, REL_ATTRS['y'] + PAD + ROW_H * index,
                         REL_ATTRS['w'] - 12, ROW_H))

    plain = f'endArrow=none;html=1;strokeColor={INK};strokeWidth=1.5;'
    arrow = f'endArrow=classic;endFill=1;endSize=7;html=1;strokeColor={INK};strokeWidth=1.5;'
    dashed = f'endArrow=none;dashed=1;html=1;strokeColor={INK};strokeWidth=1.2;'
    boxes = geometry()
    points = connection_points(boxes)
    check_orthogonal(points)
    number = 0
    for edge in EDGES:
        base = dashed if edge.get('dashed') else arrow if edge.get('arrow') else plain
        for a, b in edge_segments(boxes, points, edge):
            source_cell, source_fraction = point_ref(boxes, edge['source'], a)
            target_cell, target_fraction = point_ref(boxes, edge['target'], b)
            number += 1
            style = (base + f'exitX={source_fraction[0]:.9f};exitY={source_fraction[1]:.9f};'
                            f'entryX={target_fraction[0]:.9f};entryY={target_fraction[1]:.9f};'
                            'exitDx=0;exitDy=0;entryDx=0;entryDy=0;'
                            # use the given points verbatim: skip the second projection onto the
                            # rhombus perimeter, so every connector stays exactly horizontal/vertical
                            'exitPerimeter=0;entryPerimeter=0;')
            body.append(
                f'        <mxCell id="edge_{number}" style="{style}" edge="1" parent="1" '
                f'source="{source_cell}" target="{target_cell}">\n'
                f'          <mxGeometry relative="1" as="geometry"/>\n'
                f'        </mxCell>\n')

    return ('<mxfile host="app.diagrams.net" agent="tools/draw_er_drawio.py" version="24.7.17" type="device">\n'
            '  <diagram id="metro-conceptual-er" name="概念 E-R 图">\n'
            f'    <mxGraphModel dx="{W}" dy="{H}" grid="0" gridSize="10" guides="1" tooltips="1" '
            'connect="1" arrows="1" fold="1" page="1" pageScale="1" '
            f'pageWidth="{W}" pageHeight="{H}" math="0" shadow="0">\n'
            '      <root>\n'
            '        <mxCell id="0"/>\n'
            '        <mxCell id="1" parent="0"/>\n'
            + ''.join(body) +
            '      </root>\n'
            '    </mxGraphModel>\n'
            '  </diagram>\n'
            '</mxfile>\n')


# --- offline renderer (fallback only; the PNG is normally exported by draw.io) ---------------
def font(size, bold=False):
    name = 'timesbd.ttf' if bold else 'timesi.ttf'
    path = SERIF / name
    if path.exists():
        return ImageFont.truetype(str(path), int(size * SCALE))
    return ImageFont.load_default()


def render_png():
    image = Image.new('RGB', (W * SCALE, H * SCALE), 'white')
    draw = ImageDraw.Draw(image)

    def s(value):
        return value * SCALE

    def segment(a, b, colour=INK, width=1.5, dashed=False):
        x1, y1, x2, y2 = s(a[0]), s(a[1]), s(b[0]), s(b[1])
        w = max(1, int(round(width * SCALE)))
        if not dashed:
            draw.line([(x1, y1), (x2, y2)], fill=colour, width=w)
            return
        total = math.hypot(x2 - x1, y2 - y1) or 1
        step, offset = 7 * SCALE, 0.0
        while offset < total:
            end = min(offset + step * 0.55, total)
            draw.line([(x1 + (x2 - x1) * offset / total, y1 + (y2 - y1) * offset / total),
                       (x1 + (x2 - x1) * end / total, y1 + (y2 - y1) * end / total)],
                      fill=colour, width=w)
            offset += step

    def arrow_head(a, b, size=7):
        angle = math.atan2(b[1] - a[1], b[0] - a[0])
        length = size * SCALE
        spread = math.radians(24)
        tip = (s(b[0]), s(b[1]))
        left = (tip[0] - length * math.cos(angle - spread), tip[1] - length * math.sin(angle - spread))
        right = (tip[0] - length * math.cos(angle + spread), tip[1] - length * math.sin(angle + spread))
        draw.polygon([tip, left, right], fill=INK)

    def rect(x, y, w, h, fill, stroke=INK, width=1.5):
        draw.rectangle([s(x), s(y), s(x + w), s(y + h)], fill=fill, outline=stroke,
                       width=max(1, int(round(width * SCALE))))

    def text(x, y, value, size, colour=INK, anchor='lm', underline=None):
        f = font(size)
        draw.text((s(x), s(y)), value, font=f, fill=colour, anchor=anchor)
        if underline:
            width = draw.textlength(value, font=f)
            left = s(x) - width / 2 if anchor == 'mm' else s(x)
            y_line = s(y) + size * SCALE * 0.42
            thickness = max(1, int(round(SCALE * 0.8)))
            if underline == 'dashed':        # 弱实体的部分键：虚线下划线
                dash, gap, cursor = 4 * SCALE, 3 * SCALE, left
                while cursor < left + width:
                    draw.line([(cursor, y_line), (min(cursor + dash, left + width), y_line)],
                              fill=colour, width=thickness)
                    cursor += dash + gap
            else:                            # 主键：实线下划线
                draw.line([(left, y_line), (left + width, y_line)],
                          fill=colour, width=thickness)

    def diamond_shape(cx, cy, w, h, title, identifying=False):
        points = [(s(cx - w / 2), s(cy)), (s(cx), s(cy - h / 2)), (s(cx + w / 2), s(cy)),
                  (s(cx), s(cy + h / 2))]
        draw.polygon(points, fill=DIAMOND_FILL, outline=INK)
        draw.line(points + [points[0]], fill=INK, width=max(1, int(round(1.5 * SCALE))))
        if identifying:
            # 识别联系：内侧再画一圈菱形，形成双菱形
            inset = 4
            inner = [(s(cx - w / 2 + inset), s(cy)), (s(cx), s(cy - h / 2 + inset)),
                     (s(cx + w / 2 - inset), s(cy)), (s(cx), s(cy + h / 2 - inset))]
            draw.line(inner + [inner[0]], fill=INK, width=max(1, int(round(1.5 * SCALE))))
        text(cx, cy, title, 13, anchor='mm')

    boxes = geometry()
    points = connection_points(boxes)
    check_orthogonal(points)
    for edge in EDGES:
        for a, b in edge_segments(boxes, points, edge):
            segment(a, b, dashed=bool(edge.get('dashed')), width=1.2 if edge.get('dashed') else 1.5)
            if edge.get('arrow'):
                arrow_head(a, b)

    def _row(left, centre, name, mark, csv):
        """属性行：列名（主键实线/部分键虚线）+ 灰色（CSV 列名）。"""
        f = font(ROW_FONT)
        draw.text((s(left), s(centre)), name, font=f, fill=INK, anchor='lm')
        width_name = draw.textlength(name, font=f)
        y_line = s(centre) + ROW_FONT * SCALE * 0.42
        thickness = max(1, int(round(SCALE * 0.8)))
        if mark == 'pk':
            draw.line([(s(left), y_line), (s(left) + width_name, y_line)],
                      fill=INK, width=thickness)
        elif mark == 'partial':
            dash, gap, cursor = 4 * SCALE, 3 * SCALE, s(left)
            while cursor < s(left) + width_name:
                draw.line([(cursor, y_line), (min(cursor + dash, s(left) + width_name), y_line)],
                          fill=INK, width=thickness)
                cursor += dash + gap
        if csv:
            draw.text((s(left) + width_name, s(centre)), f'（{csv}）', font=f,
                      fill='#5b6f7a', anchor='lm')

    for entity in ENTITIES:
        box = boxes[entity['id']]
        body_top = box['y'] + HEAD_H
        body_h = box['h'] - HEAD_H
        draw.rectangle([s(box['x']), s(box['y']), s(box['x'] + box['w']), s(body_top)],
                       fill=HEAD_FILL)
        draw.rectangle([s(box['x']), s(body_top), s(box['x'] + box['w']), s(body_top + body_h)],
                       fill='white')
        rect(box['x'], box['y'], box['w'], box['h'], None)
        if entity.get('weak'):
            # 弱实体：外侧再套一圈，形成双矩形
            rect(box['x'] - 4, box['y'] - 4, box['w'] + 8, box['h'] + 8, None)
        segment((box['x'], body_top), (box['x'] + box['w'], body_top))
        text(box['x'] + box['w'] / 2, box['y'] + HEAD_H / 2, entity['title'], 14, anchor='mm')
        for index, (name, mark, csv) in enumerate(entity['attrs']):
            centre = body_top + PAD + ROW_H * index + ROW_H / 2
            _row(box['x'] + 8, centre, name, mark, csv)

    for diamond_spec in DIAMONDS:
        diamond_shape(diamond_spec['cx'], diamond_spec['cy'], diamond_spec['w'],
                      diamond_spec['h'], diamond_spec['title'],
                      identifying=bool(diamond_spec.get('identifying')))

    box = boxes[REL_ATTRS['id']]
    rect(box['x'], box['y'], box['w'], box['h'], 'white')
    for index, (name, csv) in enumerate(REL_ATTRS['attrs']):
        centre = box['y'] + PAD + ROW_H * index + ROW_H / 2
        _row(box['x'] + 8, centre, name, '', csv)

    image.save(PNG, 'PNG', optimize=True)
    return PNG


# --- draw.io export (authoritative PNG) ----------------------------------------------------
EDGE_CANDIDATES = [
    pathlib.Path(r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'),
    pathlib.Path(r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'),
]


def viewer_url(xml):
    """diagrams.net viewer link: base64(deflateRaw(encodeURIComponent(xml))) behind 'R'."""
    uri = urllib.parse.quote(xml, safe="!~*'()")
    compressor = zlib.compressobj(9, zlib.DEFLATED, -15)
    raw = compressor.compress(uri.encode('ascii')) + compressor.flush()
    payload = 'R' + urllib.parse.quote(base64.b64encode(raw).decode('ascii'), safe='')
    return 'https://viewer.diagrams.net/?lightbox=1&nav=0&edit=_blank&page=1#' + payload


def ink_bbox(image):
    from PIL import ImageChops
    ink = ImageChops.difference(image, Image.new('RGB', image.size, 'white'))
    mask = ink.convert('L').point(lambda value: 255 if value > 6 else 0)
    return mask.getbbox()


def export_with_drawio(scale=SCALE, margin=26):
    """Render the .drawio in diagrams.net's own viewer with headless Edge, then crop."""
    edge = next((path for path in EDGE_CANDIDATES if path.exists()), None)
    if edge is None:
        print('headless Edge not found; falling back to the offline renderer')
        return False
    scratch = ROOT / '.runtime'
    scratch.mkdir(exist_ok=True)
    shot = scratch / 'drawio_export.png'
    url = viewer_url(DRAWIO.read_text(encoding='utf-8'))
    window = f'{W + 80},{H + 80}'
    for budget in (20000, 45000):
        if shot.exists():
            shot.unlink()
        subprocess.run([str(edge), '--headless=new', '--disable-gpu', '--no-first-run',
                        '--hide-scrollbars', f'--force-device-scale-factor={scale}',
                        f'--window-size={window}', f'--virtual-time-budget={budget}',
                        f'--screenshot={shot}', url], capture_output=True)
        if not shot.exists():
            continue
        image = Image.open(shot).convert('RGB')
        box = ink_bbox(image)
        if box is None:
            continue
        pad = margin * scale
        image.crop((max(0, box[0] - pad), max(0, box[1] - pad),
                    min(image.width, box[2] + pad), min(image.height, box[3] + pad))
                   ).save(PNG, 'PNG', optimize=True)
        return True
    return False


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fit_page()
    DRAWIO.write_text(drawio_xml(), encoding='utf-8')
    print(f'wrote {DRAWIO.relative_to(ROOT)}')
    if export_with_drawio():
        print(f'wrote {PNG.relative_to(ROOT)}  (exported by the draw.io viewer)')
    else:
        png = render_png()
        print(f'wrote {png.relative_to(ROOT)}  (offline fallback renderer)')


if __name__ == '__main__':
    main()
