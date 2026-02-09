from PIL import Image, ImageDraw, ImageFont

# Veličina slike
width, height = 1000, 400
img = Image.new("RGB", (width, height), color=(255, 255, 255))

draw = ImageDraw.Draw(img)

try:
    font = ImageFont.truetype("arial.ttf", 16)
except:
    font = ImageFont.load_default()

stations = {
    "Spremiste fittinga": (100, 200),
    "Spremiste i rezanje": (250, 200),
    "Bendanje": (400, 200),
    "Fit Up": (550, 200),
    "Welding": (700, 200),
    "NDT": (850, 200),
    "Tehnicka kontrola": (950, 200)
}

sq_size = 60

for name, (x, y) in stations.items():
    draw.rectangle([x - sq_size//2, y - sq_size//2, x + sq_size//2, y + sq_size//2], fill=(200, 200, 255), outline="black")
    bbox = draw.textbbox((0, 0), name, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((x - w/2, y - h/2), name, fill="black", font=font)

# Spremi u folder projekta
img.save("C:/Users/domag/spool_tracking/layout.png")
print("layout.png je spremna!")
