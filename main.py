import httpx
from ics import Calendar
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.request import HTTPXRequest
import pytz
import asyncio
import os
import schedule
import threading
import logging
import time as time_module
import re

# Cargar variables de entorno desde .env
try:
    from dotenv import load_dotenv
    # load_dotenv()  # Comentado temporalmente para debugging
except ImportError:
    print("⚠️ python-dotenv no instalado. Usando variables de entorno del sistema.")

# CONFIGURACIÓN
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("❌ Token de Telegram no encontrado. Configura la variable TELEGRAM_TOKEN como variable de entorno.")
# Chats autorizados: tu chat personal + tu grupo
AUTHORIZED_CHATS = ["6632759708", "-5061302808"]
MOODLE_URL = "https://virtual.uvm.edu.ve/virtual/calendar/export_execute.php?userid=2007&authtoken=5be6f027de4a2016615289e3ef3cb40c425c14ab&preset_what=all&preset_time=recentupcoming"

HORA_RECORDATORIOS = "20:44"
DIAS_RECORDATORIO = [5, 3, 2, 1]

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

tz = pytz.timezone("America/Caracas")

def extraer_materia(nombre_evento, descripcion, categorias=None):
    """Extrae el nombre de la materia desde categorías, título o descripción"""
    codigos_materias = {
        'Back': 'Backend (Ingeniería De La Programación)',
        'Backend': 'Backend (Ingeniería De La Programación)',
        'Computación Gráfica': 'Computación Gráfica VI',
        'CompGraf': 'Computación Gráfica VI',
        'Dis Log': 'Diseño Lógico I',
        'Dis Log I': 'Diseño Lógico I',
        'DisLogI': 'Diseño Lógico I',
        'Diseño Lógico': 'Diseño Lógico I', 
        'Est Desc': 'Estadística Descriptiva',
        'EstDesc': 'Estadística Descriptiva',
        'Estadística': 'Estadística Descriptiva',
        'Estadistica': 'Estadística Descriptiva',
        'Fis I': 'Física I',
        'FisI': 'Física I',
        'Física': 'Física I',
        'Fisica': 'Física I',
        'Mat III': 'Matemática III',
        'Mat Iii': 'Matemática III',
        'MatIII': 'Matemática III',
        'Matemática': 'Matemática III',
        'Matematica': 'Matemática III',
        'Matematicas': 'Matemática III',
        'Ingeniería de Computación': 'Ingeniería de Computación',
        'Materias Comunes': 'Materias Comunes'
    }
    
    # Buscar en categorías de Moodle
    if categorias:
        for categoria in categorias:
            categoria_str = str(categoria)
            for codigo, nombre in codigos_materias.items():
                if codigo.lower() in categoria_str.lower():
                    return nombre
            # Usar categoría formateada si no coincide
            categoria_limpia = re.sub(r'20\d+[A-Z]', '', categoria_str)
            if len(categoria_limpia) > 2:
                return re.sub(r'([a-z])([A-Z])', r'\1 \2', categoria_limpia).title()
    
    # Buscar en título y descripción
    texto_completo = f"{nombre_evento} {descripcion}".lower()
    for codigo, nombre in codigos_materias.items():
        if codigo.lower() in texto_completo:
            return nombre
    
    # Extraer usando patrones
    match = re.search(r'(\w+(?:\s+\w+)*)\s*[-:]', texto_completo)
    if match:
        materia = match.group(1).strip().title()
        if not any(palabra in materia.lower() for palabra in ['vencimiento', 'actividad', 'tarea', 'examen']):
            return materia
    
    return "Materia no identificada"

app = None
bot_global = None

