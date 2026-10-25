"""Stand controller PS5 · costruzione dei pezzi dal modello originale.

Uso (dalla cartella del progetto):
    blender -b --factory-startup --python blender/costruisci.py

Legge originale/base_originale.stl e originale/holder_originale.stl (mesh dei 3mf),
scrive blender/Stand_Controller_PS5.blend, gli STL in stl/ (orientati per la stampa)
e dati/geometria.json.

Coordinate di montaggio: X verso il retro (i controller stanno a -X), Y in larghezza,
Z in alto; base da Z 0 a 8, centro della base nell'origine.
"""
import bpy, bmesh, math, json, os
from mathutils import Matrix, Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ORIG = os.path.join(ROOT, "originale")
STL = os.path.join(ROOT, "stl")

# --- misure -------------------------------------------------------------
BASE_TOP = 8.0
BASE_GROW = 5.0                          # raggio in più del piatto rispetto all'originale (Ø190)
SLOT_GAP, SLOT_DEEPER = 0.15, 0.3        # gioco per lato della sede del tenone e profondità in più
# due viti autofilettanti a testa svasata 4 × 20 da sotto, nel piede pieno davanti al tenone
SCREWS = [(-24.0, -20.0), (-24.0, 20.0)]
SCREW_HOLE, SCREW_CSK = 4.5, 8.6         # foro passante nella base e svasatura a 90°
SCREW_PILOT, SCREW_PILOT_DEPTH = 3.3, 16.0   # foro guida nel montante, dal piano della base
# filetto: il fondo del portapenne è la vite, la base ha la madrevite incassata
TH_X, TH_Y = -63.5, 0.0
TH_R, TH_P, TH_H = 20.5, 2.5, 1.25      # raggio esterno della vite, passo, profondità
TH_RECESS = 6.0                          # profondità della madrevite nella base (fondo da 2 mm)
TH_LEN = 5.7                             # lunghezza della vite sotto il portapenne
TH_GAP = 0.4                             # gioco radiale della madrevite
# portapenne
PP_R, PP_WALL, PP_H = 24.0, 2.2, 90.0    # raggio a metà altezza, parete, altezza
PP_R_END, PP_RIM = 22.5, 3.0             # raggio al piede e in cima, spessore del bordo
PP_HOLE_V0, PP_HOLE_V1 = 15.5, 83.5      # fascia forata (dal piede): sotto restano piene le punte delle penne
PP_CELL, PP_STRUT = 7.5, 2.0             # passo delle celle di Voronoi e larghezza delle nervature
PP_FLOOR = 2.0                           # fondo interno sopra la base (sotto c'è la vite piena)
# custodia HUAWEI FreeBuds 3: Ø60,9 × 21,8 mm (scheda Huawei)
FB_D, FB_T = 60.9, 21.8
FB_R = FB_D / 2 + 0.55                   # raggio della culla
FB_W = FB_T + 1.2                        # larghezza della fessura
FB_WALL = 2.8
FB_X0 = 31.5                             # inizio culla (retro della colonna a X 28,4)
FB_FLOOR = 2.0                           # fondo della culla sopra la base
FB_TOP = 34.0                            # altezza delle sponde
FB_HALF_Y = FB_R + 3.5
# taglio del braccio basso, nel profilo del holder (x, y prima della rotazione)
ARM_CUT = [(-130, -75), (-57.65, -75), (-45.0, -28.0), (-130, -28.0)]

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.unit_settings.scale_length = 0.001
sc.unit_settings.length_unit = 'MILLIMETERS'


def coll(name, hide=False):
    c = bpy.data.collections.new(name)
    sc.collection.children.link(c)
    c.hide_viewport = c.hide_render = hide
    return c


C_ORIG, C_STAMPA, C_RIF = coll("ORIGINALE", True), coll("PEZZI_MONTATI"), coll("RIFERIMENTI")


def import_stl(path, name, c):
    bpy.ops.wm.stl_import(filepath=path)
    o = bpy.context.selected_objects[0]
    o.name = o.data.name = name
    for u in o.users_collection:
        u.objects.unlink(o)
    c.objects.link(o)
    return o


def obj_from_bm(bm, name, c):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me)
    c.objects.link(o)
    return o


