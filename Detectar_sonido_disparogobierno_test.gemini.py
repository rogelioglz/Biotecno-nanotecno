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

Cambios añadidos por Rogelio:
    - Módulo lector/publicador de palabras (derogantes/keywords)
    - Ampliación de patrones de detección (incluye "disparo" y jefaturas)
    - Nuevas autoridades/jefaturas añadidas
    - Guardado de mensajes y palabras detectadas en /messages y /published_words
    - Integración SMTP opcional para envío de mensajes (configurable por entorno)
    - Cabeceras adicionales: Reply-To: zavalarogelio1984@gmail.com, X-Origin-Domain: Biotecno.local
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import smtplib
import ssl
from email.message import EmailMessage
import google.generativeai as genai

# ============================================================================
# CONFIGURACIÓN
# ============================================================================

# API Key Management
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "YOUR_GEMINI_API_KEY_HERE")
MODEL_NAME = "gemini-2.0-flash"
TEMPERATURE = 0.7
MAX_TOKENS = 2048

# SMTP (env-configurable)
ENABLE_SMTP = os.getenv("ENABLE_SMTP", "false").lower() == "true"
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER or "no-reply@biotecno.local")
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() == "true"
ORIGIN_DOMAIN = os.getenv("ORIGIN_DOMAIN", "Biotecno.local")
REPLY_TO_EMAIL = os.getenv("REPLY_TO_EMAIL", "zavalarogelio1984@gmail.com")

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
    },
    # Nuevas jefaturas solicitadas
    "belinda-mk": {
        "name": "Belinda MK (Jefatura Belinda)",
        "email": "belinda-mk@biotecno.local",
        "ai_task": "message_formatting",
        "format": "formal"
    },
    "ultra-conclaves-jose": {
        "name": "Ultra Conclaves - Jose (Jefatura)",
        "email": "ultraconclaves-jose@biotecno.local",
        "ai_task": "report_generation",
        "format": "executive_summary"
    },
    "contrato_isaquio": {
        "name": "Contrato de Isaquio",
        "email": "isaquio-contrato@biotecno.local",
        "ai_task": "legal_validation",
        "format": "technical"
    },
    "belithoricos": {
        "name": "Belithoricos (Jefatura Técnica)",
        "email": "belithoricos@biotecno.local",
        "ai_task": "message_formatting",
        "format": "technical"
    }
}

# Patrones y keywords ampliadas (Búsqueda de 'disparo' y derivados)
DETECTION_KEYWORDS = [
    "disparo",
    "gunshot",
    "ballistic_impulse",
    "belinda-mk",
    "ultra-conclaves-jose",
    "contrato de isaquio",
    "contrato_isaquio",
    "belithoricos",
    "belithoric"
]

# Lista de palabras "derogantes" o sensibles a detectar en transcripciones/etiquetas
DEROGANTES = [
    # Ejemplo: palabras a monitorizar/filtrar; el usuario puede actualizar esta lista
    "insulto1",
    "insulto2",
    "palabra-prohibida",
]

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
        "timestamp_logged": "2026-07-14T14:36:15Z",
        # Campo opcional 'order' para activar acciones (por ejemplo: "chimera")
        "order": "chimera"
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
6. Incluye listado de keywords/patrones detectados

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
# FUNCIONES DE PRUEBA y NUEVAS FUNCIONES (lector/publicador)
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


def generate_detection_report(detection_data: Dict[str, Any], matched_keywords: Optional[List[str]] = None) -> Optional[str]:
    """
    Genera reporte de detección usando Gemini AI
    Tarea: report_generation
    """
    try:
        logger.info(f"📝 Generando reporte para muestra: {detection_data.get('sample_id')}")
        
        model = genai.GenerativeModel(MODEL_NAME)
        data_with_keywords = dict(detection_data)
        if matched_keywords:
            data_with_keywords["matched_keywords"] = matched_keywords
        
        prompt = PROMPT_TEMPLATES["report_generation"].format(
            detection_data=json.dumps(data_with_keywords, indent=2, ensure_ascii=False)
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
{