import os
import io
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
)
from PIL import Image, ImageDraw, ImageFont

# --- الإعدادات ---
# يمكنك تغيير نصوص الحقوق هنا
WATERMARK_TEXTS = ["صياد العروض", "@SayadAlorood"]
FONT_SIZE = 50
MARGIN = 20

# تعريف состояний المحادثة
CHOOSING, PHOTO = range(2)

# تعريف الألوان مع قيم RGBA (الرقم الأخير للشفافية)
COLORS = {
    "white": {"name": "أبيض ⚪", "value": (255, 255, 255, 128)},
    "black": {"name": "أسود ⚫", "value": (0, 0, 0, 128)},
    "red": {"name": "أحمر 🔴", "value": (255, 0, 0, 150)},
    "blue": {"name": "أزرق 🔵", "value": (0, 0, 255, 150)},
    "yellow": {"name": "أصفر 🟡", "value": (255, 255, 0, 180)},
}


# --- الدوال ---

def add_watermark(image_stream, texts, color):
    """تستقبل الصورة، قائمة نصوص، ولون، ثم تضيف الختم المائي."""
    try:
        image = Image.open(image_stream).convert("RGBA")
        txt_layer = Image.new("RGBA", image.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(txt_layer)

        try:
font = ImageFont.truetype("Elgharib-AlwiSahafa.ttf", FONT_SIZE)
except IOError:
            print("لم يتم العثور على خط Elgharib-AlwiSahafa.ttf، سيتم استخدام الخط الافتراضي.")
            font = ImageFont.load_default()

        total_text_height = 0
        lines_data = []

        # حساب أبعاد كل سطر
        for text in texts:
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            lines_data.append({'text': text, 'width': text_width, 'height': text_height})
            total_text_height += text_height

        # رسم النصوص من الأسفل للأعلى
        current_y = image.height - MARGIN
        for line in reversed(lines_data):
            current_y -= line['height']
            position = (image.width - line['width'] - MARGIN, current_y)
            draw.text(position, line['text'], font=font, fill=color)

        watermarked_image = Image.alpha_composite(image, txt_layer)

        final_buffer = io.BytesIO()
        watermarked_image.convert("RGB").save(final_buffer, "JPEG")
        final_buffer.seek(0)
        return final_buffer
    except Exception as e:
        print(f"حدث خطأ أثناء إضافة الحقوق: {e}")
        return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """تبدأ المحادثة بسؤال المستخدم عن اللون."""
    keyboard = [
        [
            InlineKeyboardButton(details["name"], callback_data=color_key)
            for color_key, details in list(COLORS.items())[:3]
        ],
        [
            InlineKeyboardButton(details["name"], callback_data=color_key)
            for color_key, details in list(COLORS.items())[3:]
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("أهلاً بك! يرجى اختيار لون الحقوق أولاً:", reply_markup=reply_markup)
    return CHOOSING


async def choose_color(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """تحفظ اختيار اللون وتطلب الصورة."""
    query = update.callback_query
    await query.answer()
    chosen_color_key = query.data

    # حفظ اللون المختار في بيانات المستخدم
    context.user_data["color"] = COLORS[chosen_color_key]["value"]
    
    await query.edit_message_text(
        text=f"ممتاز، تم اختيار اللون: {COLORS[chosen_color_key]['name']}\n\nالآن، أرسل الصورة لوضع الحقوق عليها."
    )
    return PHOTO


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """تعالج الصورة المرسلة وتضيف الحقوق."""
    # استرجاع اللون من بيانات المستخدم
    color = context.user_data.get("color")
    if not color:
        await update.message.reply_text("حدث خطأ، يرجى البدء من جديد بالأمر /start")
        return ConversationHandler.END

    await update.message.reply_text("تم استلام الصورة، جاري إضافة الحقوق...")

    photo_file = await update.message.photo[-1].get_file()
    image_buffer = io.BytesIO()
    await photo_file.download_to_memory(image_buffer)
    image_buffer.seek(0)

    watermarked_photo_buffer = add_watermark(image_buffer, WATERMARK_TEXTS, color)

    if watermarked_photo_buffer:
        await update.message.reply_photo(photo=watermarked_photo_buffer, caption="تم وضع الحقوق بنجاح!")
    else:
        await update.message.reply_text("عذرًا، حدث خطأ أثناء معالجة الصورة.")

    # إنهاء المحادثة بعد إتمام العملية
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """تلغي المحادثة الحالية."""
    await update.message.reply_text("تم إلغاء العملية. ابدأ من جديد مع /start.")
    return ConversationHandler.END


def main():
    """الدالة الرئيسية لتشغيل البوت."""
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    if not TOKEN:
        raise ValueError("لم يتم العثور على TELEGRAM_TOKEN! يرجى إعداده كمتغير بيئة.")

    application = Application.builder().token(TOKEN).build()

    # إعداد معالج المحادثة
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING: [CallbackQueryHandler(choose_color)],
            PHOTO: [MessageHandler(filters.PHOTO, handle_photo)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    
    print("البوت يعمل الآن...")
    application.run_polling()

if __name__ == "__main__":
    main()
