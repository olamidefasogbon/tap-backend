# services/whatsapp.py
import httpx
from core.config import settings
import logging

logger = logging.getLogger(__name__)

async def send_payment_link(phone_number: str, product_name: str, amount: float, link: str):
    """
    Sends the tap. payment link via WhatsApp. 
    In development, it just logs to the console to prevent crashes.
    """
    if settings.WHATSAPP_TOKEN == "your_meta_token_here" or not settings.WHATSAPP_TOKEN:
        logger.warning(f"🔧 DEV MODE: Skipping actual WhatsApp message to {phone_number}.")
        logger.info(f"📲 MESSAGE CONTENT: 'Pay NGN {amount:,.2f} for {product_name} here: {link}'")
        return {"status": "mocked", "message": "Logged to console instead of WhatsApp"}

    url = f"https://graph.facebook.com/v19.0/{settings.WHATSAPP_PHONE_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "template",
        "template": {
            "name": "payment_link_ready",
            "language": {"code": "en"},
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": product_name},
                        {"type": "text", "text": f"NGN {amount:,.2f}"},
                        {"type": "text", "text": link}
                    ]
                }
            ]
        }
    }
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"WhatsApp API Error: {e.response.text}")
            return {"status": "failed", "error": str(e)}


async def send_escrow_update(phone_number: str, message: str):
    """
    Sends an escrow status update (e.g., shipped, delivered) via WhatsApp.
    """
    if settings.WHATSAPP_TOKEN == "your_meta_token_here" or not settings.WHATSAPP_TOKEN:
        logger.warning(f"🔧 DEV MODE: Skipping actual WhatsApp update to {phone_number}.")
        logger.info(f"📲 UPDATE CONTENT: '{message}'")
        return {"status": "mocked", "message": "Logged to console instead of WhatsApp"}

    url = f"https://graph.facebook.com/v19.0/{settings.WHATSAPP_PHONE_ID}/messages"
    
    headers = {
        "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "text",
        "text": {"body": message}
    }
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"WhatsApp API Error: {e.response.text}")
            return {"status": "failed", "error": str(e)}