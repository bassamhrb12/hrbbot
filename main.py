import os
import io
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler
from PIL import Image, ImageDraw, ImageFont

# --- Settings ---
WATERMARK_TEXTS = ["صياد العروض", "@SayadAlorood"]
DEFAULT_COLOR = (0, 0, 0, 60)  # Default color is transparent black
FONT_SIZE = 40
ROTATION_ANGLE = 30
TILE_PADDING = 100

# Available colors for the /color command
COLORS = {
    "white": {"name": "أبيض ⚪", "value": (255, 255, 255, 60)},
    "black": {"name": "أسود ⚫", "value": (0, 0, 0, 60)},
    "red": {"name": "أحمر 🔴", "value": (255, 0, 0, 70)},
    "blue": {"name": "أزرق 🔵", "value": (0, 0, 255, 70)},
    "yellow": {"name": "أصفر 🟡", "value": (255, 255, 0, 75)},
}


# --- Functions ---

def add_watermark(image_stream, texts, color):
    """Receives an image and adds a repeating, distributed watermark."""
    try:
        base_image = Image.open(image_stream).convert("RGBA")
        watermark_layer = Image.new("RGBA", base_image.size, (255, 255, 255, 0))
        watermark_draw = ImageDraw.Draw(watermark_layer)
        
        try:
            font = ImageFont.truetype("Elgharib-AlwiSahafa.ttf", FONT_SIZE)
        except IOError:
            print("Custom font not found, using default.")
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
        print(f"Error adding watermark: {e}")
        return None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Sends the new welcome and instructions message."""
    intro_text = """
أهلاً بك في بوت حقوق "صياد العروض"! 📸

وظيفتي هي إضافة العلامة المائية "صياد العروض" على أي صورة ترسلها لي للحفاظ على حقوقك.

*كيف تستخدم البوت؟*
- أرسل صورة مباشرةً لوضع العلامة المائية عليها باللون الافتراضي (أسود).
- لتغيير لون العلامة المائية، استخدم الأمر /color.
"""
    await update.message.reply_text(intro_text, parse_mode='Markdown')

async def color_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Displays the color selection keyboard."""
    keyboard = [
        [InlineKeyboardButton(details["name"], callback_data=key) for key, details in list(COLORS.items())]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("اختر لون الحقوق الجديد:", reply_markup=reply_markup)

async def change_color(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Saves the user's chosen color."""
    query = update.callback_query
    await query.answer()
    chosen_color_key = query.data

    context.user_data["color"] = COLORS[chosen_color_key]["value"]
    
    await query.edit_message_text(
        text=f"تم تغيير اللون بنجاح إلى: {COLORS[chosen_color_key]['name']}\n"
             f"جميع الصور التالية ستستخدم هذا اللون."
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processes any photo sent to the bot."""
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
    """Main function to run the bot."""
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    if not TOKEN:
        raise ValueError("TELEGRAM_TOKEN not found! Please set it as an environment variable.")

    application = Application.builder().token(TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("color", color_command))
    application.add_handler(CallbackQueryHandler(change_color))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
