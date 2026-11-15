"""Build the original training dummy mesh, materials, icons and B42 tile assets."""
import io
import math
from pathlib import Path
import struct

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "SuQingTrainingDummy" / "42"
ADDON = ROOT / "SuQingTrainingDummyViewpoint" / "42"
ART = ROOT / "art"
SHEET = "suqing_training_dummy_01"
PACK = "SuQingTrainingDummy_tiles"
FACINGS = (("N", 180), ("E", -90), ("S", 0), ("W", 90))
TILE_SIZE = (128, 256)
GROUND = (64, 224)  # B42 tile scale 2, sprite anchor (64, 192).
CELL = 128
ATLAS_SIZE = 512


def make_atlas():
    """Original wood, canvas, iron, cord, and painted target surface."""
    rng = np.random.default_rng(7837)
    y, x = np.mgrid[:CELL, :CELL]
    grain = rng.normal(0, 1, (CELL, CELL))
    weave = np.cos(x * math.pi) + np.cos(y * math.pi)
    swatches = [
        ("wood", (121, 85, 52), grain * 3 + (np.sin(x*.18) + np.sin(x*.9 + np.sin(y*.04)))*5),
        ("endgrain", (150, 108, 66), grain * 3 + np.cos(np.hypot((x-80)*1.2, y-77)*.43)*7),
        ("linen", (177, 150, 104), grain * 4 + weave*4 + np.sin(y*.17)*3),
        ("iron", (77, 74, 67), grain * 5 + np.cos(y*.19)*2),
        ("cord", (138, 109, 69), grain * 4 + np.sin(x*.9-y*.65)*8),
        ("plum", (95, 66, 92), grain * 4 + weave*3),
        ("target", (189, 162, 118), grain * 4 + weave*4),
        ("patch", (148, 116, 82), grain * 4 + weave*3),
        ("seam", (214, 189, 143), grain * 3 + np.sin(x*1.25-y*.8)*7),
    ]
    atlas = Image.new("RGBA", (ATLAS_SIZE, ATLAS_SIZE), (0, 0, 0, 255))
    regions = {}
    for index, (name, base, noise) in enumerate(swatches):
        if name == "target":
            r = np.hypot(x-(CELL-1)/2, y-(CELL-1)/2)
            dark = (r <= 10) | ((r >= 24) & (r <= 29)) | ((r >= 43) & (r <= 49))
            color = np.where(dark[:, :, None], np.array([103, 58, 65]), np.array(base))
        else:
            color = np.broadcast_to(base, (CELL, CELL, 3))
        pixels = np.clip(color + noise[:, :, None], 0, 255).astype(np.uint8)
        swatch = Image.fromarray(pixels).convert("RGBA")
        if name == "wood":
            pen = ImageDraw.Draw(swatch)
            for knot_x, knot_y in [(33, 22), (89, 87)]:
                for ring in range(3, 12, 4):
                    pen.ellipse((knot_x-ring//2,knot_y-ring,knot_x+ring//2,knot_y+ring), outline=(89,57,34,255))
        cell_x, cell_y = (index % 4) * CELL, (index // 4) * CELL
        atlas.paste(swatch, (cell_x, cell_y))
        regions[name] = (cell_x, cell_y)
    return atlas, regions


class Mesh:
    def __init__(self, regions):
        self.regions = regions
        self.vertices = []
        self.uvs = []
        self.faces = []

    def polygon(self, points, material, coordinates=None):
        if coordinates is None:
            coordinates = ((0, 0), (1, 0), (1, 1), (0, 1))
        cell_x, cell_y = self.regions[material]
        border = 3
        uv = [
            ((cell_x + border + u * (CELL - 2*border)) / ATLAS_SIZE,
             1 - (cell_y + border + v * (CELL - 2*border)) / ATLAS_SIZE)
            for u, v in coordinates
        ]
        start = len(self.vertices)
        self.vertices.extend(points)
        self.uvs.extend(uv)
        self.faces.extend((start, start+n, start+n+1) for n in range(1, len(points)-1))

    def box(self, center, size, material, pitch=0, yaw=0, wooden=False):
        hx, hy, hz = np.array(size) * .5
        corners = np.array([
            (-hx,-hy,-hz), (hx,-hy,-hz), (hx,hy,-hz), (-hx,hy,-hz),
            (-hx,-hy,hz), (hx,-hy,hz), (hx,hy,hz), (-hx,hy,hz),
        ])
        cos, sin = math.cos(pitch), math.sin(pitch)
        corners = corners @ np.array(((cos,0,-sin),(0,1,0),(sin,0,cos)))
        corners = rotate(corners, yaw) + center
        for n, side in enumerate(((3,2,1,0),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7))):
            self.polygon(corners[list(side)], "endgrain" if wooden and n < 2 else material)

    def loft(self, center, levels, material, sides=16):
        """Loft elliptical levels defined by height and horizontal radii."""
        angles = np.arange(sides) * (2 * math.pi / sides)
        rings = [
            np.column_stack((np.cos(angles)*rx, np.sin(angles)*ry, np.full(sides,z))) + center
            for z, rx, ry in levels
        ]
        for level, (bottom, top) in enumerate(zip(rings, rings[1:])):
            for side in range(sides):
                next_side = (side + 1) % sides
                u0, u1 = (side % 4)/4, ((side % 4)+1)/4
                v0, v1 = 1-level/(len(rings)-1), 1-(level+1)/(len(rings)-1)
                self.polygon((bottom[side], bottom[next_side], top[next_side], top[side]),
                             material, ((u0,v0),(u1,v0),(u1,v1),(u0,v1)))
        cap_uv = np.column_stack((np.cos(angles), np.sin(angles))) * .47 + .5
        self.polygon(rings[-1], material, cap_uv)
        self.polygon(rings[0][::-1], material, cap_uv[::-1])

    def target(self, center_z, radii, plane_y):
        """A slightly padded square made from a tight rounded cloth patch."""
        outline = [
            (-.84,-1), (.84,-1), (1,-.84), (1,.84),
            (.84,1), (-.84,1), (-1,.84), (-1,-.84),
        ][::-1]
        center = (0, plane_y+.012, center_z)
        for n, (x0, z0) in enumerate(outline):
            x1, z1 = outline[(n+1) % len(outline)]
            self.polygon((center, (x0*radii[0],plane_y,center_z+z0*radii[1]),
                          (x1*radii[0],plane_y,center_z+z1*radii[1])),
                         "target", ((.5,.5),(.5+x0*.49,.5-z0*.49),(.5+x1*.49,.5-z1*.49)))

    def arrays(self):
        return np.asarray(self.vertices), np.asarray(self.uvs), np.asarray(self.faces)


def rotate(vertices, degrees):
    angle = math.radians(degrees)
    c, s = math.cos(angle), math.sin(angle)
    return vertices @ np.array(((c, s, 0), (-s, c, 0), (0, 0, 1)))


def make_dummy(regions):
    mesh = Mesh(regions)
    # Crossed wooden base, upright and diagonal kick braces.
    mesh.box((0, 0, .039), (.78, .11, .078), "wood", yaw=0)
    mesh.box((0, 0, .055), (.07, .72, .11), "wood")
    mesh.box((0, 0, .64), (.105, .105, 1.23), "wood", wooden=True)
    for sign in (-1, 1):
        mesh.box((sign*.155, 0, .20), (.052, .066, .38), "wood",
                 pitch=math.radians(-43*sign))
        mesh.box((sign*.278, .061, .067), (.052, .016, .051), "iron")
    # Arms are the horizontal cross bar, wrapped in linen around the striking ends.
    mesh.box((0, 0, 1.10), (.88, .091, .087), "wood", yaw=0)
    for sign in (-1, 1):
        arm = sign*.309
        mesh.box((arm, 0, 1.105), (.187, .136, .143), "linen", yaw=sign*2)
        mesh.box((arm+sign*.046, 0, 1.105), (.028, .146, .153), "cord")
        mesh.box((arm-sign*.061, 0, 1.105), (.024, .146, .153), "plum")
        mesh.box((sign*.430, 0, 1.10), (.022, .10, .101), "endgrain")
    # Stuffed torso and sack head on the center pole.
    mesh.loft((0,0,0), ((.60,.105,.068),(.63,.159,.103),(.78,.178,.118),
                        (1.00,.207,.142),(1.15,.205,.138),(1.21,.154,.104),
                        (1.24,.078,.067)), "linen")
    mesh.loft((0,0,0), ((1.235,.067,.074),(1.29,.073,.079)), "cord", sides=12)
    mesh.loft((0,.006,0), ((1.29,.073,.071),(1.33,.102,.093),(1.455,.111,.095),
                           (1.525,.084,.074),(1.54,.040,.040)), "linen")
    # One rear seam and visible lacing. The geometric target is on the south face.
    mesh.loft((0,0,0), ((.69,.171,.112),(.73,.178,.118)), "plum")
    mesh.target(.966, (.137,.185), .147)
    for z in (.80,.85,.90,.95,1.,1.05,1.10):
        mesh.box((0,-.138,z), (.052,.018,.011), "seam", pitch=math.radians(11))
    mesh.box((.10,-.108,1.06), (.059,.013,.110), "patch", pitch=math.radians(-20), yaw=11)
    return mesh


def render(mesh, texture, rotation, size, scale, origin):
    """Depth-buffered orthographic render with the PZ tile projection."""
    vertices, uv, triangles = mesh.arrays()
    world = rotate(vertices, rotation)
    sx = (world[:, 0] - world[:, 1])*scale + origin[0]
    sy = (world[:, 0] + world[:, 1])*scale*.5 - world[:, 2]*scale*1.5 + origin[1]
    depth = world[:, 0] + world[:, 1] + world[:, 2]*1.3
    width, height = size
    rgba = np.zeros((height,width,4), dtype=np.uint8)
    z_buffer = np.full((height,width), -np.inf)
    atlas = np.asarray(texture)
    light = np.asarray((-.28,.63,.72))
    light /= np.linalg.norm(light)
    for ids in triangles:
        a, b, c = world[ids]
        normal = np.cross(b-a, c-a)
        normal /= np.linalg.norm(normal)
        shade = .66 + .32 * max(0., np.dot(normal, light)) + .05 * max(0., normal[2])
        x, y, z = sx[ids], sy[ids], depth[ids]
        left, right = max(0, math.floor(x.min())), min(width-1, math.ceil(x.max()))
        top, bottom = max(0, math.floor(y.min())), min(height-1, math.ceil(y.max()))
        if left > right or top > bottom:
            continue
        xx, yy = np.meshgrid(np.arange(left,right+1)+.5, np.arange(top,bottom+1)+.5)
        area = (y[1]-y[2])*(x[0]-x[2]) + (x[2]-x[1])*(y[0]-y[2])
        if abs(area) < 1e-8:
            continue
        q0 = ((y[1]-y[2])*(xx-x[2]) + (x[2]-x[1])*(yy-y[2])) / area
        q1 = ((y[2]-y[0])*(xx-x[2]) + (x[0]-x[2])*(yy-y[2])) / area
        q2 = 1-q0-q1
        d = q0*z[0] + q1*z[1] + q2*z[2]
        region = (slice(top,bottom+1), slice(left,right+1))
        visible = (q0 >= -1e-7) & (q1 >= -1e-7) & (q2 >= -1e-7) & (d > z_buffer[region])
        if not visible.any():
            continue
        weights = np.column_stack((q0[visible],q1[visible],q2[visible]))
        sample = weights @ uv[ids]
        tx = np.clip((sample[:,0]*ATLAS_SIZE).astype(int), 0, ATLAS_SIZE-1)
        ty = np.clip(((1-sample[:,1])*ATLAS_SIZE).astype(int), 0, ATLAS_SIZE-1)
        colors = atlas[ty,tx].copy()
        colors[:,:3] = np.clip(colors[:,:3]*shade,0,255).astype("uint8")
        rgba[region][visible] = colors
        z_buffer[region][visible] = d[visible]
    return Image.fromarray(rgba)


def export_viewpoint(mesh, texture):
    media = ADDON / "media/viewpoint"
    media.mkdir(parents=True, exist_ok=True)
    (media / "dummy.mtl").write_text(
        "newmtl dummy_atlas\nKa 1 1 1\nKd 1 1 1\nKs 0.05 0.05 0.05\n"
        "Ns 12\nd 1\nillum 2\nmap_Kd dummy_atlas.png\n", encoding="ascii")
    texture.save(media / "dummy_atlas.png")

    vertices, uv, faces = mesh.arrays()
    rows = ["# Original model. X east, Y south, Z up. One unit per tile.",
            "mtllib dummy.mtl", "o SuQingTrainingDummy", "usemtl dummy_atlas"]
    rows.extend("v %.7f %.7f %.7f" % tuple(point) for point in vertices)
    rows.extend("vt %.7f %.7f" % tuple(point) for point in uv)
    normals = np.cross(vertices[faces[:,1]]-vertices[faces[:,0]],
                       vertices[faces[:,2]]-vertices[faces[:,0]])
    normals /= np.linalg.norm(normals, axis=1)[:,None]
    rows.extend("vn %.7f %.7f %.7f" % tuple(point) for point in normals)
    rows.extend("f " + " ".join(f"{v+1}/{v+1}/{n+1}" for v in face) for n, face in enumerate(faces))
    (media / "dummy.obj").write_text("\n".join(rows)+"\n", encoding="ascii")

    manifest = ["id=suqing-training-dummy-viewpoint", "name=SuQing Training Dummy",
                "version=1", "model.dummy=dummy.obj"]
    manifest.extend(f"bind.{SHEET}_{i}=dummy,{degrees},0,0,0,1"
                    for i, (_,degrees) in enumerate(FACINGS))
    (media / "package.properties").write_text("\n".join(manifest)+"\n", encoding="ascii")


def int32(n):
    return struct.pack("<i", n)


def string32(value):
    value = value.encode("ascii")
    return int32(len(value)) + value


def export_tiles(sprites):
    media = CORE / "media"
    packs = media / "texturepacks"
    packs.mkdir(parents=True, exist_ok=True)
    width, height = TILE_SIZE
    sheet = Image.new("RGBA", (width*4,height))
    for i, sprite in enumerate(sprites):
        sheet.paste(sprite, (i*width, 0))
    sheet.save(ART / f"{SHEET}.png")

    tiles = bytearray(b"tdef" + int32(1) + int32(1))
    tiles += f"{SHEET}\n{SHEET}.png\n".encode("ascii") + struct.pack("<4i",4,1,1,4)
    page = bytearray(b"PZPK" + int32(1) + int32(1) + string32(PACK+"_0") + int32(4) + int32(1))
    for i, (facing, _) in enumerate(FACINGS):
        props = {"BlocksPlacement": "", "CustomName": "TrainingDummy", "GroupName": "SuQing",
                 "Facing": facing, "Material": "Wood", "Material2": "Fabric", "solidtrans": ""}
        tiles += int32(len(props))
        for key, value in sorted(props.items()):
            tiles += f"{key}\n{value}\n".encode("ascii")
        page += string32(f"{SHEET}_{i}") + struct.pack("<8i", i*width,0,width,height,0,0,width,height)
    png = io.BytesIO()
    sheet.save(png, format="PNG")
    page += int32(png.tell()) + png.getvalue()
    (media / f"{SHEET}.tiles").write_bytes(tiles)
    (packs / f"{PACK}.pack").write_bytes(page)


def export_icons_and_preview(mesh, atlas):
    hero = render(mesh, atlas, -12, (400, 580), 185, (205,513))
    hero = hero.crop(hero.getbbox())
    icon = hero.copy()
    icon.thumbnail((106,110), Image.Resampling.LANCZOS)
    frame = Image.new("RGBA", (128,128))
    frame.alpha_composite(icon, ((128-icon.width)//2,(128-icon.height)//2))
    textures = CORE / "media/textures"
    textures.mkdir(parents=True, exist_ok=True)
    frame.save(textures / "Item_SuQingTrainingDummy.png")

    for path in (CORE, ADDON):
        badge = Image.new("RGBA", (128,128), (0,0,0,0))
        draw = ImageDraw.Draw(badge)
        draw.rounded_rectangle((5,5,122,122), radius=23, fill="#28232b", outline="#8b748b", width=4)
        badge.alpha_composite(frame)
        badge.resize((64,64), Image.Resampling.LANCZOS).save(path / "icon.png")

    preview = Image.new("RGBA", (940,500), "#222025")
    draw = ImageDraw.Draw(preview)
    draw.text((25,23), "SUQING'S TRAINING DUMMY", fill="#f2e5d7", font_size=28)
    for i, (label, rotation) in enumerate((("FRONT",-12), ("SIDE",-95), ("BACK",168))):
        center_x = 160 + 310*i
        draw.text((center_x,447), label, fill="#dbb8cc", anchor="mt", font_size=17)
        floor = [(center_x-116,383), (center_x,325), (center_x+116,383), (center_x,441)]
        draw.polygon(floor, fill="#343039", outline="#4e454f")
        model = render(mesh, atlas, rotation, (280,350), 135, (140,325))
        preview.alpha_composite(model, (center_x-140,58))
    preview.convert("RGB").save(ART / "training-dummy-preview.png")


def main():
    ART.mkdir(parents=True, exist_ok=True)
    atlas, regions = make_atlas()
    mesh = make_dummy(regions)
    export_viewpoint(mesh, atlas)
    width, height = TILE_SIZE
    sprites = [
        render(mesh, atlas, rotation, (2*width,2*height), 128, (2*GROUND[0],2*GROUND[1]))
        .resize(TILE_SIZE, Image.Resampling.LANCZOS)
        for _, rotation in FACINGS
    ]
    export_tiles(sprites)
    export_icons_and_preview(mesh, atlas)
    print(f"Built {len(mesh.faces)} model triangles and {len(sprites)} directional tiles")


if __name__ == "__main__":
    main()