async def obtener_tareas_calendario(dias_limite=7):
    """Obtiene las tareas del calendario de Moodle filtradas por días"""
    max_intentos = 3
    timeout_inicial = 10.0
    
    for intento in range(max_intentos):
        try:
            logger.info(f"Obteniendo calendario de Moodle... (intento {intento + 1}/{max_intentos})")
            
            # Hacer la petición asíncrona con timeout progresivo
            timeout_actual = timeout_inicial + (intento * 5)  # 10s, 15s, 20s
            async with httpx.AsyncClient(timeout=timeout_actual) as client:
                r = await client.get(MOODLE_URL)
                r.raise_for_status()  # Verificar que la respuesta sea exitosa
        
            calendar = Calendar(r.text)

            hoy = datetime.now(tz).date()
            tareas = []
            
            for evento in calendar.events:
                if evento.begin is None:
                    continue
                    
                fecha_entrega = evento.begin.astimezone(tz).date()
                dias_restantes = (fecha_entrega - hoy).days

                # Filtrar por días límite
                if 0 <= dias_restantes <= dias_limite:
                    nombre_evento = str(evento.name) if evento.name else "Sin título"
                    descripcion = str(evento.description) if hasattr(evento, 'description') and evento.description else ""
                    categorias = evento.categories if hasattr(evento, 'categories') and evento.categories else set()
                    
                    materia = extraer_materia(nombre_evento, descripcion, categorias)
                    
                    tareas.append({
                        'nombre': nombre_evento,
                        'materia': materia,
                        'fecha_entrega': fecha_entrega,
                        'dias_restantes': dias_restantes
                    })
        
            # Ordenar por días restantes
            tareas.sort(key=lambda x: x['dias_restantes'])
            logger.info(f"✅ Calendario obtenido exitosamente: {len(tareas)} tareas encontradas")
            return tareas
            
        except Exception as e:
            logger.warning(f"⚠️ Intento {intento + 1} falló: {e}")
            if intento < max_intentos - 1:
                tiempo_espera = (intento + 1) * 2  # 2s, 4s
                logger.info(f"🔄 Reintentando en {tiempo_espera} segundos...")
                await asyncio.sleep(tiempo_espera)
            else:
                logger.error(f"❌ Error al obtener calendario después de {max_intentos} intentos: {e}")
                return []

