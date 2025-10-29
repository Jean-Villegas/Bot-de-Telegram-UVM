# 🤖 Bot de Recordatorios Académicos - Moodle + Telegram

Bot **persistente e inteligente** que te mantiene al día con tus tareas universitarias de Moodle.

## ✨ Características Avanzadas

- 🤖 **Bot persistente** - Se mantiene activo las 24 horas
- 💬 **Comandos interactivos** - Consulta tus tareas cuando quieras
- ⏰ **Recordatorios automáticos** - Te avisa a hora específica (13:00)
- 📅 **Extracción inteligente** - Identifica automáticamente las materias
- 🎓 **Organizado por materia** - Computación Gráfica, Backend, etc.
- 🚦 **Código de colores** - Urgencia visual (rojo=hoy, amarillo=mañana)
- 🇻🇪 **Zona horaria Venezuela** - Configurado para América/Caracas
- 🛡️ **Seguro y robusto** - Manejo completo de errores

## 🚀 Instalación

1. **Clona o descarga** este proyecto
2. **Instala las dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

## ⚙️ Configuración

### 1. Crear un Bot de Telegram

1. Habla con [@BotFather](https://t.me/BotFather) en Telegram
2. Usa el comando `/newbot` y sigue las instrucciones
3. Copia el token que te proporciona

### 2. Obtener tu Chat ID

1. Habla con [@userinfobot](https://t.me/userinfobot) en Telegram
2. Te enviará tu Chat ID

### 3. Configurar el bot

Edita el archivo `main.py` en las líneas 12-13:
```python
TELEGRAM_TOKEN = "TU_TOKEN_AQUÍ"
CHAT_ID = "TU_CHAT_ID_AQUÍ"
```

### 4. Configurar tu URL de Moodle

Si tu URL de Moodle es diferente, actualiza la línea 14 en `main.py`

## 🚀 Modo de Uso

### 1. **Iniciar el Bot Persistente:**
```bash
python main.py
```
El bot se mantendrá **activo permanentemente**, esperando comandos y ejecutando recordatorios automáticos.

### 2. **Comandos de Telegram:**

#### `/start`
- Muestra información del bot y comandos disponibles
- Confirma que el bot está activo

#### `/tareas`
- **📋 Consulta manual** - Muestra tareas de los **próximos 7 días**
- Código de colores:
  - 🔴 **¡HOY!** - Vence hoy
  - 🟡 **Mañana** - Vence mañana  
  - 🟠 **En X días** - Vence en 2-3 días
  - 🟢 **En X días** - Vence en 4-7 días

### 3. **Recordatorios Automáticos:**
- ⏰ **Todos los días a las 13:00 (1 PM)**
- 📢 Te avisa cuando falten: **5, 3, 2, y 1 días**
- 🎯 Solo para tareas próximas a vencer
- 🤖 **Completamente automático** - sin intervención

### 4. **Ejecución Permanente (Recomendado):**

**Opción A - Consola:**
```bash
# Mantener la consola abierta
python main.py
```

**Opción B - Servicio Windows:**
1. Crear `bot_service.bat`:
```batch
@echo off
cd /d "C:\Users\Jean\Desktop\bot_telegram"
python main.py
```

2. Programar en **Programador de Tareas**:
   - Ejecutar al inicio del sistema
   - Ejecutar permanentemente
   - Reiniciar si falla

## 📋 Funcionalidades Completas

### 🤖 **Bot Persistente:**
- ✅ **Ejecuta 24/7** - Se mantiene activo permanentemente
- ✅ **Responde a comandos** - Interfaz interactiva vía Telegram
- ✅ **Scheduler integrado** - Recordatorios automáticos programados
- ✅ **Manejo robusto** - Se recupera automáticamente de errores

### 📚 **Gestión Inteligente de Tareas:**
- ✅ **Extrae materias automáticamente** - CompGraf → Computación Gráfica
- ✅ **Consulta manual** - `/tareas` para ver próximos 7 días
- ✅ **Recordatorios automáticos** - A las 13:00 cuando falten 5,3,2,1 días
- ✅ **Formato organizado** - Por materia, fecha y urgencia
- ✅ **Código de colores** - Identificación visual de urgencia

### 🔧 **Técnico:**
- ✅ **Conexión Moodle** - Extrae calendario automáticamente
- ✅ **Zona horaria Venezuela** - América/Caracas
- ✅ **Logging completo** - Seguimiento detallado de actividad
- ✅ **Seguridad** - Autorización por Chat ID

## 🔧 Solución de Problemas

### Error de conexión:
- Verifica tu conexión a internet
- Confirma que la URL de Moodle sea correcta

### Bot no responde:
- Verifica que el token del bot sea correcto
- Asegúrate de que el Chat ID sea tu ID personal

### Error de módulos:
- Ejecuta: `pip install -r requirements.txt`

### Bot no se mantiene activo:
- Verifica que no hayas cerrado la consola
- Usa el Programador de Tareas para ejecución permanente
- Revisa los logs para errores específicos

### Comandos no responden:
- Verifica que el Chat ID sea correcto
- Confirma que el bot esté iniciado (debe mostrar "Bot Iniciado")
- Usa `/start` para verificar conexión

## 📝 Notas de Seguridad

- **NO compartas tu token** del bot
- Considera usar variables de entorno para mayor seguridad
- El archivo `config_ejemplo.txt` tiene instrucciones para variables de entorno

## 💬 Ejemplos de Uso

### **Consulta Manual:**
```
Tú: /tareas
Bot: 📋 Tareas Pendientes - Próximos 7 días

1. 🔴 ¡HOY!
🎓 Computación Gráfica
📝 Vencimiento de e-actividad 4.0 - Presentación de ideas de Proyectos
📅 2025-10-28

2. 🟡 Mañana
🎓 Backend / Desarrollo Backend  
📝 Vencimiento de e-actividad 2.1
📅 2025-10-29
```

### **Recordatorio Automático:**
```
Bot (13:00): 📚 Recordatorio Automático

🔴 ¡URGENTE! - Vence mañana

🎓 Materia: Computación Gráfica
📝 Actividad: Vencimiento de e-actividad 3.2 . Modelado de escena en Blender
📅 Fecha límite: 2025-10-29
⏰ Faltan 1 día(s) para entregar.
```

## 🤝 Contribuciones

¡Las contribuciones son bienvenidas! Por favor crea un issue o pull request.

---
*🎓 Desarrollado para estudiantes universitarios de Venezuela 🇻🇪*  
*🤖 Bot inteligente y persistente para una mejor gestión académica*
