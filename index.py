from flask import Flask, request, render_template as render, send_file, redirect, url_for, flash
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.utils import ImageReader
from io import BytesIO
from PIL import Image, ImageDraw
from textwrap import wrap
from werkzeug.utils import secure_filename
from PIL import Image
from fpdf import FPDF
import os
import zipfile
from pdf2image import convert_from_path
from werkzeug.utils import secure_filename
# from pdf2docx import Converter # New Import for DOCX conversion
from io import BytesIO

app = Flask(__name__)
app.secret_key = 'super_secret_key_for_flash'

def make_circular_image(file_stream, size_px):
    """Crops an image into a circle, resizes it, and returns a ReportLab ImageReader."""
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
    """Draws wrapped text onto the canvas."""
    canvas_obj.setFont(font_name, font_size)
    lines = []
    
    # Calculate approx chars per line based on font size and max width
    approx_chars = max(30, int(max_width / (font_size * 0.55)))
    
    for paragraph in text.split("\n"):
        if paragraph.strip():
            # Use textwrap to split the paragraph into lines
            for ln in wrap(paragraph, width=approx_chars):
                lines.append(ln)
        # Handle explicit newlines/empty paragraphs for spacing
        else:
            lines.append("")
            
    for ln in lines:
        canvas_obj.drawString(x, y, ln)
        y -= leading
    return y

@app.route('/')
def home():
    # Placeholder to serve the main HTML file
    return render("index.html")

@app.route('/form')
def form():
    # Placeholder to serve the form HTML file
    return render("form.html")