# === COMANDO /tareas ===
async def comando_tareas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando para mostrar tareas pendientes en los próximos 7 días"""
    try:
        chat_id = update.effective_chat.id
        
        logger.info(f"Comando /tareas recibido de chat {chat_id}")
        
        # Verificar que sea un chat autorizado
        if str(chat_id) not in AUTHORIZED_CHATS:
            await update.message.reply_text("❌ No tienes autorización para usar este bot.")
            return
        
        # Mensaje de estado más rápido
        mensaje_estado = await update.message.reply_text("🔄 Consultando Moodle...")
        
        tareas = await obtener_tareas_calendario(dias_limite=7)
        
        # Borrar mensaje de estado y mostrar resultado
        await mensaje_estado.delete()
        
        if not tareas:
            mensaje = "✅ *¡Genial!*\n\nNo tienes tareas pendientes en los próximos 7 días. 🎉"
            await update.message.reply_text(mensaje, parse_mode="Markdown")
            return
        
        # Formatear mensaje con todas las tareas
        mensaje = f"📋 *Tareas Pendientes - Próximos 7 días*\n\n"
        
        for i, tarea in enumerate(tareas, 1):
            if tarea['dias_restantes'] == 0:
                urgencia = "🔴 *¡HOY!*"
            elif tarea['dias_restantes'] == 1:
                urgencia = "🟡 *Mañana*"
            elif tarea['dias_restantes'] <= 3:
                urgencia = f"🟠 *En {tarea['dias_restantes']} días*"
            else:
                urgencia = f"🟢 *En {tarea['dias_restantes']} días*"
            
            materia_texto = f"🎓 *{tarea['materia']}*\n" if tarea['materia'] else ""
            
            mensaje += (
                f"*{i}.* {urgencia}\n"
                f"{materia_texto}"
                f"📝 {tarea['nombre']}\n"
                f"📅 {tarea['fecha_entrega']}\n\n"
            )
        
        # Enviar resultado
        await update.message.reply_text(mensaje, parse_mode="Markdown")
            
    except Exception as e:
        logger.error(f"Error en comando /tareas: {e}")
        try:
            await mensaje_estado.delete()
        except:
            pass
        await update.message.reply_text("❌ Error al conectar con Moodle. Intenta nuevamente.")

async def comando_mes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando para mostrar tareas pendientes en los próximos 30 días"""
    try:
        chat_id = update.effective_chat.id
        
        logger.info(f"Comando /mes recibido de chat {chat_id}")
        
        # Verificar que sea un chat autorizado
        if str(chat_id) not in AUTHORIZED_CHATS:
            await update.message.reply_text("❌ No tienes autorización para usar este bot.")
            return
        
        # Mensaje de estado
        mensaje_estado = await update.message.reply_text("🔄 Consultando tareas del mes completo...")
        
        tareas = await obtener_tareas_calendario(dias_limite=30)
        
        # Borrar mensaje de estado
        await mensaje_estado.delete()
        
        if not tareas:
            mensaje = "✅ *¡Increíble!*\n\nNo tienes tareas pendientes en los próximos 30 días. 🎉"
            await update.message.reply_text(mensaje, parse_mode="Markdown")
            return
        
        # Agrupar tareas por semana
        tareas_semana = {"Esta semana (0-7 días)": [], "Próxima semana (8-14 días)": [], 
                        "Tercera semana (15-21 días)": [], "Cuarta semana (22-30 días)": []}
        
        for tarea in tareas:
            dias = tarea['dias_restantes']
            if 0 <= dias <= 7:
                tareas_semana["Esta semana (0-7 días)"].append(tarea)
            elif 8 <= dias <= 14:
                tareas_semana["Próxima semana (8-14 días)"].append(tarea)
            elif 15 <= dias <= 21:
                tareas_semana["Tercera semana (15-21 días)"].append(tarea)
            else:
                tareas_semana["Cuarta semana (22-30 días)"].append(tarea)
        
        # Formatear mensaje por semanas
        mensaje = f"📅 *Tareas Pendientes - Próximos 30 días*\n"
        mensaje += f"📊 *Total: {len(tareas)} tareas*\n\n"
        
        for semana, lista_tareas in tareas_semana.items():
            if lista_tareas:
                mensaje += f"📍 *{semana}*\n"
                for tarea in lista_tareas:
                    if tarea['dias_restantes'] == 0:
                        urgencia = "🔴"
                    elif tarea['dias_restantes'] <= 3:
                        urgencia = "🟡"
                    elif tarea['dias_restantes'] <= 7:
                        urgencia = "🟠"
                    else:
                        urgencia = "🟢"
                    
                    materia_texto = f"🎓 *{tarea['materia']}*" if tarea['materia'] != "Materia no identificada" else "📚"
                    mensaje += f"{urgencia} {materia_texto}\n📝 {tarea['nombre']}\n📅 {tarea['fecha_entrega']} ({tarea['dias_restantes']}d)\n\n"
                
                mensaje += "➖➖➖➖➖➖➖\n\n"
        
        # Enviar resultado
        await update.message.reply_text(mensaje, parse_mode="Markdown")
            
    except Exception as e:
        logger.error(f"Error en comando /mes: {e}")
        try:
            await mensaje_estado.delete()
        except:
            pass
        await update.message.reply_text("❌ Error al conectar con Moodle. Intenta nuevamente.")

# === RECORDATORIOS AUTOMÁTICOS ===
async def enviar_recordatorios_automaticos(bot=None):
    """Envía recordatorios automáticos para tareas que vencen en 5, 3, 2, 1 días"""
    try:
        logger.info("Ejecutando verificación de recordatorios automáticos...")
        
        tareas = await obtener_tareas_calendario(dias_limite=5)
        
        # Filtrar solo las tareas que necesitan recordatorio
        tareas_recordatorio = [t for t in tareas if t['dias_restantes'] in DIAS_RECORDATORIO]
        
        if not tareas_recordatorio:
            logger.info("No hay tareas que requieran recordatorio hoy")
            return
        
        # Usar el bot pasado como parámetro o el global
        if bot is None:
            bot = bot_global
        
        if bot is None:
            logger.error("No se pudo obtener el bot para enviar recordatorios")
            return
        
        for tarea in tareas_recordatorio:
            dias = tarea['dias_restantes']
            
            if dias == 1:
                urgencia = "🔴 *¡URGENTE!* - Vence mañana"
            elif dias == 2:
                urgencia = "🟡 *¡Importante!* - Vence pasado mañana"
            elif dias == 3:
                urgencia = "🟠 *Recordatorio* - Vence en 3 días"
            else:
                urgencia = f"🟢 *Recordatorio* - Vence en {dias} días"
            
            materia_texto = f"🎓 *Materia:* {tarea['materia']}\n" if tarea['materia'] else ""
            
            mensaje = (
                f"📚 *Recordatorio Automático*\n\n"
                f"{urgencia}\n\n"
                f"{materia_texto}"
                f"📝 *Actividad:* {tarea['nombre']}\n"
                f"📅 *Fecha límite:* {tarea['fecha_entrega']}\n"
                f"⏰ Faltan *{dias} día(s)* para entregar."
            )
            
            # Enviar recordatorios a todos los chats autorizados
            for chat_id in AUTHORIZED_CHATS:
                try:
                    await bot.send_message(chat_id=chat_id, text=mensaje, parse_mode="Markdown")
                    logger.info(f"Recordatorio enviado a chat {chat_id}")
                except Exception as e:
                    logger.error(f"Error enviando recordatorio a chat {chat_id}: {e}")
            logger.info(f"Recordatorio automático enviado: {tarea['materia']} - {tarea['nombre']}")
            
    except Exception as e:
        logger.error(f"Error en recordatorios automáticos: {e}")