def boolean(target, tool, op, tolerant=False):
    m = target.modifiers.new("b", 'BOOLEAN')
    m.operation, m.object, m.solver = op, tool, 'EXACT'
    m.use_hole_tolerant = tolerant
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(tool)


def prism(poly, z0, z1, name, c):
    bm = bmesh.new()
    bot = [bm.verts.new((x, y, z0)) for x, y in poly]
    top = [bm.verts.new((x, y, z1)) for x, y in poly]
    bm.faces.new(bot[::-1]); bm.faces.new(top)
    n = len(poly)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((bot[i], bot[j], top[j], top[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return obj_from_bm(bm, name, c)


def box(x0, x1, y0, y1, z0, z1, name, c):
    return prism([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], z0, z1, name, c)


def radial_solid(rfun, z0, z1, cx, cy, name, c, seg=144, dz=0.1):
    """Solido chiuso con raggio r(theta, z): filetti, cilindri, smussi."""
    bm = bmesh.new()
    nz = max(2, int(round((z1 - z0) / dz)) + 1)
    rings = []
    for k in range(nz):
        z = z0 + (z1 - z0) * k / (nz - 1)
        ring = []
        for i in range(seg):
            t = 2 * math.pi * i / seg
            r = rfun(t, z)
            ring.append(bm.verts.new((cx + r * math.cos(t), cy + r * math.sin(t), z)))
        rings.append(ring)
    for k in range(nz - 1):
        a, b = rings[k], rings[k + 1]
        for i in range(seg):
            j = (i + 1) % seg
            bm.faces.new((a[i], a[j], b[j], b[i]))
    cb = bm.verts.new((cx, cy, z0)); ct = bm.verts.new((cx, cy, z1))
    for i in range(seg):
        j = (i + 1) % seg
        bm.faces.new((cb, rings[0][j], rings[0][i]))
        bm.faces.new((ct, rings[-1][i], rings[-1][j]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return obj_from_bm(bm, name, c)


def thread_r(t, z, r_out, z_ref):
    """Profilo trapezoidale a 60°, filetto destro: cresta 0,24 p, fianchi 0,29 p."""
    p, h = TH_P, TH_H
    u = ((z - z_ref) - p * t / (2 * math.pi)) % p / p
    crest, flank = 0.24, 0.29
    if u < crest:
        f = 1.0
    elif u < crest + flank:
        f = 1 - (u - crest) / flank
    elif u < 1 - flank:
        f = 0.0
    else:
        f = (u - (1 - flank)) / flank
    return r_out - h + h * f


# --- originali in posa di montaggio ------------------------------------
base_o = import_stl(os.path.join(ORIG, "base_originale.stl"), "ORIG_base", C_ORIG)
hold_o = import_stl(os.path.join(ORIG, "holder_originale.stl"), "ORIG_holder", C_ORIG)

# piede del holder: tenone X -34,25…-1,35, spalla che appoggia sulla base
hv = [v.co for v in hold_o.data.vertices]
ten_x = [v.x for v in hv if v.y < -123]
tx = -(min(ten_x) + max(ten_x)) / 2
shoulder = min(v.y for v in hv if v.x < -38 and v.y < -100)
HOLD_M = Matrix.Translation((tx, 0, BASE_TOP - shoulder)) @ Matrix.Rotation(math.radians(90), 4, 'X')
BASE_M = Matrix.Translation((0, 0, 4.0))

# --- P02 sostegno: holder senza il braccio basso -----------------------
sup = hold_o.copy(); sup.data = hold_o.data.copy()
sup.name = sup.data.name = "P02_Sostegno"
C_STAMPA.objects.link(sup)
cut = prism(ARM_CUT, -40, 40, "taglio_braccio", C_STAMPA)
boolean(sup, cut, 'DIFFERENCE')
# l'STL originale ha un triangolo degenere (3 spigoli aperti a Y 46,4): lo dissolvo
bm = bmesh.new(); bm.from_mesh(sup.data)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
near = [v for v in bm.verts if (v.co.xy - Vector((-12.58, 46.41))).length < 0.1]
bmesh.ops.remove_doubles(bm, verts=near, dist=0.03)
bmesh.ops.dissolve_degenerate(bm, dist=0.001, edges=bm.edges)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(sup.data); bm.free()
sup.data.transform(HOLD_M)
# fori guida per le viti autofilettanti, nel piede pieno davanti al tenone
for sx, sy in SCREWS:
    boolean(sup, radial_solid(lambda t, z: SCREW_PILOT / 2, BASE_TOP - 1.0, BASE_TOP + SCREW_PILOT_DEPTH, sx, sy,
                              "foro_guida", C_STAMPA, seg=32, dz=30), 'DIFFERENCE')

# --- P01 base: perno filettato + culla FreeBuds ------------------------
base = base_o.copy(); base.data = base_o.data.copy()
base.name = base.data.name = "P01_Base"
C_STAMPA.objects.link(base)
base.data.transform(BASE_M)
# piatto da Ø180 a Ø190: sposto in fuori solo il bordo (raccordo R2 fra r 88 e 90);
# dentro r 50 ci sono solo gli angoli della sede (r 38), che restano dove sono
for v in base.data.vertices:
    r = v.co.xy.length
    if r > 50:
        v.co.xy *= (r + BASE_GROW) / r

# sede del tenone: 0,15 mm di gioco per lato e 0,3 mm più profonda, così il montante entra a mano
# e appoggia sempre con la spalla sul piano (nell'originale il gioco è zero)
tv = [v.co for v in sup.data.vertices if v.co.z < BASE_TOP - 0.01]
tx0, tx1 = min(v.x for v in tv), max(v.x for v in tv)
ty0, ty1 = min(v.y for v in tv), max(v.y for v in tv)
tz0 = min(v.z for v in tv)
boolean(base, box(tx0 - SLOT_GAP, tx1 + SLOT_GAP, ty0 - SLOT_GAP, ty1 + SLOT_GAP,
                  tz0 - SLOT_DEEPER, BASE_TOP + 1.0, "sede_giocata", C_STAMPA), 'DIFFERENCE')
# fori passanti con svasatura a 90° sotto la base, per le viti a testa svasata
for sx, sy in SCREWS:
    boolean(base, radial_solid(lambda t, z: SCREW_HOLE / 2, -1.0, BASE_TOP + 1.0, sx, sy,
                               "foro_vite", C_STAMPA, seg=48, dz=20), 'DIFFERENCE')
    boolean(base, radial_solid(lambda t, z: SCREW_CSK / 2 - z, -0.5, SCREW_CSK / 2 - SCREW_HOLE / 2, sx, sy,
                               "svasatura", C_STAMPA, seg=48, dz=0.25), 'DIFFERENCE')

def female_r(t, z):
    r = thread_r(t, z, TH_R, BASE_TOP) + TH_GAP                  # stessa fase della vite
    return max(r, TH_R + TH_GAP + 0.3 - (BASE_TOP - z))          # invito a 45° alla bocca
sock = radial_solid(female_r, BASE_TOP - TH_RECESS, BASE_TOP + 1.0, TH_X, TH_Y, "madrevite", C_STAMPA)
boolean(base, sock, 'DIFFERENCE')

fx0, fx1 = FB_X0, FB_X0 + 2 * FB_WALL + FB_W
def rounded_rect(x0, x1, y0, y1, r, n=6):
    pts = []
    for cx, cy, a0 in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for k in range(n + 1):
            a = math.radians(a0 + 90 * k / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts

def x_cylinder(r, length, cx, cz, name):
    bpy.ops.mesh.primitive_cylinder_add(vertices=180, radius=r, depth=length,
                                        location=(cx, 0, cz), rotation=(0, math.radians(90), 0))
    o = bpy.context.active_object
    o.name = name
    for u in o.users_collection:
        u.objects.unlink(o)
    C_STAMPA.objects.link(o)
    return o

cradle = prism(rounded_rect(fx0, fx1, -FB_HALF_Y, FB_HALF_Y, 3.0), BASE_TOP - 1.0, BASE_TOP + FB_TOP, "culla", C_STAMPA)
boolean(base, cradle, 'UNION')
fb_cz = BASE_TOP + FB_FLOOR + FB_R
boolean(base, x_cylinder(FB_R, FB_W, (fx0 + fx1) / 2, fb_cz, "tasca"), 'DIFFERENCE')
# intaglio a U nelle due sponde: la custodia resta in vista e si spinge fuori col dito
FB_NOTCH = 17.0
boolean(base, x_cylinder(FB_NOTCH, fx1 - fx0 + 2, (fx0 + fx1) / 2, fb_cz, "intaglio"), 'DIFFERENCE')
boolean(base, box(fx0 - 1, fx1 + 1, -FB_NOTCH, FB_NOTCH, fb_cz, fb_cz + 40, "intaglio_alto", C_STAMPA), 'DIFFERENCE')
# smusso di 1 mm sugli spigoli alti della culla
bm = bmesh.new(); bm.from_mesh(base.data)
edges = [e for e in bm.edges if all(abs(v.co.z - (BASE_TOP + FB_TOP)) < 1e-3 for v in e.verts)
         and all(v.co.x > fx0 - 0.01 for v in e.verts)
         and abs(e.verts[0].co.x - e.verts[1].co.x) + abs(e.verts[0].co.y - e.verts[1].co.y) > 2.0]
bmesh.ops.bevel(bm, geom=edges, offset=0.8, segments=1, affect='EDGES')
# il piano superiore esce dalle booleane a ventaglio, con schegge lunghe dal perno agli angoli
# della sede (si vedono come righe nella guida): lo ritriangolo con spigoli scambiati alla Delaunay
# con punti interni: spezzo gli spigoli interni lunghi (il contorno resta com'è)
def top_faces():
    return [f for f in bm.faces if f.normal.z > 0.999 and all(abs(v.co.z - BASE_TOP) < 1e-4 for v in f.verts)]
for _ in range(8):
    top = set(top_faces())
    bmesh.ops.triangulate(bm, faces=list(top), quad_method='BEAUTY', ngon_method='BEAUTY')
    top = set(top_faces())
    inner = [e for e in {e for f in top for e in f.edges} if len(e.link_faces) == 2 and all(f in top for f in e.link_faces)]
    bmesh.ops.beautify_fill(bm, faces=list(top), edges=inner)
    top = set(top_faces())
    inner = [e for e in {e for f in top for e in f.edges} if len(e.link_faces) == 2 and all(f in top for f in e.link_faces)]
    long_e = [e for e in inner if e.calc_length() > 6.0]
    if not long_e:
        break
    bmesh.ops.subdivide_edges(bm, edges=long_e, cuts=1)
bmesh.ops.triangulate(bm, faces=top_faces(), quad_method='BEAUTY', ngon_method='BEAUTY')
bm.to_mesh(base.data); bm.free()

# --- P03 portapenne -----------------------------------------------------
def lathe(profile, cx, cy, name, c, seg=180):
    """Rivoluzione di un profilo chiuso (r, z) attorno a Z; i punti con r = 0 sono poli."""
    bm = bmesh.new()
    rings = []
    for r, z in profile:
        if r == 0:
            rings.append([bm.verts.new((cx, cy, z))] * seg)
        else:
            rings.append([bm.verts.new((cx + r * math.cos(2 * math.pi * i / seg),
                                        cy + r * math.sin(2 * math.pi * i / seg), z)) for i in range(seg)])
    n = len(rings)
    for k in range(n):
        a, b = rings[k], rings[(k + 1) % n]
        for i in range(seg):
            j = (i + 1) % seg
            q = list(dict.fromkeys((a[i], a[j], b[j], b[i])))
            if len(q) >= 3:
                bm.faces.new(q)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return obj_from_bm(bm, name, c)

def pp_radius(zr):
    """Botte: Ø45 alle estremità, Ø48 a metà altezza (zr dal piede del portapenne)."""
    return PP_R_END + (PP_R - PP_R_END) * math.sin(math.pi * min(max(zr, 0), PP_H) / PP_H)


def voronoi_holes(circ, v0, v1, spacing, strut, seed=7):
    """Celle di Voronoi sulla parete srotolata (u lungo la circonferenza, periodico; v in altezza),
    ristrette di metà nervatura per lato, tagliate fra v0 e v1 e arrotondate con Chaikin."""
    import random
    rnd = random.Random(seed)
    pts = []
    for _ in range(20000):                                   # Poisson disk a lanci
        p = (rnd.uniform(0, circ), rnd.uniform(v0 - spacing, v1 + spacing))
        if all(min(abs(p[0] - q[0]), circ - abs(p[0] - q[0])) ** 2 + (p[1] - q[1]) ** 2 >= spacing ** 2 for q in pts):
            pts.append(p)
    def clip(poly, n, c):                                    # tiene n·p <= c
        out = []
        for i, a in enumerate(poly):
            b = poly[(i + 1) % len(poly)]
            da, db = n[0] * a[0] + n[1] * a[1] - c, n[0] * b[0] + n[1] * b[1] - c
            if da <= 0:
                out.append(a)
            if (da < 0) != (db < 0) and da != db:
                t = da / (da - db)
                out.append((a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])))
        return out
    holes = []
    for s in pts:
        if not v0 - spacing / 2 < s[1] < v1 + spacing / 2:
            continue
        poly = [(s[0] - 3 * spacing, s[1] - 3 * spacing), (s[0] + 3 * spacing, s[1] - 3 * spacing),
                (s[0] + 3 * spacing, s[1] + 3 * spacing), (s[0] - 3 * spacing, s[1] + 3 * spacing)]
        for q0 in pts:
            for k in (-1, 0, 1):
                q = (q0[0] + k * circ, q0[1])
                d = math.hypot(q[0] - s[0], q[1] - s[1])
                if q0 is s and k == 0 or d > 3 * spacing:
                    continue
                n = ((q[0] - s[0]) / d, (q[1] - s[1]) / d)
                m = ((q[0] + s[0]) / 2, (q[1] + s[1]) / 2)
                poly = clip(poly, n, n[0] * m[0] + n[1] * m[1] - strut / 2)
                if len(poly) < 3:
                    break
        poly = clip(clip(poly, (0, -1), -v0), (0, 1), v1) if len(poly) >= 3 else []
        dedup = []                                           # il ritaglio duplica i vertici sulle rette
        for p in poly:
            if not dedup or math.hypot(p[0] - dedup[-1][0], p[1] - dedup[-1][1]) > 0.3:
                dedup.append(p)
        if len(dedup) > 2 and math.hypot(dedup[0][0] - dedup[-1][0], dedup[0][1] - dedup[-1][1]) <= 0.3:
            dedup.pop()
        poly = dedup if len(dedup) >= 3 else []
        for _ in range(3):                                   # angoli arrotondati
            poly = [p for i, a in enumerate(poly) for b in (poly[(i + 1) % len(poly)],)
                    for p in ((0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1]),
                              (0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1]))]
        if len(poly) >= 3:
            area = 0.5 * abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1])))
            if area > 6.0:
                holes.append(poly)
    return holes


