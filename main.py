import logging
import pandas as pd
import threading
from flask import Flask
from telegram import Update
from telegram.ext import Application, ChatJoinRequestHandler, MessageHandler, filters, ContextTypes

# Configuración de servidor Flask dummy para Render Free Tier
app_web = Flask(__name__)

@app_web.route('/')
def home():
    return "Bot Verificador PNF SST activo 24/7"

def run_web():
    app_web.run(host='0.0.0.0', port=10000)

# Configuración de registros (logs)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- DATOS CONFIGURADOS OFICIALES ---
TOKEN_BOT = "8846578757:AAESE81HBDL4b4f9SdqK-hhv131OlwNsoY0"
URL_CSV = "https://docs.google.com/spreadsheets/d/e/2PACX-1vT5Nn1xZ1I6K3U8A0jO9sX-lK9wKz_s2J/pub?output=csv"

async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    request = update.chat_join_request
    user_id = request.from_user.id
    chat_id = request.chat.id
    
    context.bot_data[user_id] = chat_id
    
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text="👋 **¡Hola! Bienvenido al proceso de ingreso del PNF SST.**\n\n"
                 "Para aprobar tu solicitud de acceso al grupo, por favor **responde a este mensaje enviando tu número de Cédula de Identidad** (solo números, sin puntos ni letras).\n\n"
                 " Ejemplo: `12345678`"
        )
        logging.info(f"Solicitud recibida de {user_id}. Mensaje enviado.")
    except Exception as e:
        logging.error(f"No se pudo enviar mensaje a {user_id}: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    
    if user_id not in context.bot_data:
        await update.message.reply_text("No tengo ninguna solicitud de ingreso pendiente registrada para ti.")
        return
        
    chat_id = context.bot_data[user_id]
    await update.message.reply_text("🔍 Verificando tu número de cédula en el registro de inscripción...")
    
    try:
        df = pd.read_csv(URL_CSV)
        col_cedula = [col for col in df.columns if 'cedula' in col.lower() or 'documento' in col.lower() or 'identidad' in col.lower()]
        
        if col_cedula:
            col_name = col_cedula[0]
            cedulas = df[col_name].astype(str).str.replace(r'\D', '', regex=True).tolist()
            cedula_usuario = ''.join(filter(str.isdigit, text))
            
            if cedula_usuario in cedulas:
                await context.bot.approve_chat_join_request(chat_id=chat_id, user_id=user_id)
                await update.message.reply_text("✅ **¡Inscripción verificada exitosamente!**\n\nTu solicitud de ingreso ha sido aprobada. Ya puedes acceder al grupo.")
                del context.bot_data[user_id]
            else:
                await update.message.reply_text(
                    "❌ **Cédula no encontrada en el registro de inscripción.**\n\n"
                    "Por favor, verifica el número e inténtalo de nuevo.\n\n"
                    "Si aún no te has registrado en la actividad, debes completar la inscripción ingresando al siguiente enlace:\n"
                    "👉 https://forms.gle/sUgBFykejJxXMdWY7\n\n"
                    "Una vez completado el formulario, vuelve a enviar tu número de cédula por aquí."
                )
        else:
            await update.message.reply_text(" Error técnico: No se encontró la columna de Cédula en la base de datos. Por favor contacta al administrador.")
            
    except Exception as e:
        logging.error(f"Error al verificar cédula: {e}")
        await update.message.reply_text(" Ocurrió un error al consultar la base de datos. Por favor intenta más tarde.")

def main():
    # Iniciar servidor Flask en un hilo independiente para satisfacer el plan Free de Render
    threading.Thread(target=run_web, daemon=True).start()

    app = Application.builder().token(TOKEN_BOT).build()
    app.add_handler(ChatJoinRequestHandler(handle_join_request))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🤖 Bot Verificador operando en vivo...")
    app.run_polling()

if __name__ == '__main__':
    main()
