from flask import Flask, request, render_template as render, send_file, redirect, url_for
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.utils import ImageReader
from io import BytesIO
from PIL import Image, ImageDraw
from textwrap import wrap

app = Flask(__name__)

def make_circular_image(file_stream, size_px):
    try:
        img = Image.open(file_stream).convert("RGBA")
        # crop to square
        min_side = min(img.size)
        left = (img.width - min_side) // 2
        top = (img.height - min_side) // 2
        img = img.crop((left, top, left + min_side, top + min_side))
        img = img.resize((size_px, size_px), Image.LANCZOS)

        mask = Image.new("L", (size_px, size_px), 0)
        d = ImageDraw.Draw(mask)
        d.ellipse((0, 0, size_px - 1, size_px - 1), fill=255)

        out = Image.new("RGBA", (size_px, size_px))
        out.paste(img, (0, 0), mask=mask)

        # optional white border
        border = Image.new("RGBA", (size_px, size_px))
        bd = ImageDraw.Draw(border)
        bd.ellipse((1, 1, size_px - 2, size_px - 2), outline=(255, 255, 255, 255), width=3)
        out = Image.alpha_composite(out, border)

        b = BytesIO()
        out.save(b, format="PNG")
        b.seek(0)
        return ImageReader(b)
    except Exception:
        return None

def draw_wrapped(canvas_obj, x, y, text, max_width, font_name="Helvetica", font_size=10, leading=14):
    canvas_obj.setFont(font_name, font_size)
    lines = []
    for paragraph in text.split("\n"):
        # approximate max chars per line based on font_size; use wrap with a heuristic
        # we will attempt wrapping by characters; adjust width to chars ratio:
        approx_chars = max(30, int(max_width / (font_size * 0.55)))
        for ln in wrap(paragraph, width=approx_chars):
            lines.append(ln)
        if paragraph.strip() == "":
            lines.append("")
    for ln in lines:
        canvas_obj.drawString(x, y, ln)
        y -= leading
    return y

@app.route('/')
def home():
    return render("index.html")

@app.route('/form')
def form():
    return render("form.html")

