import os
import requests

# ============================================
# CONFIGURACIÓN - SOLO NOMBRES DE VARIABLES
# ============================================

# Todas estas son solo REFERENCIAS a variables en Render
CONFIG = {
    'api_key': os.environ.get('DEEPSEEK_API_KEY'),
    'model': os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat'),
    'max_tokens': int(os.environ.get('MAX_TOKENS', '300')),
    'temperature': float(os.environ.get('TEMPERATURE', '0.7'))
}

def send_to_deepseek(message):
    """Envía mensaje a DeepSeek API"""
    
    # Verificar que la API key esté configurada
    if not CONFIG['api_key']:
        return {"error": "API key no configurada en Render"}
    
    # Usar la API key (que viene de Render, no del código)
    headers = {
        "Authorization": f"Bearer {CONFIG['api_key']}",
        # El valor REAL de {CONFIG['api_key']} viene de Render
    }

def construir_prompt_para_deepseek(nombre_personaje, contexto, mensaje_usuario, apodo_usuario):
    """
    Construye un prompt optimizado para DeepSeek usando el formato de mensajes de chat.
    DeepSeek usa el formato estándar de OpenAI (ChatML).
    """
    # El contexto ya viene estructurado desde api_cht.php con formato:
    # Eres {nombre}. {descripcion}... --- PERSONALIDAD --- ... --- HISTORIAL DE CONVERSACIÓN --- ... --- MENSAJE ACTUAL --- ...
    
    # Para DeepSeek, vamos a crear un sistema que contenga las instrucciones del personaje
    # y luego el historial como mensajes anteriores.
    
    # Primero, extraemos las partes del contexto
    sistema_prompt = f"Eres {nombre_personaje}. "
    
    # Buscamos las secciones del contexto
    partes = contexto.split("---")
    
    # La primera parte es la descripción básica
    if partes:
        # Extraemos la descripción (antes de cualquier sección ---)
        primera_parte = partes[0]
        # Removemos "Eres {nombre}." si ya está
        primera_parte = primera_parte.replace(f"Eres {nombre_personaje}.", "").strip()
        sistema_prompt += primera_parte
    
    # Para las demás partes, las añadimos como instrucciones
    for i in range(1, len(partes)):
        parte = partes[i].strip()
        if parte.startswith("PERSONALIDAD"):
            sistema_prompt += f"\n\nPersonalidad:\n{parte.replace('PERSONALIDAD ---', '').strip()}"
        elif parte.startswith("ESTILO DE DIÁLOGO"):
            sistema_prompt += f"\n\nEstilo de diálogo:\n{parte.replace('ESTILO DE DIÁLOGO ---', '').strip()}"
        elif parte.startswith("REGLAS DE ROLEPLAY"):
            sistema_prompt += f"\n\nReglas de roleplay:\n{parte.replace('REGLAS DE ROLEPLAY ---', '').strip()}"
        elif parte.startswith("EJEMPLOS DE CONVERSACIÓN"):
            sistema_prompt += f"\n\nEjemplos de conversación:\n{parte.replace('EJEMPLOS DE CONVERSACIÓN ---', '').strip()}"
    
    # Limpiar caracteres extraños
    sistema_prompt = sistema_prompt.replace('\r\n', '\n').replace('\r', '\n')
    
    return sistema_prompt