z0, z1 = BASE_TOP, BASE_TOP + PP_H
zf = z0 + PP_FLOOR
outer = [(0, z0), (pp_radius(0) - 0.3, z0), (pp_radius(0.3), z0 + 0.3)]   # spalla piana che appoggia sulla base
outer += [(pp_radius(zr), z0 + zr) for zr in range(2, int(PP_H) - 1, 2)]
outer += [(pp_radius(PP_H - 1.0), z1 - 1.0), (pp_radius(PP_H) - 1.0, z1)]
inner = [(pp_radius(PP_H) - PP_RIM + 0.5, z1), (pp_radius(PP_H) - PP_RIM, z1 - 0.5),
         (pp_radius(PP_H - 3) - PP_RIM, z1 - 3)]
inner += [(pp_radius(zr) - PP_WALL, z0 + zr) for zr in range(int(PP_H) - 5, int(PP_FLOOR), -2)]
inner += [(pp_radius(PP_FLOOR) - PP_WALL - 1.0, zf), (0, zf)]
cup = lathe(outer + inner, TH_X, TH_Y, "P03_Portapenne", C_STAMPA, seg=144)

# parete a celle di Voronoi, come il vaso di riferimento ma con poche facce
R_MID = PP_R_END + (PP_R - PP_R_END) / 2
holes = voronoi_holes(2 * math.pi * R_MID, PP_HOLE_V0, PP_HOLE_V1, PP_CELL, PP_STRUT)
bm = bmesh.new()
for poly in holes:
    ring_in, ring_out = [], []
    for u, v in poly:
        t = u / R_MID
        r = pp_radius(v)
        ring_in.append(bm.verts.new((TH_X + (r - PP_WALL - 1.5) * math.cos(t), TH_Y + (r - PP_WALL - 1.5) * math.sin(t), z0 + v)))
        ring_out.append(bm.verts.new((TH_X + (r + 1.5) * math.cos(t), TH_Y + (r + 1.5) * math.sin(t), z0 + v)))
    bm.faces.new(ring_in[::-1]); bm.faces.new(ring_out)
    for i in range(len(poly)):
        j = (i + 1) % len(poly)
        bm.faces.new((ring_in[i], ring_in[j], ring_out[j], ring_out[i]))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
