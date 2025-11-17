from flask import Flask, request, render_template as render, send_file, redirect, url_for
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.utils import ImageReader
from io import BytesIO
from PIL import Image, ImageDraw, ImageOps

app = Flask(__name__)

@app.route('/')
def Home():
    return render("index.html", text="Flask")

@app.route('/form')
def Form():
    return render('form.html')


def make_circular_image(file_stream, size):
    """
    Create a circular (RGBA) PNG from a file-like object.
    Returns a BytesIO containing the PNG.
    """
    img = Image.open(file_stream).convert("RGBA")

    # Resize and crop to square
    min_side = min(img.size)
    left = (img.width - min_side) // 2
    top = (img.height - min_side) // 2
    right = left + min_side
    bottom = top + min_side
    img = img.crop((left, top, right, bottom))
    img = img.resize((size, size), Image.LANCZOS)

    # Create circle mask
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0, size, size), fill=255)

    # Apply mask to image (keep alpha)
    output = Image.new("RGBA", (size, size))
    output.paste(img, (0, 0), mask=mask)

    # Optional: add thin white circular border to match sample aesthetic
    border = Image.new("RGBA", (size, size))
    border_draw = ImageDraw.Draw(border)
    border_draw.ellipse((1, 1, size-2, size-2), outline=(255,255,255,255), width=4)
    output = Image.alpha_composite(output, border)

    out_buf = BytesIO()
    output.save(out_buf, format="PNG")
    out_buf.seek(0)
    return out_buf


@app.route('/generate-pdf', methods=['POST'])
def generate_pdf():

    # Collect user input
    name = request.form.get("name", "No Name")
    age = request.form.get("age", "")
    city = request.form.get("city", "")
    phone = request.form.get("phone", "")
    email = request.form.get("email", "")
    skill1 = request.form.get("skill1", "")
    skill2 = request.form.get("skill2", "")
    skill3 = request.form.get("skill3", "")
    education = request.form.get("education", "")
    about = request.form.get("about", "")

    # Handle uploaded profile image
    profile_file = request.files.get("profile")
    image_reader = None
    image_size_px = 110  # pixels for the circular avatar

    if profile_file and profile_file.filename:
        try:
            circular_png = make_circular_image(profile_file.stream, image_size_px)
            image_reader = ImageReader(circular_png)
        except Exception as e:
            # If processing fails, ignore and fall back to None
            print("Profile image processing error:", e)
            image_reader = None

    # If no uploaded image, try a placeholder in static (optional)
    if image_reader is None:
        try:
            with open("static/placeholder_profile.png", "rb") as f:
                circular_png = make_circular_image(f, image_size_px)
                image_reader = ImageReader(circular_png)
        except Exception:
            image_reader = None  # still None if placeholder missing

    # Create PDF in memory
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Sidebar
    sidebar_w = 180
    sidebar_color = HexColor("#2CB1B5")
    c.setFillColor(sidebar_color)
    c.rect(0, 0, sidebar_w, height, fill=1)

    # Draw circular profile image on sidebar (from top)
    if image_reader is not None:
        img_w = img_h = image_size_px
        # Convert px to points: ReportLab's default is 72 DPI; pillow default res is not guaranteed but this is okay for sizing
        # We'll draw the image at a fixed point size (in points)
        pt_size = 100  # points for the displayed image
        x_img = 40
        y_img = height - 60 - pt_size  # top margin 60
        c.drawImage(image_reader, x_img, y_img, width=pt_size, height=pt_size, mask='auto')

    # Sidebar white text/content
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 14)
    # If image present, start name a bit lower; else a bit higher
    start_y = height - 180 if image_reader else height - 100
    c.drawString(30, start_y, name)

    c.setFont("Helvetica", 10)
    c.drawString(30, start_y - 22, f"Age: {age}")
    c.drawString(30, start_y - 38, f"City: {city}")

    # Contact
    c.setFont("Helvetica-Bold", 12)
    c.drawString(30, start_y - 70, "CONTACT")
    c.setFont("Helvetica", 10)
    c.drawString(30, start_y - 90, phone)
    c.drawString(30, start_y - 106, email)

    # Skills
    c.setFont("Helvetica-Bold", 12)
    c.drawString(30, start_y - 140, "SKILLS")
    c.setFont("Helvetica", 10)
    c.drawString(30, start_y - 160, f"• {skill1}")
    c.drawString(30, start_y - 176, f"• {skill2}")
    c.drawString(30, start_y - 192, f"• {skill3}")

    # Right/main area
    x = sidebar_w + 20
    right_w = width - x - 40

    # Name big heading on right
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 26)
    c.drawString(x, height - 80, name)

    # Horizontal rule under name
    c.setLineWidth(1)
    c.line(x, height - 88, x + 220, height - 88)

    # About
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x, height - 120, "ABOUT")
    c.setFont("Helvetica", 11)
    about_text = c.beginText(x, height - 140)
    about_text.setLeading(14)
    # Wrap text manually to fit right_w
    from textwrap import wrap
    wrapped = []
    max_chars = 95  # approximate; not exact but decent
    for paragraph in about.split("\n"):
        lines = wrap(paragraph, width=90)
        if not lines:
            wrapped.append("")
        else:
            wrapped.extend(lines)
    for ln in wrapped:
        about_text.textLine(ln)
    c.drawText(about_text)

    # Education
    edu_y = height - 260
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x, edu_y, "EDUCATION")
    c.setFont("Helvetica", 11)
    edu_text = c.beginText(x, edu_y - 18)
    edu_text.setLeading(14)
    for line in education.split("\n"):
        edu_text.textLine(line)
    c.drawText(edu_text)

    # Finish up
    c.showPage()
    c.save()
    buffer.seek(0)

    return send_file(buffer, as_attachment=True,
                     download_name=f"{name}_CV.pdf",
                     mimetype="application/pdf")


if __name__ == "__main__":
    app.run(debug=True)