def extraer_historial_del_contexto(contexto, apodo_usuario, nombre_personaje):
    """
    Extrae el historial de conversación del contexto para convertirlo a formato de mensajes.
    """
    mensajes = []
    
    # Buscar la sección de historial
    if "--- HISTORIAL DE CONVERSACIÓN ---" in contexto:
        partes = contexto.split("--- HISTORIAL DE CONVERSACIÓN ---")
        if len(partes) > 1:
            historial_parte = partes[1]
            # Limitar a la siguiente sección "---" si existe
            if "---" in historial_parte:
                historial_parte = historial_parte.split("---")[0]
            
            # Procesar líneas del historial
            lineas = historial_parte.strip().split('\n')
            for linea in lineas:
                linea = linea.strip()
                if not linea:
                    continue
                
                # Buscar patrones como "apodo: mensaje" o "nombre: mensaje"
                if f"{apodo_usuario}:" in linea:
                    contenido = linea.split(f"{apodo_usuario}:")[1].strip()
                    mensajes.append({"role": "user", "content": contenido})
                elif f"{nombre_personaje}:" in linea:
                    contenido = linea.split(f"{nombre_personaje}:")[1].strip()
                    mensajes.append({"role": "assistant", "content": contenido})
    
    return mensajes

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.get_json()
    nombre_personaje = data.get('nombre_personaje', '')
    contexto = data.get('contexto', '')
    mensaje_usuario = data.get('mensaje_usuario', '')
    apodo_usuario = data.get('apodo_usuario', '')

    if not nombre_personaje or not contexto or not mensaje_usuario or not apodo_usuario:
        return jsonify({'error': 'Faltan datos'}), 400

    # Construir el prompt del sistema para DeepSeek
    sistema_prompt = construir_prompt_para_deepseek(nombre_personaje, contexto, mensaje_usuario, apodo_usuario)
    
    # Extraer historial del contexto
    historial_mensajes = extraer_historial_del_contexto(contexto, apodo_usuario, nombre_personaje)
    
    # Preparar la lista de mensajes para DeepSeek
    messages = []
    
    # 1. Añadir el prompt del sistema
    messages.append({
        "role": "system",
        "content": sistema_prompt
    })
    
    # 2. Añadir el historial de conversación (si existe)
    for msg in historial_mensajes:
        messages.append(msg)
    
    # 3. Añadir el mensaje actual del usuario
    messages.append({
        "role": "user",
        "content": mensaje_usuario
    })
    
    # Debug: imprimir la estructura de mensajes
    print(f"DeepSeek Messages Structure: {json.dumps(messages, ensure_ascii=False)[:500]}...")
    print(f"Total messages: {len(messages)}")
    print(f"System prompt length: {len(sistema_prompt)}")

    respuesta = ""
    try:
        url = DEEPSEEK_API_URL
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": DEEPSEEK_MODEL,
            "messages": messages,
            "max_tokens": 300,
            "temperature": 0.7,
            "top_p": 0.9,
            "frequency_penalty": 0.3,
            "presence_penalty": 0.3,
            "stop": [f"\n{apodo_usuario}:", f"{apodo_usuario}:", f"\n{nombre_personaje}:", f"{nombre_personaje}:"]
        }

        print(f"Enviando solicitud a DeepSeek API...")
        response = requests.post(url, json=data, headers=headers, timeout=60)
        
        print(f"DeepSeek Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"DeepSeek Response JSON keys: {result.keys()}")
            
            if 'choices' in result and len(result['choices']) > 0:
                respuesta = result['choices'][0]['message']['content'].strip()
                
                # Limpiar la respuesta: remover cualquier mención del apodo o nombre si aparece
                respuesta = respuesta.split(f"{apodo_usuario}:")[0].split(f"{nombre_personaje}:")[0].strip()
                
                # Si la respuesta está vacía, proporcionar una por defecto
                if not respuesta:
                    respuesta = f"..."
                    
                print(f"Respuesta generada: {respuesta[:100]}...")
            else:
                error_msg = "No se pudo generar una respuesta."
                if 'error' in result:
                    error_msg = f"Error de API: {result['error'].get('message', 'Unknown error')}"
                print(f"Error en respuesta DeepSeek: {error_msg}")
                respuesta = "No se pudo generar una respuesta en este momento."
        
        # Manejar errores específicos de DeepSeek
        elif response.status_code == 401:
            print(f"Error de autenticación DeepSeek: {response.text}")
            respuesta = "Error de configuración del servidor. Por favor, contacta al administrador."
        
        elif response.status_code == 429:
            print(f"Rate limit excedido en DeepSeek: {response.text}")
            respuesta = "Estoy recibiendo demasiadas solicitudes. Por favor, espera un momento e intenta nuevamente."
        
        elif response.status_code == 402:
            print(f"Límite de crédito excedido en DeepSeek: {response.text}")
            respuesta = "Lo siento, el servicio está temporalmente no disponible. Vuelve a intentar más tarde."
        
        else:
            print(f"Error en API DeepSeek: {response.status_code} - {response.text}")
            respuesta = "Lo siento, ocurrió un error al procesar tu solicitud."

    except requests.exceptions.Timeout:
        print("Timeout en solicitud a DeepSeek")
        respuesta = "La solicitud tardó demasiado tiempo. Por favor, intenta nuevamente."
    
    except requests.exceptions.RequestException as e:
        print(f"Error de conexión con DeepSeek: {e}")
        respuesta = "Error de conexión. Por favor, verifica tu internet e intenta nuevamente."
    
    except Exception as e:
        print(f"Error inesperado con DeepSeek: {e}")
        respuesta = "Lo siento, ocurrió un error inesperado."

    return jsonify({'respuesta': respuesta})

@app.route('/healthz', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy', 
        'service': 'Chat API con DeepSeek',
        'version': '3.0',
        'model': DEEPSEEK_MODEL
    })