# === FUNCIÓN PARA VERIFICAR RECORDATORIOS (EJECUTA A LAS 20:25) ===
def verificar_recordatorios():
    """Función que se ejecuta en el scheduler para verificar recordatorios"""
    # Crear un nuevo loop de eventos para esta función
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(enviar_recordatorios_automaticos(bot_global))
    finally:
        loop.close()

# === COMANDO /status ===
async def comando_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando para verificar el estado del bot"""
    chat_id = update.effective_chat.id
    
    # Verificar que sea un chat autorizado
    if str(chat_id) not in AUTHORIZED_CHATS:
        await update.message.reply_text("❌ No tienes autorización para usar este bot.")
        return
    
    try:
        # Verificar conexión con Telegram
        bot = bot_global if bot_global else app.bot
        me = await bot.get_me()
        
        # Verificar conexión con Moodle
        moodle_status = "❌ Error"
        try:
            tareas = await obtener_tareas_calendario(dias_limite=1)
            moodle_status = f"✅ OK ({len(tareas)} tareas encontradas)"
        except Exception as e:
            moodle_status = f"❌ Error: {str(e)[:50]}..."
        
        # Información del sistema
        import datetime
        ahora = datetime.datetime.now()
        proximo_recordatorio = f"Mañana a las {HORA_RECORDATORIOS}"
        
        mensaje = (
            f"🤖 Estado del Bot\n\n"
            f"📡 Telegram: ✅ Conectado como @{me.username}\n"
            f"🌐 Moodle: {moodle_status}\n"
            f"⏰ Recordatorios: {proximo_recordatorio}\n"
            f"🕐 Hora actual: {ahora.strftime('%H:%M:%S')}\n"
            f"📅 Fecha: {ahora.strftime('%d/%m/%Y')}\n\n"
            f"💡 Comandos disponibles:\n"
            f"• /start - Información del bot\n"
            f"• /tareas - Tareas próximas 7 días\n"
            f"• /mes - Tareas próximos 30 días\n"
            f"• /status - Estado del bot"
        )
        
        await update.message.reply_text(mensaje)
        
    except Exception as e:
        logger.error(f"Error en comando /status: {e}")
        logger.error(f"Tipo de error: {type(e).__name__}")
        logger.error(f"Bot global disponible: {bot_global is not None}")
        logger.error(f"App disponible: {app is not None}")
        await update.message.reply_text(f"❌ Error al verificar el estado del bot: {str(e)[:100]}")

# === COMANDO /start ===
async def comando_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando de bienvenida"""
    chat_id = update.effective_chat.id
    
    # Verificar que sea un chat autorizado
    if str(chat_id) not in AUTHORIZED_CHATS:
        await update.message.reply_text("❌ No tienes autorización para usar este bot.")
        return
    
    mensaje = (
        "🤖 *Bot de Recordatorios Académicos*\n\n"
        "¡Hola! Soy tu asistente para recordatorios de tareas de Moodle.\n\n"
        "*Comandos disponibles:*\n"
        "• `/tareas` - Ver tareas pendientes (próximos 7 días)\n"
        "• `/mes` - Ver todas las tareas del mes (próximos 30 días)\n"
        "• `/start` - Mostrar este mensaje\n\n"
        "*Recordatorios automáticos:*\n"
        f"• Todos los días a las {HORA_RECORDATORIOS}\n"
        "• Te aviso cuando falten 5, 3, 2, y 1 días\n\n"
        "✅ ¡El bot está activo y funcionando!"
    )
    
    await update.message.reply_text(mensaje, parse_mode="Markdown")

