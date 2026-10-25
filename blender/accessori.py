"""Stand controller PS5 · accessori di riferimento (solo per vedere gli ingombri).

Crea nella collezione RIFERIMENTI un DualSense, cinque penne nel portapenne e
delle cuffie d'esempio sul gancio. Non sono pezzi da stampare: forme semplificate.
Si lancia nel .blend aperto (Alt+P sul testo accessori.py) o in fondo a costruisci.py.

Misure: DualSense 160 × 66 × 106 mm (Sony); penne Ø9 × 140 mm.
"""
import bpy, bmesh, math
from mathutils import Matrix, Vector

PREFIX = "ACC_"
CUP = Vector((-63.5, 0.0, 10.0))          # centro del fondo interno del portapenne
CUP_R_IN, CUP_TOP = 19.5, 98.0          # bordo del portapenne: foro Ø39 in cima
HOOK_X, HOOK_TOP = 70.0, 240.6            # centro e quota della sella del gancio cuffie


def collection():
    c = bpy.data.collections.get("RIFERIMENTI")
    if c is None:
        c = bpy.data.collections.new("RIFERIMENTI")
        bpy.context.scene.collection.children.link(c)
    return c


def material(name, rgb):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.diffuse_color = (*rgb, 1)
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs[0].default_value = (*rgb, 1)
    return m


def add_object(name, bm, mats, c):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    for m in mats:
        me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    c.objects.link(o)
    for p in me.polygons:
        p.use_smooth = True
    return o


def put(bm, geom_bm, matrix, mat_index):
    """Copia geom_bm in bm trasformata, con l'indice di materiale dato."""
    me = bpy.data.meshes.new("tmp")
    geom_bm.to_mesh(me); geom_bm.free()
    me.transform(matrix)
    for p in me.polygons:
        p.material_index = mat_index
    bm.from_mesh(me)
    bpy.data.meshes.remove(me)


def cube(sx, sy, sz):
    b = bmesh.new()
    bmesh.ops.create_cube(b, size=1.0)
    bmesh.ops.scale(b, vec=(sx, sy, sz), verts=b.verts)
    return b


def rounded_cube(sx, sy, sz, r):
    b = cube(sx, sy, sz)
    bmesh.ops.bevel(b, geom=b.edges[:], offset=r, segments=4, affect='EDGES', profile=0.5)
    return b


def cylinder(r, h, seg=32):
    b = bmesh.new()
    bmesh.ops.create_cone(b, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=h)
    return b


def sphere(r):
    b = bmesh.new()
    bmesh.ops.create_uvsphere(b, u_segments=32, v_segments=16, radius=r)
    return b


