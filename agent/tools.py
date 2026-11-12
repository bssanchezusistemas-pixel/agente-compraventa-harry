# agent/tools.py — Herramientas del agente
# Generado por AgentKit

"""
Herramientas especificas de Compraventa Harry.

OJO: la informacion del negocio le llega al agente por el system prompt
(config/prompts.yaml), asi que para CONTESTAR preguntas de clientes no hace falta
ejecutar nada de aca. Este archivo es el lugar para las ACCIONES estructuradas:
registrar cotizaciones, calificar prospectos, consultar disponibilidad o tickets.
"""

import logging
from pathlib import Path

import yaml

logger = logging.getLogger("agentkit")

CARPETA_KNOWLEDGE = Path("knowledge")


def cargar_info_negocio() -> dict:
    """Carga la informacion del negocio desde config/business.yaml."""
    try:
        with open("config/business.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        logger.error("config/business.yaml no encontrado")
        return {}


def obtener_horario() -> dict:
    """Retorna el horario de atencion del negocio."""
    info = cargar_info_negocio()
    return {
        "horario_local": info.get("negocio", {}).get("horario", "Lunes a Sabado 8:00 AM - 7:00 PM"),
        "whatsapp": "24 horas (24/7)",
        "abierto_hoy": True,
    }


def buscar_en_knowledge(consulta: str) -> str:
    """
    Busca informacion en los archivos de /knowledge.
    Retorna los fragmentos que coinciden con la consulta.
    """
    if not CARPETA_KNOWLEDGE.is_dir():
        return "No hay archivos de conocimiento disponibles."

    resultados = []
    for ruta in sorted(CARPETA_KNOWLEDGE.iterdir()):
        if ruta.name.startswith(".") or not ruta.is_file():
            continue
        try:
            contenido = ruta.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if consulta.lower() in contenido.lower():
            resultados.append(f"[{ruta.name}]: {contenido[:500]}")

    if resultados:
        return "\n---\n".join(resultados)
    return "No encontre informacion especifica sobre eso en mis archivos."


def registrar_prospecto_moto(telefono: str, modelo: str, precio: str, estado_impuestos: str) -> dict:
    """Registra los datos de un cliente interesado en vender su moto."""
    logger.info(f"Prospecto moto registrado para {telefono}: {modelo} - Pretendido: {precio}")
    return {
        "status": "registrado",
        "telefono": telefono,
        "modelo": modelo,
        "precio_pretendido": precio,
        "impuestos": estado_impuestos,
    }


def registrar_prospecto_oro(telefono: str, tipo_pieza: str, peso_gr: str, precio: str) -> dict:
    """Registra los datos de un cliente interesado en vender oro."""
    logger.info(f"Prospecto oro registrado para {telefono}: {tipo_pieza} - {peso_gr}g - {precio}")
    return {
        "status": "registrado",
        "telefono": telefono,
        "pieza": tipo_pieza,
        "peso": peso_gr,
        "precio": precio,
    }