@app.route('/generate-pdf', methods=['POST'])
def generate_pdf():
    # Collect fields
    name = request.form.get("name", "Your Name")
    title = request.form.get("title", "Job Title")
    profile = request.form.get("profile_text", "A brief professional summary...")
    experiences = request.form.get("experiences", "")
    education = request.form.get("education", "")
    skills = request.form.get("skills", "")
    languages = request.form.get("languages", "")
    hobbies = request.form.get("hobbies", "")
    phone = request.form.get("phone", "")
    email = request.form.get("email", "")
    address = request.form.get("address", "")

    # Profile image processing
    profile_file = request.files.get("photo")
    image_reader = None
    if profile_file and profile_file.filename:
        image_reader = make_circular_image(profile_file.stream, 120)
    
    # Create PDF
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Colors and layout constants
    blue = HexColor("#2C3E50")  # Dark professional blue
    light_gray = HexColor("#F5F7FA")
    left_col_w = 190
    margin = 40
    
    # --- New Top Section Layout (Name, Title, Image) ---
    
    img_size = 120
    img_x = margin
    # Define top content start Y coordinate (40 pts from top margin)
    y_start = height - margin 
    img_y = y_start - img_size - 10 
    
    # 1. Image placement (top-left)
    if image_reader:
        c.drawImage(image_reader, img_x, img_y, width=img_size, height=img_size, mask='auto')

    # 2. Name and Title (next to image)
    name_x = img_x + img_size + 20
    name_y = img_y + img_size - 35 # Align slightly below top of image
    
    c.setFillColor(blue) # Use dark blue for the name
    c.setFont("Helvetica-Bold", 32)
    c.drawString(name_x, name_y, name)
    
    name_y -= 30
    c.setFont("Helvetica", 16)
    c.drawString(name_x, name_y, title)
    
    # New Y position for subsequent main content blocks (below the image area)
    content_y_start = img_y - 30 
    
    # --- Left Column Background (Sidebar) ---
    left_col_end_y = margin
    c.setFillColor(light_gray)
    # The gray rect starts from the new content Y position
    c.rect(margin, left_col_end_y, left_col_w - margin + 10, content_y_start - left_col_end_y, fill=1, stroke=0)

    # --- Left Column Content ---
    left_x = margin + 10
    current_y = content_y_start - 10 # Start content inside the gray box
    leading = 16 # Increased vertical spacing in left column
    
    # CONTACT block (left)
    c.setFillColor(blue)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(left_x, current_y, "CONTACT")
    c.setFillColor(black)
    current_y -= leading
    c.setFont("Helvetica", 10)
    if phone: c.drawString(left_x, current_y, phone); current_y -= leading
    if email: c.drawString(left_x, current_y, email); current_y -= leading
    if address:
        current_y -= 4
        # draw_wrapped is used with increased leading
        current_y = draw_wrapped(c, left_x, current_y, address, left_col_w - 30, font_size=9, leading=14) 
    
    current_y -= 15

    # SKILLS block
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(blue)
    c.drawString(left_x, current_y, "SKILLS")
    current_y -= leading
    c.setFillColor(black)
    c.setFont("Helvetica", 10)
    for s in [s.strip() for s in skills.split(",") if s.strip()]:
        c.drawString(left_x + 6, current_y, u"• " + s)
        current_y -= leading

    current_y -= 10

    # LANGUAGES block
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(blue)
    c.drawString(left_x, current_y, "LANGUAGES")
    current_y -= leading
    c.setFillColor(black)
    c.setFont("Helvetica", 10)
    for ln in [l.strip() for l in languages.split(",") if l.strip()]:
        c.drawString(left_x + 6, current_y, u"• " + ln)
        current_y -= leading

    current_y -= 10

    # HOBBIES block
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(blue)
    c.drawString(left_x, current_y, "HOBBIES")
    current_y -= leading
    c.setFillColor(black)
    c.setFont("Helvetica", 10)
    for h in [h.strip() for h in hobbies.split(",") if h.strip()]:
        c.drawString(left_x + 6, current_y, u"• " + h)
        current_y -= leading

    # --- Right Column Main Content ---
    right_x = left_col_w + 30
    right_w = width - right_x - margin
    leading_r = 16 # Increased vertical spacing in right column

    # PROFILE (right) - Aligned with the start of the left column content
    cur_y = content_y_start - 10 
    
    c.setFillColor(blue)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(right_x, cur_y, "PROFILE")
    cur_y -= leading_r
    c.setFillColor(black)
    c.setFont("Helvetica", 10)
    # Use draw_wrapped for the profile section
    cur_y = draw_wrapped(c, right_x, cur_y, profile, right_w, font_size=10, leading=14)
    cur_y -= 15

    # WORK EXPERIENCE
    c.setFillColor(blue)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(right_x, cur_y, "WORK EXPERIENCE")
    cur_y -= leading_r
    c.setFillColor(black)
    c.setFont("Helvetica", 10)

    # Parse experiences
    exp_blocks = []
    raw_blocks = [b.strip() for b in experiences.split("\n\n") if b.strip()]
    for b in raw_blocks:
        lines = [l for l in b.split("\n") if l.strip()]
        if not lines: continue
        title_line = lines[0]
        company_dates = lines[1] if len(lines) > 1 else ""
        bullets = lines[2:] if len(lines) > 2 else []
        exp_blocks.append((title_line, company_dates, bullets))

    for (job, company_dates, bullets) in exp_blocks:
        # Job title bold
        c.setFont("Helvetica-Bold", 11)
        c.drawString(right_x, cur_y, job)
        cur_y -= 14 # Space down for the next line

        # Company / dates
        if company_dates:
            c.setFont("Helvetica", 9)
            # Use draw_wrapped for company/dates in case it's long
            cur_y = draw_wrapped(c, right_x, cur_y, company_dates, right_w, font_size=9, leading=12)
            cur_y += 1 # Correction from draw_wrapped's automatic leading step
        
        # bullets
        c.setFont("Helvetica", 10)
        bullet_x = right_x + 8
        bullet_w = right_w - 8
        bullet_leading = 14 # Bullet leading
        
        for bt in bullets:
            # Re-implementing wrapping for bullet points for better control
            lines = []
            approx_chars = max(30, int(bullet_w / (10 * 0.55))) # 10 is font size
            for ln in wrap(bt, width=approx_chars):
                lines.append(ln)

            first = True
            for bl in lines:
                prefix = u"• " if first else "  " # Indent subsequent lines
                c.drawString(bullet_x, cur_y, prefix + bl)
                cur_y -= bullet_leading
                first = False

        cur_y -= 18 # Increased vertical spacing between experience blocks

        # Basic page overflow check (simplified, only checks against bottom margin)
        if cur_y < margin + 60:
            c.showPage()
            # Reset Y position for new page
            cur_y = height - margin - 10 # Start content lower than top margin
            c.setFillColor(blue)
            c.setFont("Helvetica-Bold", 14)
            # Add a small header/title on continuation pages
            c.drawString(margin, height - 30, f"{name} - Continuation")
            c.drawString(right_x, cur_y, "WORK EXPERIENCE (Cont.)")
            cur_y -= leading_r
            c.setFillColor(black)
            c.setFont("Helvetica", 10)

    # EDUCATION
    c.setFillColor(blue)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(right_x, cur_y, "EDUCATION")
    cur_y -= leading_r
    c.setFillColor(black)
    c.setFont("Helvetica", 10)
    
    for line in [l for l in education.split("\n") if l.strip()]:
        # Each education line may be "Degree - Institution (dates)"
        cur_y = draw_wrapped(c, right_x, cur_y, line, right_w, font_size=10, leading=14)
        cur_y -= 6

    # Finish and save
    c.showPage()
    c.save()
    buffer.seek(0)

    return send_file(buffer, as_attachment=True,
                     download_name=f"{name.replace(' ', '_')}_Resume.pdf",
                     mimetype="application/pdf")


