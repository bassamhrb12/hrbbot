import os
import io
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from PIL import Image, ImageDraw, ImageFont

# --- الإعدادات ---
WATERMARK_TEXTS = ["صياد العروض"]
DEFAULT_COLOR = (0, 0, 0, 60)  # اللون الأسود الشفاف هو اللون الافتراضي
FONT_SIZE = 40
ROTATION_ANGLE = 30
TILE_PADDING = 100

# تعريف الألوان المتاحة للتغيير
COLORS = {
    "white": {"name": "أبيض ⚪", "value": (255, 255, 255, 60)},
    "black": {"name": "أسود ⚫", "value": (0, 0, 0, 60)},
    "red": {"name": "أحمر 🔴", "value": (255, 0, 0, 70)},
    "blue": {"name": "أزرق 🔵", "value": (0, 0, 255, 70)},
    "yellow": {"name": "أصفر 🟡", "value": (255, 255, 0, 75)},
}


# --- الدوال ---

def add_watermark(image_stream, texts, color):
    """تستقبل الصورة وتضيف ختم مائي متكرر وموزع."""
    try:
        base_image = Image.open(image_stream).convert("RGBA")
        watermark_layer = Image.new("RGBA", base_image.size, (255, 255, 255, 0))
        watermark_draw = ImageDraw.Draw(watermark_layer)
        
        try:
            font = ImageFont.truetype("Elgharib-AlwiSahafa.ttf", FONT_SIZE)
        except IOError:
            print("لم يتم العثور على الخط المخصص، سيتم استخدام الخط الافتراضي.")
            font = ImageFont.load_default()

        text_to_repeat = texts[0]
        text_bbox = watermark_draw.textbbox((0, 0), text_to_repeat, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        tile_width = int(text_width + TILE_PADDING)
        tile_height = int(text_height + TILE_PADDING)

        for x in range(-tile_width, base_image.width, tile_width):
            for y in range(-tile_height, base_image.height, tile_height * 2):
                watermark_draw.text((x, y), text_to_repeat, font=font, fill=color, anchor="ms", angle=ROTATION_ANGLE)

        final_image = Image.alpha_composite(base_image, watermark_layer)

        final_buffer = io.BytesIO()
        final_image.convert("RGB").save(final_buffer, "JPEG")
        final_buffer.seek(0)
        return final_buffer
        
    except Exception as e:
        print(f"حدث خطأ أثناء إضافة الحقوق: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رسالة ترحيبية وإرشادية."""
    await update.message.reply_text(
        "أهلاً بك!\n\n"
        "- أرسل أي صورة لوضع الحقوق عليها باللون الافتراضي (الأسود).\n"
        "- لتغيير لون الحقوق، استخدم الأمر /color."
    )

async def color_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يعرض قائمة الألوان للاختيار."""
    keyboard = [
        [InlineKeyboardButton(details["name"], callback_data=key) for key, details in list(COLORS.items())]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("اختر لون الحقوق الجديد:", reply_markup=reply_markup)

async def change_color(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يحفظ اللون الذي اختاره المستخدم."""
    query = update.callback_query
    await query.answer()
    chosen_color_key = query.data

    # حفظ اللون المختار في بيانات المستخدم لهذه المحادثة
    context.user_data["color"] = COLORS[chosen_color_key]["value"]
    
    await query.edit_message_text(
        text=f"تم تغيير اللون بنجاح إلى: {COLORS[chosen_color_key]['name']}\n"
             f"جميع الصور التالية ستستخدم هذا اللون."
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """يعالج أي صورة يتم إرسالها."""
    # تحقق إذا كان المستخدم قد اختار لوناً من قبل، وإلا استخدم اللون الافتراضي
    color_to_use = context.user_data.get("color", DEFAULT_COLOR)
    
    await update.message.reply_text("تم استلام الصورة، جاري إضافة الحقوق...")

    photo_file = await update.message.photo[-1].get_file()
    image_buffer = io.BytesIO()
    await photo_file.download_to_memory(image_buffer)
    image_buffer.seek(0)

    watermarked_photo_buffer = add_watermark(image_buffer, WATERMARK_TEXTS, color_to_use)

    if watermarked_photo_buffer:
        await update.message.reply_photo(photo=watermarked_photo_buffer, caption="تم وضع الحقوق بنجاح!")
    else:
        await update.message.reply_text("عذرًا، حدث خطأ أثناء معالجة الصورة.")

def main():
    """الدالة الرئيسية لتشغيل البوت."""
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    if not TOKEN:
        raise ValueError("لم يتم العثور على TELEGRAM_TOKEN! يرجى إعداده كمتغير بيئة.")

    application = Application.builder().token(TOKEN).build()

    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("color", color_command))
    application.add_handler(CallbackQueryHandler(change_color)) # لمعالجة ضغط الأزرار
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    print("البوت يعمل الآن...")
    application.run_polling()

if __name__ == "__main__":
    main()
