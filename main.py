import os
import io
from PIL import Image, ImageDraw, ImageFont
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- الإعدادات ---
WATERMARK_TEXT = "صياد العروض"
FONT_SIZE = 50
FONT_COLOR = (255, 255, 255, 128)
MARGIN = 20

# دالة لوضع الختم المائي على الصورة
def add_watermark(image_stream):
    try:
        image = Image.open(image_stream).convert("RGBA")
        txt_layer = Image.new("RGBA", image.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(txt_layer)
        
        try:
            # يفترض أن ملف الخط موجود في نفس المجلد
            font = ImageFont.truetype("Elgharib-AlwiSahaf.ttf", FONT_SIZE)
        except IOError:
            font = ImageFont.load_default()
            print("لم يتم العثور على خط Elgharib-AlwiSahaf.ttf، سيتم استخدام الخط الافتراضي.")
            
        text_bbox = draw.textbbox((0, 0), WATERMARK_TEXT, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        position = (image.width - text_width - MARGIN, image.height - text_height - MARGIN)
        draw.text(position, WATERMARK_TEXT, font=font, fill=FONT_COLOR)
        
        watermarked_image = Image.alpha_composite(image, txt_layer)
        
        final_buffer = io.BytesIO()
        watermarked_image.convert("RGB").save(final_buffer, "JPEG")
        final_buffer.seek(0)
        return final_buffer
    except Exception as e:
        print(f"حدث خطأ أثناء إضافة الحقوق: {e}")
        return None

# دالة لمعالجة الصور المستلمة
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo_file = await update.message.photo[-1].get_file()
    image_buffer = io.BytesIO()
    await photo_file.download_to_memory(image_buffer)
    image_buffer.seek(0)
    
    await update.message.reply_text("تم استلام الصورة، جاري إضافة الحقوق...")

    watermarked_photo_buffer = add_watermark(image_buffer)

    if watermarked_photo_buffer:
        await update.message.reply_photo(photo=watermarked_photo_buffer, caption="تم وضع الحقوق بنجاح!")
    else:
        await update.message.reply_text("عذرًا، حدث خطأ أثناء معالجة الصورة.")

# دالة لبدء التشغيل
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("أهلاً بك في بوت (صياد العروض)! أرسل لي أي صورة لوضع الحقوق عليها.")

def main():
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    if not TOKEN:
        raise ValueError("لم يتم العثور على TELEGRAM_TOKEN! يرجى إعداده كمتغير بيئة.")

    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    print("البوت يعمل الآن...")
    application.run_polling()

if __name__ == "__main__":
    main()
