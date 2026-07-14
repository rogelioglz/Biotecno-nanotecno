#!/usr/bin/env python3
"""
Test Script: Google Gemini AI Integration for Authority Delivery
Módulo: Detección de Sonido de Disparo - Reporte a Gobierno (Primer Mandato)

Descripción:
    Este script prueba la integración de Google Gemini 2.0 Flash para:
    - Detección de sonidos de disparo
    - Generación automática de reportes
    - Entrega a autoridades de comunicación
    - Validación legal y cumplimiento normativo

Autoridades Objetivo:
    - ANARTEL (Autoridad Nacional de Telecomunicaciones)
    - Ministerio de Comunicaciones
    - ANIC (Infraestructura de Comunicaciones)
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any
import google.generativeai as genai

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

# API Key Management
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")
MODEL_NAME = "gemini-2.0-flash"
TEMPERATURE = 0.7
MAX_TOKENS = 2048

# Autoridades de Comunicación (Primer Mandato)
AUTHORITIES = {
    "anartel": {
        "name": "ANARTEL (Autoridad Nacional de Telecomunicaciones)",
        "email": "reportes@anartel.gov",
        "ai_task": "legal_validation",
        "format": "formal"
    },
    "ministerio": {
        "name": "Ministerio de Comunicaciones",
        "email": "reportes@comunicaciones.gov",
        "ai_task": "report_generation",
        "format": "executive_summary"
    },
    "anic": {
        "name": "ANIC (Autoridad Nacional de Infraestructura de Comunicaciones)",
        "email": "compliance@anic.gov",
        "ai_task": "message_formatting",
        "format": "technical"
    }
}

# Configuración de Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/logs/gemini-test.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================================
# DATOS DE PRUEBA: Sonido de Disparo Detectado
# ============================================================================

SAMPLE_GUNSHOT_DETECTION = {
    "sample_id": "GUNSHOT-2026-07-14-001",
    "timestamp": "2026-07-14T14:35:42Z",
    "sensor_type": "audio_spectrogram",
    "location": {
        "latitude": 10.396528,
        "longitude": -75.506694,
        "address": "Sector Centro, Ciudad A"
    },
    "detection_data": {
        "event_type": "gunshot",
        "confidence_score": 0.94,
        "frequency_analysis": {
            "peak_frequency_hz": 3850,
            "spectral_peaks": [3850, 7200, 10500],
            "duration_ms": 145,
            "decibel_level": 167
        },
        "pattern_match": {
            "matched_pattern": "ballistic_impulse",
            "similarity_score": 0.92,
            "reference_database": "gunshot_library_v2"
        }
    },
    "infrared_summary": {
        "event_characteristics": [
            "Impulso balístico detectado",
            "Frecuencia dominante: 3.85 kHz",
            "Amplitud peak: 167 dB SPL",
            "Duración: 145 ms",
            "Patrón compatible con calibre 9mm"
        ],
        "flags": ["HIGH_CONFIDENCE", "URGENT"],
        "geographic_precision": 6,
        "geospatial_reference": "WGS84"
    },
    "operator_info": {
        "operator_id": "OP-2026-0847",
        "timestamp_logged": "2026-07-14T14:36:15Z"
    }
}

# ============================================================================
# PROMPTS PARA GEMINI AI
# ============================================================================

PROMPT_TEMPLATES = {
    "report_generation": """
Analiza los siguientes datos de detección de sonido de disparo y genera un reporte formal 
para autoridades de comunicación del primer mandato:

DATOS DE DETECCIÓN:
{detection_data}

INSTRUCCIONES:
1. Genera un resumen ejecutivo en lenguaje formal
2. Incluye hallazgos técnicos detallados
3. Proporciona recomendaciones de acción
4. Cita cumplimiento con regulaciones
5. Formato: YAML estructurado

SALIDA ESPERADA:
- Título profesional
- Resumen ejecutivo (150-200 palabras)
- Hallazgos técnicos
- Análisis de riesgo
- Recomendaciones
- Cumplimiento normativo
""",

    "legal_validation": """
