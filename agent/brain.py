# agent/brain.py — Cerebro del agente: conexion con IA (Gemini / Claude)
# Generado por AgentKit

"""
Logica de IA del agente. Lee el system prompt de config/prompts.yaml y genera las
respuestas con la API configurada (Google Gemini o Anthropic Claude).
"""

import logging
import os

import yaml
from dotenv import load_dotenv

load_dotenv(override=True)
logger = logging.getLogger("agentkit")

AI_PROVIDER = (os.getenv("AI_PROVIDER") or "").strip().lower()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("GOOGLE_API_KEY", "").strip()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "").strip()

# Evitar advertencia de google-genai en consola normalizando el entorno
if GEMINI_API_KEY:
    os.environ["GOOGLE_API_KEY"] = GEMINI_API_KEY
    os.environ.pop("GEMINI_API_KEY", None)

# Inicializacion de clientes segun las credenciales disponibles
gemini_client = None
anthropic_client = None

if GEMINI_API_KEY or AI_PROVIDER == "gemini":
    try:
        from google import genai

        gemini_client = genai.Client(
            api_key=GEMINI_API_KEY,
            http_options={"api_version": "v1beta"},
        )
        GEMINI_MODEL = os.getenv("GEMINI_MODEL") or "gemini-3.5-flash"
        if GEMINI_MODEL == "gemini-2.5-flash":
            GEMINI_MODEL = "gemini-3.5-flash"
        logger.info(f"Cerebro IA configurado con Google Gemini ({GEMINI_MODEL})")
    except Exception as e:
        logger.error(f"Error inicializando Google Gemini: {e}")

if (ANTHROPIC_API_KEY or AI_PROVIDER == "anthropic") and not gemini_client:
    try:
        from anthropic import AsyncAnthropic

        anthropic_client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)
        ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL") or "claude-sonnet-5-5"
        logger.info(f"Cerebro IA configurado con Anthropic Claude ({ANTHROPIC_MODEL})")
    except Exception as e:
        logger.error(f"Error inicializando Anthropic: {e}")


def cargar_config_prompts() -> dict:
    """Lee toda la configuracion desde config/prompts.yaml."""
    try:
        with open("config/prompts.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        logger.error("config/prompts.yaml no encontrado")
        return {}


def cargar_system_prompt() -> str:
    """El system prompt: quien es el agente y que sabe del negocio."""
    return cargar_config_prompts().get(
        "system_prompt", "Eres un asistente util. Responde siempre en espanol."
    )


def obtener_mensaje_error() -> str:
    """Que decirle al cliente cuando algo falla de nuestro lado."""
    return cargar_config_prompts().get(
        "error_message",
        "Lo siento, estoy teniendo problemas tecnicos. Por favor intenta de nuevo en unos minutos.",
    )


def obtener_mensaje_fallback() -> str:
    """Que decirle al cliente cuando no se entendio el mensaje."""
    return cargar_config_prompts().get(
        "fallback_message", "Disculpa, no entendi tu mensaje. Podrias reformularlo?"
    )


async def generar_respuesta(mensaje: str, historial: list[dict]) -> tuple[str, bool]:
    """
    Genera una respuesta con el modelo de IA.

    Args:
        mensaje: el mensaje nuevo del cliente
        historial: los mensajes anteriores, [{"role": "user"|"assistant"|"model", "content": "..."}]

    Returns:
        (texto, es_respuesta_real)
    """
    if not mensaje or not mensaje.strip():
        return obtener_mensaje_fallback(), False

    system_prompt = cargar_system_prompt()

    # ── Modo 1: Google Gemini ───────────────────────────────────
    if gemini_client is not None:
        try:
            from google.genai import types

            contents = []
            for m in historial:
                rol = "user" if m.get("role") == "user" else "model"
                contents.append(
                    types.Content(
                        role=rol,
                        parts=[types.Part.from_text(text=m.get("content", ""))],
                    )
                )

            contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=mensaje)],
                )
            )

            config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.7,
            )

            model_name = os.getenv("GEMINI_MODEL") or "gemini-3.5-flash"
            if model_name == "gemini-2.5-flash":
                model_name = "gemini-3.5-flash"
            models_to_try = [model_name]
            for m in ["gemini-3.5-flash-lite", "gemini-2.5-flash-lite", "gemini-flash-lite-latest"]:
                if m not in models_to_try:
                    models_to_try.append(m)

            res = None
            last_err = None
            for m in models_to_try:
                try:
                    res = await gemini_client.aio.models.generate_content(
                        model=m,
                        contents=contents,
                        config=config,
                    )
                    if res and res.text:
                        break
                except Exception as ex:
                    last_err = ex
                    logger.warning(f"Error con modelo {m}: {ex}. Probando siguiente modelo...")
                    continue

            if not res or not res.text:
                if last_err:
                    logger.error(f"Todos los modelos de Gemini fallaron: {last_err}")
                return obtener_mensaje_fallback(), False

            texto = res.text.strip()
            return texto, True

        except Exception as e:
            logger.error(f"Error llamando a Gemini: {e}")
            return obtener_mensaje_error(), False

    # ── Modo 2: Anthropic Claude ────────────────────────────────
    if anthropic_client is not None:
        try:
            mensajes = [{"role": m["role"], "content": m["content"]} for m in historial]
            mensajes.append({"role": "user", "content": mensaje})

            modelo = os.getenv("ANTHROPIC_MODEL") or "claude-sonnet-5-5"
            max_tokens = int(os.getenv("ANTHROPIC_MAX_TOKENS") or "4096")

            respuesta = await anthropic_client.messages.create(
                model=modelo,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=mensajes,
            )

            partes = [b.text for b in respuesta.content if b.type == "text"]
            texto = "\n".join(p for p in partes if p).strip()

            if not texto:
                return obtener_mensaje_fallback(), False

            return texto, True

        except Exception as e:
            logger.error(f"Error llamando a Claude: {e}")
            return obtener_mensaje_error(), False

    logger.error("No hay ningun proveedor de IA configurado (falta GEMINI_API_KEY o ANTHROPIC_API_KEY)")
    return obtener_mensaje_error(), False