@app.route('/generate-pdf', methods=['POST'])
def generate_pdf():
    # Collect fields
    name = request.form.get("name", "Your Name")
    title = request.form.get("title", "")
    profile = request.form.get("profile_text", "")
    experiences = request.form.get("experiences", "")  # expected blocks separated by blank lines
    education = request.form.get("education", "")
    skills = request.form.get("skills", "")
    languages = request.form.get("languages", "")
    hobbies = request.form.get("hobbies", "")
    phone = request.form.get("phone", "")
    email = request.form.get("email", "")
    address = request.form.get("address", "")

    # Profile image
    profile_file = request.files.get("photo")
    image_reader = None
    if profile_file and profile_file.filename:
        image_reader = make_circular_image(profile_file.stream, 120)

    # fallback placeholder if static exists
    if image_reader is None:
        try:
            with open("static/placeholder_profile.png", "rb") as f:
                image_reader = make_circular_image(f, 120)
        except Exception:
            image_reader = None

    # Create PDF
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Colors and layout
    blue = HexColor("#1E73BE")  # professional blue
    left_col_w = 190
    margin = 40

    # Header: Full width top bar with name and title centered
    c.setFillColor(blue)
    c.rect(0, height - 90, width, 90, fill=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 26)
    c.drawString(margin, height - 60, name)
    c.setFont("Helvetica", 12)
    c.drawString(margin, height - 80, title)

    # Right under header: start main content below header
    y_start = height - 110

    # Left column background soft (light gray)
    c.setFillColor(HexColor("#F5F7FA"))
    c.rect(margin, margin, left_col_w - margin + 10, height - 150, fill=1, stroke=0)

    # Place profile image at top of left column (if present)
    if image_reader:
        img_x = margin + 20
        img_y = height - 190
        c.drawImage(image_reader, img_x, img_y, width=110, height=110, mask='auto')

    # LEFT column content positions
    left_x = margin + 10
    current_y = height - 220

    # CONTACT block (left)
    c.setFillColor(black)
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(blue)
    c.drawString(left_x, current_y, "CONTACT")
    c.setFillColor(black)
    current_y -= 18
    c.setFont("Helvetica", 10)
    if phone: c.drawString(left_x, current_y, phone); current_y -= 14
    if email: c.drawString(left_x, current_y, email); current_y -= 14
    if address:
        # wrap address
        current_y -= 4
        current_y = draw_wrapped(c, left_x, current_y, address, left_col_w - 30, font_size=9, leading=12)

    current_y -= 10

    # SKILLS block
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(blue)
    c.drawString(left_x, current_y, "SKILLS")
    current_y -= 16
    c.setFillColor(black)
    c.setFont("Helvetica", 10)
    # skills comma separated -> bullet lines
    for s in [s.strip() for s in skills.split(",") if s.strip()]:
        c.drawString(left_x + 6, current_y, u"• " + s)
        current_y -= 14

    current_y -= 6

    # LANGUAGES block
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(blue)
    c.drawString(left_x, current_y, "LANGUAGES")
    current_y -= 16
    c.setFillColor(black)
    c.setFont("Helvetica", 10)
    for ln in [l.strip() for l in languages.split(",") if l.strip()]:
        c.drawString(left_x + 6, current_y, u"• " + ln)
        current_y -= 14

    current_y -= 6

    # HOBBIES block
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(blue)
    c.drawString(left_x, current_y, "HOBBIES")
    current_y -= 16
    c.setFillColor(black)
    c.setFont("Helvetica", 10)
    for h in [h.strip() for h in hobbies.split(",") if h.strip()]:
        c.drawString(left_x + 6, current_y, u"• " + h)
        current_y -= 14

    # RIGHT column main content
    right_x = left_col_w + 30
    right_w = width - right_x - margin

    # PROFILE (right)
    cur_y = height - 120
    c.setFillColor(blue)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(right_x, cur_y, "PROFILE")
    cur_y -= 18
    c.setFillColor(black)
    c.setFont("Helvetica", 10)
    cur_y = draw_wrapped(c, right_x, cur_y, profile, right_w, font_size=10, leading=14)
    cur_y -= 8

    # WORK EXPERIENCE
    c.setFillColor(blue)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(right_x, cur_y, "WORK EXPERIENCE")
    cur_y -= 18
    c.setFillColor(black)
    c.setFont("Helvetica", 10)

    # Parse experiences: separate by blank lines. Each block: first line Job Title, second line Company - Dates, following lines bullets
    exp_blocks = []
    raw_blocks = [b.strip() for b in experiences.split("\n\n") if b.strip()]
    for b in raw_blocks:
        lines = [l for l in b.split("\n") if l.strip()]
        if not lines:
            continue
        title_line = lines[0]
        company_dates = lines[1] if len(lines) > 1 else ""
        bullets = lines[2:] if len(lines) > 2 else []
        exp_blocks.append((title_line, company_dates, bullets))

    for (job, company_dates, bullets) in exp_blocks:
        # Job title bold
        c.setFont("Helvetica-Bold", 11)
        c.drawString(right_x, cur_y, job)
        # Company / dates smaller, right-aligned on same line
        if company_dates:
            c.setFont("Helvetica", 9)
            # draw dates at right edge
            text_w = c.stringWidth(company_dates, "Helvetica", 9)
            c.drawString(right_x + right_w - text_w, cur_y, company_dates)
        cur_y -= 14
        # company name line if included in company_dates or separate
        if company_dates and "-" in company_dates:
            # already shown
            pass
        # bullets
        c.setFont("Helvetica", 10)
        for bt in bullets:
            # wrap long bullet
            bullet_lines = wrap(bt, width=100)
            first = True
            for bl in bullet_lines:
                prefix = u"• " if first else "  "
                c.drawString(right_x + 8, cur_y, prefix + bl)
                cur_y -= 12
                first = False
        cur_y -= 6
        # if we run low on page, create new page (basic check)
        if cur_y < margin + 120:
            c.showPage()
            # re-draw header area on new page (minimal)
            c.setFillColor(blue)
            c.rect(0, height - 90, width, 90, fill=1)
            c.setFillColor(white)
            c.setFont("Helvetica-Bold", 20)
            c.drawString(margin, height - 60, name)
            cur_y = height - 120

    # EDUCATION
    c.setFillColor(blue)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(right_x, cur_y, "EDUCATION")
    cur_y -= 18
    c.setFillColor(black)
    c.setFont("Helvetica", 10)
    for line in [l for l in education.split("\n") if l.strip()]:
        # each education line may be "Degree - Institution (dates)"
        cur_y = draw_wrapped(c, right_x, cur_y, line, right_w, font_size=10, leading=12)
        cur_y -= 6

    # Finish and save
    c.showPage()
    c.save()
    buffer.seek(0)

    return send_file(buffer, as_attachment=True,
                     download_name=f"{name.replace(' ', '_')}_Resume.pdf",
                     mimetype="application/pdf")

if __name__ == "__main__":
    app.run(debug=True)