boolean(cup, obj_from_bm(bm, "fori_voronoi", C_STAMPA), 'DIFFERENCE', tolerant=True)
z_bot = BASE_TOP - TH_LEN
def male_r(t, z):
    r = thread_r(t, z, TH_R, BASE_TOP)
    return min(r, TH_R - TH_H + (z - z_bot) + 0.2)               # invito a 45° in punta
screw = radial_solid(male_r, z_bot, z0 + 0.5, TH_X, TH_Y, "vite", C_STAMPA)
boolean(cup, screw, 'UNION')
# la booleana dei fori lascia spigoli lunghi zero e n-goni concavi, che l'export STL
# triangola male: fondo i punti coincidenti e triangolo qui
bm = bmesh.new(); bm.from_mesh(cup.data)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=2e-4)
bmesh.ops.triangulate(bm, faces=bm.faces, quad_method='BEAUTY', ngon_method='BEAUTY')
bmesh.ops.dissolve_degenerate(bm, dist=1e-5, edges=bm.edges)
# a volte restano due schegge sugli stessi tre vertici, con normali opposte: le tolgo entrambe
seen = {}
for f in bm.faces:
    seen.setdefault(frozenset(v.index for v in f.verts), []).append(f)
twins = [f for fs in seen.values() if len(fs) > 1 for f in fs]
bmesh.ops.delete(bm, geom=twins, context='FACES_ONLY')
bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
bm.to_mesh(cup.data); bm.free()