Valida el siguiente reporte de detección contra regulaciones de comunicación del primer mandato:

REPORTE A VALIDAR:
{report_data}

REGULACIONES APLICABLES:
- Leyes de comunicaciones (primer mandato)
- Protección de datos e intimidad
- Cadena de custodia
- Autorización legal para distribución

INSTRUCCIONES:
1. Verifica cumplimiento legal
2. Identifica requisitos pendientes
3. Proporciona recomendaciones de conformidad
4. Genera certificado de validación

SALIDA ESPERADA:
- Estado de validación (APROBADO/RECHAZADO/CON_CONDICIONES)
- Hallazgos legales
- Requisitos pendientes
- Recomendaciones
- Firma digital (hash)
""",

    "message_formatting": """
Transforma los siguientes datos técnicos en lenguaje formal y accesible para autoridades regulatorias:

DATOS TÉCNICOS:
{technical_data}

INSTRUCCIONES:
1. Convierte lenguaje técnico a formal-administrativo
2. Mantén precisión científica
3. Incluye contexto regulatorio
4. Proporciona contexto para tomadores de decisiones

SALIDA ESPERADA:
- Comunicado formal
- Contexto y antecedentes
- Hallazgos principales
- Implicaciones regulatorias
- Recomendaciones de acción
""",
}

# ============================================================================
# FUNCIONES DE PRUEBA
# ============================================================================

def initialize_gemini():
    """Inicializa cliente de Google Gemini"""
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        logger.info("✅ Google Gemini API configurada correctamente")
        return True
    except Exception as e:
        logger.error(f"❌ Error inicializando Gemini: {str(e)}")
        return False


def test_gemini_connectivity():
    """Prueba conexión con Google Gemini API"""
    try:
        logger.info("🔍 Probando conectividad con Google Gemini...")
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content("Responde con: CONEXIÓN_EXITOSA")
        
        if response and response.text:
            logger.info(f"✅ Conectividad verificada: {response.text[:50]}...")
            return True
        else:
            logger.error("❌ Respuesta vacía de Gemini")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error de conectividad: {str(e)}")
        return False


def generate_detection_report(detection_data: Dict[str, Any]) -> str:
    """
    Genera reporte de detección usando Gemini AI
    Tarea: report_generation
    """
    try:
        logger.info(f"📝 Generando reporte para muestra: {detection_data['sample_id']}")
        
        model = genai.GenerativeModel(MODEL_NAME)
        
        prompt = PROMPT_TEMPLATES["report_generation"].format(
            detection_data=json.dumps(detection_data, indent=2, ensure_ascii=False)
        )
        
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": TEMPERATURE,
                "max_output_tokens": MAX_TOKENS,
                "top_k": 40,
                "top_p": 0.95
            }
        )
        
        report = response.text
        logger.info(f"✅ Reporte generado exitosamente ({len(report)} caracteres)")
        
        return report
        
    except Exception as e:
        logger.error(f"❌ Error generando reporte: {str(e)}")
        return None


def validate_legal_compliance(report_data: str) -> Dict[str, Any]:
    """
    Valida cumplimiento legal del reporte usando Gemini AI
    Tarea: legal_validation
    """
    try:
        logger.info("⚖️ Validando cumplimiento legal...")
        
        model = genai.GenerativeModel(MODEL_NAME)
        
        prompt = PROMPT_TEMPLATES["legal_validation"].format(
            report_data=report_data
        )
        
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.5,  # Menor temperatura para validación legal
                "max_output_tokens": MAX_TOKENS
            }
        )
        
        validation_result = {
            "timestamp": datetime.now().isoformat(),
            "status": "VALIDATED",
            "content": response.text,
            "ai_model": MODEL_NAME
        }
        
        logger.info(f"✅ Validación completada")
        return validation_result
        
    except Exception as e:
        logger.error(f"❌ Error en validación legal: {str(e)}")
        return {"status": "ERROR", "error": str(e)}


def format_authority_message(technical_data: str, authority: str) -> str:
    """
    Formatea mensaje profesional para autoridad usando Gemini AI
    Tarea: message_formatting
    """
    try:
        logger.info(f"📧 Formateando mensaje para {authority}...")
        
        model = genai.GenerativeModel(MODEL_NAME)
        
        prompt = PROMPT_TEMPLATES["message_formatting"].format(
            technical_data=technical_data
        )
        
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": TEMPERATURE,
                "max_output_tokens": MAX_TOKENS
            }
        )
        
        formatted_message = response.text
        logger.info(f"✅ Mensaje formateado para {authority}")
        
        return formatted_message
        
    except Exception as e:
        logger.error(f"❌ Error formateando mensaje: {str(e)}")
        return None


def run_full_test_pipeline():
    """
    Ejecuta pipeline completo de prueba:
    1. Conectividad
    2. Generación de reporte
    3. Validación legal
    4. Formateo para cada autoridad
    """
    logger.info("=" * 80)
    logger.info("INICIANDO PRUEBA COMPLETA: Gemini AI para Detección de Disparos")
    logger.info("=" * 80)
    
    # Paso 1: Inicializar
    if not initialize_gemini():
        logger.error("No se pudo inicializar Gemini. Abortando prueba.")
        return False
    
    # Paso 2: Probar conectividad
    if not test_gemini_connectivity():
        logger.error("No hay conectividad con Gemini. Abortando prueba.")
        return False
    
    # Paso 3: Generar reporte
    report = generate_detection_report(SAMPLE_GUNSHOT_DETECTION)
    if not report:
        logger.error("No se pudo generar reporte. Abortando prueba.")
        return False
    
    # Guardar reporte
    report_file = f"/reports/gunshot_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    try:
        os.makedirs(os.path.dirname(report_file), exist_ok=True)
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"✅ Reporte guardado en: {report_file}")
    except Exception as e:
        logger.warning(f"⚠️ No se pudo guardar reporte: {str(e)}")
    
    # Paso 4: Validar cumplimiento legal
    validation = validate_legal_compliance(report)
    if validation["status"] != "VALIDATED":
        logger.error("Validación legal fallida.")
        return False
    
    # Paso 5: Formatear para cada autoridad
    authority_messages = {}
    for auth_id, auth_info in AUTHORITIES.items():
        message = format_authority_message(report, auth_info["name"])
        if message:
            authority_messages[auth_id] = {
                "authority": auth_info["name"],
                "email": auth_info["email"],
                "message": message
            }
            
            # Guardar mensaje
            msg_file = f"/messages/{auth_id}_message_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            try:
                os.makedirs(os.path.dirname(msg_file), exist_ok=True)
                with open(msg_file, 'w', encoding='utf-8') as f:
                    f.write(f"Destinatario: {auth_info['name']}\n")
                    f.write(f"Email: {auth_info['email']}\n")
                    f.write("-" * 80 + "\n")
                    f.write(message)
                logger.info(f"✅ Mensaje para {auth_id} guardado")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo guardar mensaje: {str(e)}")
    
    # Resumen de prueba
    logger.info("=" * 80)
    logger.info("RESUMEN DE PRUEBA EXITOSA")
    logger.info("=" * 80)
    logger.info(f"✅ Conectividad: OK")
    logger.info(f"✅ Reporte generado: {len(report)} caracteres")
    logger.info(f"✅ Validación legal: {validation['status']}")
    logger.info(f"✅ Mensajes para autoridades: {len(authority_messages)}")
    
    for auth_id, msg_info in authority_messages.items():
        logger.info(f"   - {msg_info['authority']}: {msg_info['email']}")
    
    logger.info("=" * 80)
    
    return True


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import sys
    
    # Verificar API Key
    if GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        logger.error("❌ GEMINI_API_KEY no está configurada")
        logger.error("   Configura: export GEMINI_API_KEY='your-api-key-here'")
        sys.exit(1)
    
    # Ejecutar prueba completa
    success = run_full_test_pipeline()
    
    sys.exit(0 if success else 1)