# === FUNCIÓN PRINCIPAL DEL BOT ===
async def main():
    """Función principal del bot persistente"""
    global app
    
    logger.info("🤖 Iniciando Bot de Recordatorios Académicos...")
    
    # Configurar request optimizado
    request = HTTPXRequest(
        connection_pool_size=4,
        connect_timeout=10.0,
        read_timeout=15.0,
        write_timeout=10.0,
        pool_timeout=15.0
    )
    
    # Crear aplicación con configuración mejorada
    app = Application.builder().token(TELEGRAM_TOKEN).request(request).build()
    
    # Añadir handlers de comandos
    app.add_handler(CommandHandler("start", comando_start))
    app.add_handler(CommandHandler("tareas", comando_tareas))
    app.add_handler(CommandHandler("mes", comando_mes))
    app.add_handler(CommandHandler("status", comando_status))
    
    # Programar recordatorios automáticos
    schedule.every().day.at(HORA_RECORDATORIOS).do(verificar_recordatorios)
    
    # Función para ejecutar el scheduler en un hilo separado
    def run_scheduler():
        while True:
            schedule.run_pending()
            time_module.sleep(60)  # Verificar cada minuto
    
    # Iniciar scheduler en hilo separado
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    # Función para mantener el bot activo (keep-alive)
    async def keep_alive():
        """Envía un ping cada 30 minutos para mantener el bot activo"""
        while True:
            await asyncio.sleep(1800)  # 30 minutos
            try:
                await bot.get_me()
                logger.info("🔄 Keep-alive: Bot activo")
            except Exception as e:
                logger.warning(f"⚠️ Keep-alive falló: {e}")
    
    # Iniciar keep-alive en tarea separada
    asyncio.create_task(keep_alive())
    
    # Verificar conexión con reintentos
    bot = app.bot
    global bot_global
    bot_global = bot  # Asignar bot global para el scheduler
    
    logger.info("🔗 Verificando conexión con Telegram... (v2.1)")
    for intento in range(3):
        try:
            # Verificar que el bot funcione
            me = await bot.get_me()
            logger.info(f"✅ Conectado como: @{me.username}")
            
            # Enviar mensaje de inicio
            await bot.send_message(
                chat_id="6632759708", 
                text=f"🤖 *Bot Iniciado*\n\n✅ Bot activo y funcionando\n⏰ Recordatorios automáticos a las {HORA_RECORDATORIOS}\n💬 Usa `/tareas` para ver pendientes\n🏠 Funciona en chat personal y grupo",
                parse_mode="Markdown"
            )
            break
            
        except Exception as e:
            logger.warning(f"⚠️ Intento {intento + 1}/3 falló: {e}")
            if intento < 2:
                logger.info("🔄 Reintentando en 5 segundos...")
                await asyncio.sleep(5)
            else:
                logger.error("❌ No se pudo conectar con Telegram después de 3 intentos")
                return
    
    logger.info("✅ Bot iniciado correctamente")
    logger.info(f"⏰ Recordatorios programados para las {HORA_RECORDATORIOS}")
    logger.info("📡 Bot ejecutándose... Presiona Ctrl+C para detener")
    
    # Ejecutar bot con manejo de errores mejorado
    try:
        await app.initialize()
        await app.start()
        await app.updater.start_polling(drop_pending_updates=True)
        
        # Mantener el bot corriendo
        try:
            # El bot se ejecutará indefinidamente hasta que se interrumpa
            await asyncio.Event().wait()
        except (asyncio.CancelledError, KeyboardInterrupt):
            logger.info("🛑 Deteniendo bot...")
            pass
            
    except Exception as e:
        logger.error(f"❌ Error durante la ejecución del bot: {e}")
        raise
    finally:
        # Limpiar recursos
        try:
            if app.updater.running:
                await app.updater.stop()
            await app.stop()
            await app.shutdown()
        except Exception as e:
            logger.warning(f"Error durante la limpieza: {e}")

# === EJECUTAR ===
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Bot detenido por el usuario")
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}")