def segment(p0, p1):
    """Matrice che porta l'asse Z di un cilindro alto 1 sul segmento p0-p1."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    q = d.normalized().to_track_quat('Z', 'Y')
    return Matrix.Translation((p0 + p1) / 2) @ q.to_matrix().to_4x4()


def dualsense(c, white, black):
    """Assi locali: X larghezza, Y dal fondo delle impugnature (-) ai grilletti (+), Z verso la faccia."""
    bm = bmesh.new()
    I = Matrix.Identity(4)
    put(bm, rounded_cube(112, 62, 28, 9), Matrix.Translation((0, 14, 0)), 0)        # corpo
    put(bm, rounded_cube(64, 46, 3, 1.5), Matrix.Translation((0, 4, 14)), 1)       # placca nera
    put(bm, rounded_cube(46, 26, 3, 2), Matrix.Translation((0, 30, 15)), 0)        # touchpad
    for s in (-1, 1):
        a, b = (s * 50, 28, 0), (s * 60, -40, -6)
        put(bm, cylinder(19, 1), segment(a, b) @ Matrix.Diagonal((1, 1, (Vector(b) - Vector(a)).length, 1)), 0)
        put(bm, sphere(19), Matrix.Translation(b), 0)                               # punta impugnatura
        put(bm, cylinder(8.5, 10), Matrix.Translation((s * 21, -4, 19)), 1)        # levette
        put(bm, cylinder(10, 3), Matrix.Translation((s * 21, -4, 15)), 1)
        put(bm, rounded_cube(24, 12, 16, 3), Matrix.Translation((s * 48, 48, 4)), 1)   # grilletti
        put(bm, cube(16, 16, 2), Matrix.Translation((s * 44, 16, 15)), 1)              # croce / tasti
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return add_object(PREFIX + "DualSense", bm, [white, black], c)


def pens(c, colors):
    """Cinque penne appoggiate sul fondo e inclinate verso il bordo opposto, lontano dalla colonna."""
    out = []
    for k, (ang, rgb) in enumerate(zip((10, 55, -45, 100, -95), colors)):
        a = math.radians(ang)
        foot = CUP + Vector((8 * math.cos(a), 8 * math.sin(a), 4.5))
        rim = CUP + Vector((-(CUP_R_IN - 4.5) * math.cos(a), -(CUP_R_IN - 4.5) * math.sin(a), CUP_TOP - CUP.z))
        d = (rim - foot).normalized()
        tip = foot + d * 140
        bm = bmesh.new()
        put(bm, cylinder(4.5, 1, 16), segment(foot, tip) @ Matrix.Diagonal((1, 1, 140, 1)), 0)
        put(bm, cylinder(4.8, 1, 16), segment(tip - d * 28, tip) @ Matrix.Diagonal((1, 1, 28, 1)), 1)  # cappuccio
        out.append(add_object(PREFIX + f"Penna_{k + 1}", bm, [material(f"M_ACC_penna_{k}", rgb),
                                                              material("M_ACC_nero", (0.03, 0.03, 0.03))], c))
    return out


def headphones(c, black, grey):
    """Archetto a sezione 34 × 8 mm sulla sella del gancio, padiglioni ovali ai lati."""
    R, half = 88.0, math.radians(78)
    zc = HOOK_TOP + 4 - R
    bm = bmesh.new()
    n = 40
    rings = []
    for i in range(n + 1):
        t = -half + 2 * half * i / n
        ring = []
        for dx, dr in ((-17, -4), (17, -4), (17, 4), (-17, 4)):
            r = R + dr
            ring.append(bm.verts.new((HOOK_X + dx, r * math.sin(t), zc + r * math.cos(t))))
        rings.append(ring)
    for a, b in zip(rings, rings[1:]):
        for j in range(4):
            bm.faces.new((a[j], a[(j + 1) % 4], b[(j + 1) % 4], b[j]))
    bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
    for f in bm.faces:
        f.material_index = 0
    yz_end = (R * math.sin(half), zc + R * math.cos(half))
    for s in (-1, 1):
        cup = sphere(1)
        put(bm, cup, Matrix.Translation((HOOK_X, s * (yz_end[0] + 6), yz_end[1] - 38)) @ Matrix.Diagonal((34, 20, 44, 1)), 0)
        put(bm, cylinder(30, 6), Matrix.Translation((HOOK_X, s * (yz_end[0] - 12), yz_end[1] - 38))
            @ Matrix.Rotation(math.radians(90), 4, 'X') @ Matrix.Diagonal((1, 1.3, 1, 1)), 1)   # cuscinetti
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return add_object(PREFIX + "Cuffie_esempio", bm, [black, grey], c)


def build(controller_matrix=None):
    c = collection()
    for o in [o for o in bpy.data.objects if o.name.startswith(PREFIX)]:
        bpy.data.objects.remove(o)
    white = material("M_ACC_bianco", (0.92, 0.92, 0.9))
    black = material("M_ACC_nero", (0.03, 0.03, 0.03))
    grey = material("M_ACC_grigio", (0.25, 0.25, 0.27))
    ds = dualsense(c, white, black)
    if controller_matrix is None:
        # faccia verso il davanti, inclinata di 35°; impugnature giù, davanti al braccio
        a = math.radians(35)
        xl, yl = Vector((0, -1, 0)), Vector((math.sin(a), 0, math.cos(a)))
        zl = xl.cross(yl)
        controller_matrix = Matrix.Translation(CONTROLLER_AT) @ Matrix((xl, yl, zl)).transposed().to_4x4() \
            @ Matrix.Translation((0, 15, 0))
    ds.matrix_world = controller_matrix
    pens(c, [(0.1, 0.25, 0.75), (0.8, 0.1, 0.1), (0.1, 0.55, 0.2), (0.95, 0.75, 0.1), (0.05, 0.05, 0.05)])
    headphones(c, black, grey)
    fb = bpy.data.objects.get("RIF_FreeBuds3_custodia")
    if fb:
        fb.data.materials.clear(); fb.data.materials.append(white)
    return ds


# bordo anteriore del corpo (fra le impugnature) nella culla del braccio alto: quota trovata
# facendo scendere il controller finché tocca il sostegno (minimo a X -13), più 0,3 mm
CONTROLLER_AT = Vector((-13.0, 0.0, 205.0))

if __name__ == "__main__":
    build()