@app.route('/api/debug-prompt', methods=['POST'])
def debug_prompt():
    """Endpoint para debugging del prompt"""
    data = request.get_json()
    nombre_personaje = data.get('nombre_personaje', '')
    contexto = data.get('contexto', '')
    mensaje_usuario = data.get('mensaje_usuario', '')
    apodo_usuario = data.get('apodo_usuario', '')
    
    sistema_prompt = construir_prompt_para_deepseek(nombre_personaje, contexto, mensaje_usuario, apodo_usuario)
    historial = extraer_historial_del_contexto(contexto, apodo_usuario, nombre_personaje)
    
    return jsonify({
        'sistema_prompt': sistema_prompt,
        'sistema_length': len(sistema_prompt),
        'historial_messages': historial,
        'historial_count': len(historial),
        'tiene_personalidad': "PERSONALIDAD:" in contexto or "Personalidad:" in contexto
    })

@app.route('/api/models', methods=['GET'])
def list_models():
    """Listar modelos disponibles de DeepSeek"""
    try:
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        response = requests.get("https://api.deepseek.com/v1/models", headers=headers, timeout=10)
        
        if response.status_code == 200:
            models = response.json().get('data', [])
            model_list = [model['id'] for model in models]
            return jsonify({'models': model_list, 'current_model': DEEPSEEK_MODEL})
        else:
            return jsonify({'error': f"No se pudieron obtener los modelos: {response.status_code}"})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/usage', methods=['GET'])
def get_usage():
    """Obtener información de uso de la API"""
    return jsonify({
        'provider': 'DeepSeek',
        'model': DEEPSEEK_MODEL,
        'rate_limits': 'Consultar en https://platform.deepseek.com/usage',
        'free_tier': 'Hasta 10,000 tokens por día'
    })

if __name__ == '__main__':
    # Intentar obtener la API key de variable de entorno si está disponible
    env_api_key = os.environ.get('DEEPSEEK_API_KEY')
    if env_api_key:
        DEEPSEEK_API_KEY = env_api_key
        print("Usando API key de variable de entorno")
    
    # Verificar que la API key esté configurada
    if DEEPSEEK_API_KEY == "sk-tu_api_key_aqui" or not DEEPSEEK_API_KEY:
        print("ADVERTENCIA: La API key de DeepSeek no está configurada correctamente.")
        print("Por favor, configura la variable de entorno DEEPSEEK_API_KEY o actualiza el código.")
    
    print(f"Iniciando servidor DeepSeek API con modelo: {DEEPSEEK_MODEL}")
    print(f"Endpoint disponible en: /api/chat")
    print(f"Health check en: /healthz")
    print(f"Debug en: /api/debug-prompt")
    
    app.run(host='0.0.0.0', port=5000, debug=False)
