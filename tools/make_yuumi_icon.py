from pathlib import Path
import struct

root = Path(__file__).resolve().parents[1]
png_path = root / "assets" / "yuumi.png"
ico_path = root / "assets" / "yuumi.ico"
png = png_path.read_bytes()
width, height = struct.unpack(">II", png[16:24])
width_byte = 0 if width >= 256 else width
height_byte = 0 if height >= 256 else height
directory = struct.pack("<HHH", 0, 1, 1)
entry = struct.pack("<BBBBHHII", width_byte, height_byte, 0, 0, 1, 32, len(png), 22)
ico_path.write_bytes(directory + entry + png)
print(f"Wrote {ico_path} ({width}x{height})")
