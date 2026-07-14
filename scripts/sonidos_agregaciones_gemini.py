#!/usr/bin/env python3
"""
scripts/sonidos_agregaciones_gemini.py

Script de ejemplo: agrega múltiples detecciones de sonido, calcula métricas agregadas
y genera un reporte usando Google Gemini (o un modo simulado si no hay API key).

Uso:
  - Modo simulado (sin clave): export SIMULATE_GEMINI=true
  - Con Gemini real: export GEMINI_API_KEY="..."

Salida:
  - Guarda un reporte en /reports/aggregate_report_<timestamp>.md

Este script está diseñado para funcionar con los otros módulos del repo pero es
autocontenido para facilitar pruebas locales.
"""

import os
import json
import logging
from collections import Counter, defaultdict
from datetime import datetime
from typing import List, Dict, Any, Optional

# Intentar importar la librería de Gemini; si no está y SIMULATE_GEMINI=true, usamos simulación
try:
    import google.generativeai as genai
except Exception:
    genai = None

# Configuración básica
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.0-flash")
SIMULATE_GEMINI = os.getenv("SIMULATE_GEMINI", "false").lower() == "true"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
REPORT_DIR = os.getenv("REPORT_DIR", "/reports")
LOG_PATH = os.getenv("LOG_PATH", "/logs/sonidos_agg.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Ejemplo de muestras — en producción podrías cargar desde una fuente real
EXAMPLE_SAMPLES: List[Dict[str, Any]] = [
    {
        "sample_id": "GUNSHOT-001",
        "timestamp": "2026-07-14T14:35:42Z",
        "detection": {"event_type": "gunshot", "confidence": 0.94, "flags": ["HIGH_CONFIDENCE", "URGENT"], "keywords": ["disparo", "ballistic_impulse"]}
    },
    {
        "sample_id": "GUNSHOT-002",
        "timestamp": "2026-07-14T14:40:12Z",
        "detection": {"event_type": "gunshot", "confidence": 0.88, "flags": ["HIGH_CONFIDENCE"], "keywords": ["disparo"]}
    },
    {
        "sample_id": "NOISE-003",
        "timestamp": "2026-07-14T15:01:05Z",
        "detection": {"event_type": "unknown", "confidence": 0.40, "flags": [], "keywords": ["ambient"]}
    },
    {
        "sample_id": "GUNSHOT-004",
        "timestamp": "2026-07-14T15:12:22Z",
        "detection": {"event_type": "gunshot", "confidence": 0.96, "flags": ["URGENT"], "keywords": ["gunshot", "ballistic_impulse"]}
    }
]


def aggregate_samples(samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calcula métricas agregadas sobre una lista de muestras."""
    total = len(samples)
    counts_by_event = Counter()
    confidences = defaultdict(list)
    flags_counter = Counter()
    keywords_counter = Counter()

    for s in samples:
        det = s.get('detection', {})
        event = det.get('event_type', 'unknown')
        counts_by_event[event] += 1
        conf = det.get('confidence')
        if isinstance(conf, (int, float)):
            confidences[event].append(float(conf))
        for f in det.get('flags', []) or []:
            flags_counter[f] += 1
        for k in det.get('keywords', []) or []:
            keywords_counter[k.lower()] += 1

    avg_confidence = {e: (sum(vals) / len(vals)) if vals else None for e, vals in confidences.items()}

    agg = {
        'total_samples': total,
        'counts_by_event': dict(counts_by_event),
        'avg_confidence_by_event': avg_confidence,
        'flags': dict(flags_counter.most_common()),
        'top_keywords': keywords_counter.most_common(10)
    }
    return agg


def generate_prompt_for_aggregate(agg: Dict[str, Any], samples: List[Dict[str, Any]]) -> str:
    """Construye un prompt para Gemini describiendo las métricas agregadas y pidiendo un reporte."""
    prompt = [
        "Genera un reporte ejecutivo y técnico a partir de las siguientes métricas agregadas de detección de sonidos:",
        "Métricas agregadas:",
        json.dumps(agg, indent=2, ensure_ascii=False),
        "Muestras (resumen):",
        json.dumps([{'sample_id': s.get('sample_id'), 'event': s.get('detection', {}).get('event_type'), 'confidence': s.get('detection', {}).get('confidence')} for s in samples], indent=2, ensure_ascii=False),
        "Instrucciones:\n1) Escribe un resumen ejecutivo de 120-180 palabras.\n2) Incluye hallazgos técnicos clave.\n3) Indica recomendaciones operativas.\n4) Lista las top keywords y su significado operacional.\nFormato: Markdown con secciones claras."
    ]
    return "\n\n".join(prompt)


def call_gemini(prompt: str) -> str:
    """Llama a Gemini para generar texto o devuelve simulación si no está disponible."""
    if SIMULATE_GEMINI or not GEMINI_API_KEY or genai is None:
        logger.info("ℹ️ Gemini no disponible o SIMULATE_GEMINI=true — usando respuesta simulada")
        # Respuesta simulada breve
        simulated = (
            "# Reporte Agregado (Simulado)\n\n"
            "Resumen ejecutivo: Se detectaron 3 eventos compatibles con disparos y 1 evento no concluyente. \n"
            "La confianza promedio para eventos 'gunshot' es alta (~0.92).\n\n"
            "## Hallazgos técnicos\n- Patrón 'ballistic_impulse' presente en múltiples muestras.\n\n"
            "## Recomendaciones\n- Revisión de cámaras/zonas CVR en ventanas temporales indicadas.\n"
        )
        return simulated

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(MODEL_NAME)
        response = model.generate_content(prompt, generation_config={"temperature": 0.3, "max_output_tokens": 1024})
        return response.text
    except Exception as e:
        logger.error(f"❌ Error llamando a Gemini: {e}")
        # Fallback a simulación en caso de error
        return "# Reporte Agregado (fallback)\n\nError llamando a Gemini. Revisa logs."


def save_report(text: str, prefix: str = "aggregate_report") -> str:
    os.makedirs(REPORT_DIR, exist_ok=True)
    filename = f"{REPORT_DIR}/{prefix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(text)
    logger.info(f"✅ Reporte guardado en: {filename}")
    return filename


def main(samples: Optional[List[Dict[str, Any]]] = None):
    if samples is None:
        samples = EXAMPLE_SAMPLES

    logger.info("Iniciando agregación de muestras de sonido...")
    agg = aggregate_samples(samples)
    logger.info(f"Métricas agregadas: {json.dumps(agg, ensure_ascii=False)}")

    prompt = generate_prompt_for_aggregate(agg, samples)
    report = call_gemini(prompt)

    report_file = save_report(report)
    logger.info("Pipeline completado.")
    print(f"Reporte generado: {report_file}")


if __name__ == '__main__':
    main()
