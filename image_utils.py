from PIL import Image, ImageDraw, ImageFont
import qrcode
import os
import random
from pypdf import PdfReader, PdfWriter 

def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def generate_qr(data):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=40, 
        border=1,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    return img

def draw_text_with_bg(draw, xy, text, font, text_color, bg_color=(255, 255, 255)):
    x, y = xy
    bbox = draw.textbbox((x, y), text, font=font)
    padding_x = 40
    padding_y = 20
    rect = (bbox[0] - padding_x, bbox[1] - padding_y, bbox[2] + padding_x, bbox[3] + padding_y)
    draw.rectangle(rect, fill=bg_color)
    draw.text((x, y), text, font=font, fill=text_color)

# --- ФУНКЦІЯ ДЛЯ СТВОРЕННЯ МЕТАДАНИХ (BOOKMARKS) ---
def add_bookmarks(pdf_path, data, ticket_number):
    reader = PdfReader(pdf_path)
    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    # --- ЛОГІКА ВИЗНАЧЕННЯ STANDING ---
    section_name = str(data.get('section', '')).lower()
    is_standing_zone = 'dance' in section_name or 'fan' in section_name

    # 1. Корінь
    root = writer.add_outline_item("MAX KORZH", 0)

    # 2. Статичні дані
    writer.add_outline_item("23 May 2026, 18:00", 0, parent=root)
    writer.add_outline_item("NATIONAL ARENA BUCHAREST", 0, parent=root)
    writer.add_outline_item("BULEVARDUL BASARABIA 37-39, BUCUREȘTI, BUCHAREST, ROMANIA", 0, parent=root)

    # 3. ROW (ТІЛЬКИ якщо це НЕ dance/fan)
    if not is_standing_zone:
        row_val = str(data.get('row', '-'))
        row_parent = writer.add_outline_item("ROW", 0, parent=root)
        writer.add_outline_item(row_val, 0, parent=row_parent)

    # 4. SECTION: (Завжди)
    sec_val = str(data.get('section', '-'))
    sec_parent = writer.add_outline_item("SECTION:", 0, parent=root)
    writer.add_outline_item(sec_val, 0, parent=sec_parent)

    # 5. SEAT (ТІЛЬКИ якщо це НЕ dance/fan)
    if not is_standing_zone:
        seat_val = str(data.get('seat', '-'))
        seat_parent = writer.add_outline_item("SEAT", 0, parent=root)
        writer.add_outline_item(seat_val, 0, parent=seat_parent)

    # 6. PRICE:
    price_val = str(data.get('price', '0'))
    price_parent = writer.add_outline_item("PRICE:", 0, parent=root)
    writer.add_outline_item(f"{price_val} RON", 0, parent=price_parent)

    # 7. НОМЕР КВИТКА (Додано)
    writer.add_outline_item(ticket_number, 0, parent=root)

    # 8. ДИСКЛЕЙМЕР (Додано)
    writer.add_outline_item("Doors 16.00 / Show 18.00", 0, parent=root)

    with open(pdf_path, "wb") as f_out:
        writer.write(f_out)