# --- riferimento: custodia FreeBuds 3 ----------------------------------
bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=FB_D / 2, depth=FB_T,
                                    location=((fx0 + fx1) / 2, 0, BASE_TOP + FB_FLOOR + FB_D / 2 + 0.55),
                                    rotation=(0, math.radians(90), 0))
fb = bpy.context.active_object
fb.name = fb.data.name = "RIF_FreeBuds3_custodia"
bev = fb.modifiers.new("arrotonda", 'BEVEL'); bev.width = 6; bev.segments = 6
for u in fb.users_collection:
    u.objects.unlink(fb)
C_RIF.objects.link(fb)

# --- materiali ---------------------------------------------------------
def mat(name, rgb):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1)
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs[0].default_value = (*rgb, 1)
    return m
for o, rgb in [(base, (0.12, 0.12, 0.13)), (sup, (0.15, 0.15, 0.16)), (cup, (0.75, 0.75, 0.72)), (fb, (0.95, 0.95, 0.95))]:
    o.data.materials.append(mat("M_" + o.name, rgb))

# --- verifiche e STL --------------------------------------------------
def info(o):
    bm = bmesh.new(); bm.from_mesh(o.data)
    nm = sum(1 for e in bm.edges if not e.is_manifold)
    vol = bm.calc_volume(signed=True)
    bm.free()
    co = [o.matrix_world @ v.co for v in o.data.vertices]
    mn = [min(c[i] for c in co) for i in range(3)]; mx = [max(c[i] for c in co) for i in range(3)]
    return {"min": [round(a, 2) for a in mn], "max": [round(a, 2) for a in mx],
            "size": [round(b - a, 2) for a, b in zip(mn, mx)], "volume_mm3": round(vol), "non_manifold_edges": nm}