# Set a safe directory for uploads
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# Define allowed extensions
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'pdf', 'docx'}

def allowed_file(filename):
    """Checks if the file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Conversion Logic ---

def convert_jpg_to_pdf(jpg_path, pdf_path):
    """
    Converts a single JPG image to a PDF file using Pillow and fpdf2, 
    matching the PDF page size to the image size.
    """
    try:
        # 1. Open the image
        img = Image.open(jpg_path)
        width_px, height_px = img.size

        # 2. Initialize PDF object with custom size (in points, 1pt = 1/72 inch)
        pdf = FPDF(unit='pt', format=[width_px, height_px]) 
        pdf.add_page()
        
        # 3. Add the image to the PDF, covering the entire page
        # w and h are set to the full page dimensions (width_px, height_px)
        pdf.image(jpg_path, x=0, y=0, w=width_px, h=height_px)

        # 4. Output the PDF file
        pdf.output(pdf_path)
        return True
    except Exception as e:
        print(f"Conversion error: {e}")
        return False


@app.route('/jpg-to-pdf')
def jpg_to_pdf():
    return render('jpg_to_pdf.html')

@app.route('/jpgtopdf', methods=['POST'])
def jpgToPdf():
    if request.method == 'POST':
        # Check if the post request has the file part
        if 'file' not in request.files:
            return redirect(request.url)
        
        file = request.files['file']
        
        # If user does not select file, browser also submits an empty part
        if file.filename == '':
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            # 1. Securely save the uploaded file
            filename = secure_filename(file.filename)
            jpg_filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(jpg_filepath)
            
            # 2. Define the output PDF filename and path
            # e.g., 'myimage.jpg' -> 'myimage.pdf'
            base_filename = os.path.splitext(filename)[0]
            pdf_filename = f"{base_filename}.pdf"
            pdf_filepath = os.path.join(app.config['UPLOAD_FOLDER'], pdf_filename)
            
            # 3. Perform the conversion
            if convert_jpg_to_pdf(jpg_filepath, pdf_filepath):
                # 4. Send the converted PDF for download
                return send_file(
                    pdf_filepath,
                    mimetype='application/pdf',
                    as_attachment=True,
                    download_name=pdf_filename
                )
            else:
                return "Error during conversion.", 500


def allowed_file(filename):
    """Checks if the file extension is allowed."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Conversion & Zipping Logic ---

def convert_pdf_to_jpg_and_zip(pdf_path, temp_dir, zip_filepath):
    """
    Converts all pages of a PDF to JPGs and zips them.

    :param pdf_path: Path to the input PDF.
    :param temp_dir: Temporary directory to save the individual JPGs.
    :param zip_filepath: Path where the final zip file will be saved.
    :returns: True on success, False on failure.
    """
    try:
        # 1. Convert PDF pages to a list of Pillow Image objects
        # Using 200 DPI for a good balance of quality and file size
        images = convert_from_path(pdf_path, dpi=200)

        # 2. Prepare for zipping
        base_filename = os.path.splitext(os.path.basename(pdf_path))[0]
        
        with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 3. Iterate, save each image, and add it to the zip file
            for i, image in enumerate(images):
                output_filename = f"{base_filename}_page_{i + 1}.jpg"
                output_filepath = os.path.join(temp_dir, output_filename)
                
                # Save the image (quality=90 for high quality JPEG)
                image.save(output_filepath, 'JPEG', quality=90)
                
                # Add the saved JPG to the zip file
                zipf.write(output_filepath, arcname=output_filename)
                
                # Clean up the individual JPG file immediately
                os.remove(output_filepath)
        
        return True
    
    except Exception as e:
        print(f"Conversion or Zipping error: {e}")
        # A common error is Poppler not being found.
        if "No such file or directory" in str(e):
            flash("❌ Conversion Failed! Poppler utility might not be installed or configured correctly.", "error")
        else:
            flash(f"❌ Conversion failed due to an unexpected error: {e}", "error")
        return False