def edit_ticket_pdf(data):
    random_suffix = f"{random.randint(0, 9999):04d}"
    ticket_number = f"7264.0724.{random_suffix}"
    
    disclaimer_text = (
        "Doors 16.00 / Show 18.00"
    )

    # --- ЛОГІКА ВИБОРУ ШАБЛОНУ ---
    has_seat = data.get('has_seat', True) 

    if has_seat is False:
        is_standing = True
        template_filename = "template_df.png"
    else:
        is_standing = False
        template_filename = "template.png"

    template_path = os.path.join("templates", template_filename)
    
    if not os.path.exists(template_path):
        return None, f"Помилка: Не знайдено файл {template_path}"

    img = Image.open(template_path).convert("RGB")
    draw = ImageDraw.Draw(img)
    width, height = img.size
    
    # --- ШРИФТИ ---
    try:
        font_data = ImageFont.truetype("browab_0.ttf", 328)   
        font_section = ImageFont.truetype("browab_0.ttf", 308) 
        font_ticket_num = ImageFont.truetype("browab_0.ttf", 260) 
        font_disclaimer = ImageFont.truetype("browab_0.ttf", 100)     
    except IOError:
        font_data = font_section = font_ticket_num = font_disclaimer = ImageFont.load_default()

    target_orange = hex_to_rgb("#fd9a0c") 
    black_color = (0, 0, 0)

    base_qr_x = 2258
    base_qr_y = 6326

    # QR position
    if not is_standing:
        pos_qr = (base_qr_x, base_qr_y + 400)
    else:
        pos_qr = (base_qr_x, base_qr_y)

    # --- МАЛЮВАННЯ ТЕКСТУ ---
    if is_standing:
        pos_section_stand = (697, 5780)
        pos_price_stand = (4729, 5768)
        draw_text_with_bg(draw, pos_section_stand, str(data['section']), font_section, target_orange)
        draw_text_with_bg(draw, pos_price_stand, str(data['price']), font_data, target_orange)
    else:
        pos_row = (697, 5524)
        pos_seat = (4729, 5524)
        pos_section_seat = (697, 6200)
        pos_price_seat = (4729, 6188)

        row_text = str(data['row']) if data['row'] else "-"
        draw_text_with_bg(draw, pos_row, row_text, font_data, target_orange)
        seat_text = str(data['seat']) if data['seat'] else "-"
        draw_text_with_bg(draw, pos_seat, seat_text, font_data, target_orange)
        draw_text_with_bg(draw, pos_section_seat, str(data['section']), font_section, target_orange)
        draw_text_with_bg(draw, pos_price_seat, str(data['price']), font_data, target_orange)

    # --- QR КОД (без крапок) ---
    qr_data = ticket_number.replace(".", "")
    qr_img = generate_qr(qr_data)
    
    qr_size = 2120
    qr_img = qr_img.resize((qr_size, qr_size)) 
    
    draw.rectangle((pos_qr[0], pos_qr[1], pos_qr[0] + qr_size, pos_qr[1] + qr_size), fill="white")
    img.paste(qr_img, pos_qr)

    # --- РОЗРАХУНОК РОЗМІЩЕННЯ (для переносу на стор. 2) ---
    qr_center_x = pos_qr[0] + (qr_size // 2)
    bbox_num = draw.textbbox((0, 0), ticket_number, font=font_ticket_num)
    num_w = bbox_num[2] - bbox_num[0]
    num_h = bbox_num[3] - bbox_num[1]
    
    text_num_x_page1 = qr_center_x - (num_w // 2)
    text_num_y_page1 = pos_qr[1] + qr_size + 60
    
    num_bottom_limit = text_num_y_page1 + num_h
    text_disc_y_page1 = num_bottom_limit + 150 
    
    if hasattr(draw, "multiline_textbbox"):
        bbox_disc = draw.multiline_textbbox((qr_center_x, text_disc_y_page1), disclaimer_text, font=font_disclaimer, anchor="ma", align="center")
        disc_bottom_limit = bbox_disc[3]
    else:
        lines = disclaimer_text.count('\n') + 1
        disc_bottom_limit = text_disc_y_page1 + (lines * 120)

    # --- OVERFLOW CHECK ---
    pages = [img]
    LIMIT_Y = 9000

    if disc_bottom_limit > LIMIT_Y or num_bottom_limit > LIMIT_Y:
        print(f"Контент перетнув межу {LIMIT_Y} пікселів! Переносимо номер і текст на сторінку 2.")
        
        template_page2_path = os.path.join("templates", "template_page2.png")
        if os.path.exists(template_page2_path):
            page2 = Image.open(template_page2_path).convert("RGB")
        else:
            page2 = Image.new("RGB", (width, height), "white")
            
        draw2 = ImageDraw.Draw(page2)
        
        num_y_page2 = 250 
        num_x_page2 = (width // 2) - (num_w // 2)
        draw2.text((num_x_page2, num_y_page2), ticket_number, font=font_ticket_num, fill=black_color)
        
        disc_y_page2 = num_y_page2 + num_h + 150
        draw2.text((width // 2, disc_y_page2), disclaimer_text, font=font_disclaimer, fill=black_color, anchor="ma", align="center")
        
        pages.append(page2)
        
    else:
        draw_text_with_bg(draw, (text_num_x_page1, text_num_y_page1), ticket_number, font_ticket_num, black_color)
        draw.text((qr_center_x, text_disc_y_page1), disclaimer_text, font=font_disclaimer, fill=black_color, anchor="ma", align="center")

    # --- SAVE ---
    if not os.path.exists("output"):
        os.makedirs("output")
        
    output_filename = f"output/ticket-20251202-3206{random_suffix}.pdf"
    
    pages[0].save(
        output_filename, 
        "PDF", 
        resolution=100.0, 
        save_all=True, 
        append_images=pages[1:]
    )
    
    # --- ADD METADATA ---
    try:
        add_bookmarks(output_filename, data, ticket_number)
        print(f"Метадані додано: {output_filename}")
    except Exception as e:
        print(f"Помилка метаданих: {e}")

    return output_filename, ticket_number