def clearance(a, b, samples=4000):
    """Distanza minima approssimata fra due mesh (vertici di a su superficie di b)."""
    from mathutils.bvhtree import BVHTree
    deps = bpy.context.evaluated_depsgraph_get()
    tb = BVHTree.FromObject(b, deps)
    vs = a.data.vertices
    step = max(1, len(vs) // samples)
    return round(min(tb.find_nearest(vs[i].co)[3] for i in range(0, len(vs), step)), 2)

def pilot_walls():
    """Plastica fra il foro guida e l'esterno del montante, con raggi dalla parete del foro."""
    from mathutils.bvhtree import BVHTree
    tree = BVHTree.FromPolygons([v.co for v in sup.data.vertices], [p.vertices[:] for p in sup.data.polygons])
    out = {}
    for name, d in (("davanti", (-1, 0, 0)), ("dietro", (1, 0, 0)), ("fianco", (0, 1, 0))):
        best = 1e9
        for sx, sy in SCREWS:
            for z in [BASE_TOP + 0.5 + k for k in range(int(SCREW_PILOT_DEPTH))]:
                dv = Vector(d)
                start = Vector((sx, sy, z)) + dv * (SCREW_PILOT / 2 + 0.01)
                hit = tree.ray_cast(start, dv)
                if hit[0] is not None:
                    best = min(best, hit[3])
        out[name] = round(best, 2)
    return out

geo = {"montaggio": {o.name: info(o) for o in (base, sup, cup)},
       "giochi_mm": {"portapenne-sostegno": round(min(v.co.x for v in sup.data.vertices
                                                           if BASE_TOP < v.co.z < BASE_TOP + PP_H) - (TH_X + PP_R), 2), "culla-sostegno": round(FB_X0 - max(v.co.x for v in sup.data.vertices
                                                           if BASE_TOP + 0.01 < v.co.z < BASE_TOP + FB_TOP + 1), 2),
                     "custodia-sostegno": round(FB_X0 + FB_WALL + 0.6 - max(v.co.x for v in sup.data.vertices
                                                           if BASE_TOP < v.co.z < BASE_TOP + FB_FLOOR + FB_D + 1), 2),
                     "custodia-culla_raggio": round(FB_R - FB_D / 2, 2)},
       "viti": {"posizioni": SCREWS, "foro_base": SCREW_HOLE, "svasatura": SCREW_CSK, "foro_guida": SCREW_PILOT,
                "profondita_guida": SCREW_PILOT_DEPTH,
                "materiale_attorno_al_foro_guida": pilot_walls(),
                "materiale_fra_svasatura_e_sede": round((tx0 - SLOT_GAP) - (SCREWS[0][0] + SCREW_CSK / 2), 2),
                "gioco_sede_per_lato": SLOT_GAP, "sede_piu_profonda": SLOT_DEEPER},
       "filetto": {"diametro_vite": TH_R * 2, "passo": TH_P, "profondita": TH_H, "lunghezza_vite": TH_LEN,
                   "gioco_radiale": TH_GAP, "madrevite_profonda": TH_RECESS},
       "holder": {"traslazione_x": round(tx, 3), "spalla_y": round(shoulder, 3)}}

# STL nell'orientamento di stampa
os.makedirs(STL, exist_ok=True)
PRINT_M = {base: Matrix.Identity(4), cup: Matrix.Translation((-TH_X, -TH_Y, -z_bot)),
           sup: HOLD_M.inverted()}
files = {base: "P01_Base.stl", sup: "P02_Sostegno.stl", cup: "P03_Portapenne.stl"}
geo["stampa"] = {}
for o, fn in files.items():
    tmp = o.copy(); tmp.data = o.data.copy(); C_STAMPA.objects.link(tmp)
    tmp.data.transform(PRINT_M[o])
    zmin = min(v.co.z for v in tmp.data.vertices)
    tmp.data.transform(Matrix.Translation((0, 0, -zmin)))
    geo["stampa"][fn] = info(tmp)
    geo["stampa"][fn]["matrice_montaggio"] = [[round(x, 6) for x in r] for r in (PRINT_M[o].inverted()).to_3x3()]
    bpy.ops.object.select_all(action='DESELECT')
    tmp.select_set(True); bpy.context.view_layer.objects.active = tmp
    bpy.ops.wm.stl_export(filepath=os.path.join(STL, fn), export_selected_objects=True, apply_modifiers=True)
    bpy.data.objects.remove(tmp)

with open(os.path.join(ROOT, "dati", "geometria.json"), "w", encoding="utf-8") as f:
    json.dump(geo, f, indent=1, ensure_ascii=False)
print("GEOMETRIA", json.dumps(geo))

# accessori di riferimento (controller, penne, cuffie): blender/accessori.py
import importlib.util
acc_path = os.path.join(ROOT, "blender", "accessori.py")
spec = importlib.util.spec_from_file_location("accessori", acc_path)
acc = importlib.util.module_from_spec(spec); spec.loader.exec_module(acc)
acc.build()

for path in (os.path.abspath(__file__), acc_path):
    txt = bpy.data.texts.new(os.path.basename(path))
    txt.from_string(open(path, encoding="utf-8").read())
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "blender", "Stand_Controller_PS5.blend"))
