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
# filetto portapenne (base maschio, portapenne femmina)
TH_X, TH_Y = -63.5, 0.0
TH_R, TH_P, TH_H = 10.0, 2.5, 1.25      # raggio esterno, passo, profondità
TH_LEN = 7.0                             # altezza del perno sopra la base
TH_GAP = 0.35                            # gioco radiale della madrevite
# portapenne
PP_R, PP_WALL, PP_H = 24.0, 2.0, 90.0
PP_SOCKET = 8.0                          # profondità della madrevite
PP_FLOOR = 18.0 - BASE_TOP               # spessore del fondo (madrevite + 2 mm)
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


def boolean(target, tool, op):
    m = target.modifiers.new("b", 'BOOLEAN')
    m.operation, m.object, m.solver = op, tool, 'EXACT'
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

# --- P01 base: perno filettato + culla FreeBuds ------------------------
base = base_o.copy(); base.data = base_o.data.copy()
base.name = base.data.name = "P01_Base"
C_STAMPA.objects.link(base)
base.data.transform(BASE_M)

z_top = BASE_TOP + TH_LEN
def male_r(t, z):
    r = thread_r(t, z, TH_R, BASE_TOP)
    return min(r, TH_R - TH_H + (z_top - z) + 0.2)          # invito a 45° in cima
boss = radial_solid(male_r, BASE_TOP - 1.0, z_top, TH_X, TH_Y, "perno", C_STAMPA)
boolean(base, boss, 'UNION')

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

z0, z1 = BASE_TOP, BASE_TOP + PP_H
ri, zf = PP_R - PP_WALL, z0 + PP_FLOOR
cup = lathe([(0, z0), (PP_R - 0.6, z0), (PP_R, z0 + 0.6), (PP_R, z1 - 1.0), (PP_R - 1.0, z1),
             (ri + 0.4, z1), (ri, z1 - 0.4), (ri, zf + 1.0), (ri - 1.0, zf), (0, zf)],
            TH_X, TH_Y, "P03_Portapenne", C_STAMPA)
def female_r(t, z):
    r = thread_r(t, z, TH_R, BASE_TOP) + TH_GAP                  # stessa fase del perno
    return max(r, TH_R + TH_GAP + 0.3 - (z - z0))                # invito alla bocca
sock = radial_solid(female_r, z0 - 1.0, z0 + PP_SOCKET, TH_X, TH_Y, "madrevite", C_STAMPA)
boolean(cup, sock, 'DIFFERENCE')

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

geo = {"montaggio": {o.name: info(o) for o in (base, sup, cup)},
       "giochi_mm": {"portapenne-sostegno": clearance(cup, sup), "culla-sostegno": round(FB_X0 - max(v.co.x for v in sup.data.vertices
                                                           if BASE_TOP + 0.01 < v.co.z < BASE_TOP + FB_TOP + 1), 2),
                     "custodia-sostegno": round(FB_X0 + FB_WALL + 0.6 - max(v.co.x for v in sup.data.vertices
                                                           if BASE_TOP < v.co.z < BASE_TOP + FB_FLOOR + FB_D + 1), 2),
                     "custodia-culla_raggio": round(FB_R - FB_D / 2, 2)},
       "filetto": {"diametro": TH_R * 2, "passo": TH_P, "profondita": TH_H, "lunghezza_perno": TH_LEN,
                   "gioco_radiale": TH_GAP, "madrevite_profonda": PP_SOCKET},
       "holder": {"traslazione_x": round(tx, 3), "spalla_y": round(shoulder, 3)}}

# STL nell'orientamento di stampa
os.makedirs(STL, exist_ok=True)
PRINT_M = {base: Matrix.Identity(4), cup: Matrix.Translation((-TH_X, -TH_Y, -BASE_TOP)),
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

txt = bpy.data.texts.new("costruisci.py")
txt.from_string(open(os.path.abspath(__file__), encoding="utf-8").read())
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT, "blender", "Stand_Controller_PS5.blend"))