@app.route("/pdf-to-jpg")
def pdf_to_jpg():
    return render("pdf_to_jpg.html")

@app.route('/pdf-jpg', methods=['GET', 'POST'])
def convert_pdf():
    if request.method == 'POST':
        # Check if file exists in request
        if 'file' not in request.files:
            flash("No file part in the request.", "error")
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash("No selected file.", "error")
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            # 1. Securely save the uploaded PDF
            filename = secure_filename(file.filename)
            pdf_filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(pdf_filepath)
            
            # 2. Define output paths
            base_filename = os.path.splitext(filename)[0]
            zip_filename = f"{base_filename}_images.zip"
            zip_filepath = os.path.join(app.config['UPLOAD_FOLDER'], zip_filename)
            
            # 3. Perform the conversion and zipping
            if convert_pdf_to_jpg_and_zip(pdf_filepath, app.config['UPLOAD_FOLDER'], zip_filepath):
                # 4. Clean up the uploaded PDF file
                os.remove(pdf_filepath)
                
                # 5. Send the zipped JPGs for download
                return send_file(
                    zip_filepath,
                    mimetype='application/zip',
                    as_attachment=True,
                    download_name=zip_filename
                )
            else:
                # If conversion failed, clean up the uploaded file and redirect
                if os.path.exists(pdf_filepath):
                    os.remove(pdf_filepath)
                return redirect(url_for('pdf_to_jpg'))


# def convert_pdf_to_docx(pdf_filepath, docx_buffer):
#     """
#     Converts a PDF file to a DOCX file and writes the result to a BytesIO buffer.
    
#     :param pdf_filepath: Path to the input PDF file.
#     :param docx_buffer: BytesIO buffer to store the output DOCX data.
#     :returns: True on success, False on failure.
#     """
#     try:
#         cv = Converter(pdf_filepath)
#         # Convert the PDF and write the output directly to the buffer.
#         # This prevents saving a large file to the disk before sending it.
#         cv.convert(docx_buffer)
#         cv.close()
#         docx_buffer.seek(0)
#         return True
#     except Exception as e:
#         print(f"PDF to DOCX conversion error: {e}")
#         flash(f"❌ Conversion failed! Error: {e}", "error")
#         return False

@app.route('/pdf-to-docx', methods=['GET', 'POST'])
def pdf_to_docx():
    """Handles the PDF to DOCX conversion form submission."""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash("No file part in the request.", "error")
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash("No selected file.", "error")
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            # 1. Securely save the uploaded PDF to disk (pdf2docx needs a file path)
            filename = secure_filename(file.filename)
            pdf_filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(pdf_filepath)
            
            # 2. Define the output DOCX buffer and filename
            docx_buffer = BytesIO()
            base_filename = os.path.splitext(filename)[0]
            docx_filename = f"{base_filename}.docx"

            # 3. Perform the conversion
            if convert_pdf_to_docx(pdf_filepath, docx_buffer):
                # 4. Clean up the uploaded PDF file immediately
                os.remove(pdf_filepath)
                
                # 5. Send the converted DOCX for download
                return send_file(
                    docx_buffer,
                    mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    as_attachment=True,
                    download_name=docx_filename
                )
            else:
                # 4. Clean up the uploaded PDF file on failure
                if os.path.exists(pdf_filepath):
                    os.remove(pdf_filepath)
                return redirect(url_for('pdf_to_docx'))
        
        # Path for disallowed file extension (if someone tries to upload non-pdf)
        flash("Disallowed file type. Only PDF is allowed.", "error")
        return redirect(request.url)

    # Handles GET request or fallback after failure
    return render_template('pdf_to_docx.html')

if __name__ == '__main__':
    # Clean up the uploads folder on server start (optional but recommended)
    for f in os.listdir(UPLOAD_FOLDER):
        os.remove(os.path.join(UPLOAD_FOLDER, f))
        
    app.run(debug=True)
