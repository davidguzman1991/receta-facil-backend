import logging
import smtplib
from email.message import EmailMessage
from email.utils import formataddr

from app.core.config import settings

logger = logging.getLogger(__name__)


def _send_smtp_text_sync(to_email: str, subject: str, body: str) -> None:
    """Envía un correo solo texto vía SMTP (bloqueante)."""
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr((settings.PROJECT_NAME, settings.SMTP_FROM))
    msg["To"] = to_email
    msg.set_content(body)
    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)


def _send_smtp_sync(to_email: str, subject: str, body: str, pdf_bytes: bytes, filename: str) -> None:
    """Envía el correo vía SMTP (bloqueante)."""
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr((settings.PROJECT_NAME, settings.SMTP_FROM))
    msg["To"] = to_email
    msg.set_content(body)

    msg.add_attachment(
        pdf_bytes,
        maintype="application",
        subtype="pdf",
        filename=filename,
    )

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)


async def send_prescription_email(
    to_email: str,
    patient_name: str,
    pdf_bytes: bytes,
    filename: str,
) -> bool:
    """
    Envía por correo la receta en PDF al paciente.
    Usa las variables SMTP de configuración. Si no están configuradas, no envía y retorna False.
    Retorna True si el envío fue exitoso, False en caso contrario (sin levantar excepciones al caller).
    """
    if not all([settings.SMTP_HOST, settings.SMTP_USER, settings.SMTP_PASSWORD, settings.SMTP_FROM]):
        logger.warning("SMTP not configured: prescription email not sent")
        return False

    subject = "Su receta médica"
    body = f"""Estimado/a {patient_name},

Adjuntamos su receta médica generada por su médico.

Por favor siga las indicaciones descritas.

Receta Fácil
"""

    try:
        import asyncio
        await asyncio.to_thread(
            _send_smtp_sync,
            to_email,
            subject,
            body,
            pdf_bytes,
            filename,
        )
        return True
    except Exception as e:
        logger.exception("Failed to send prescription email: %s", e)
        return False


async def send_activation_email(to_email: str, patient_name: str, activation_link: str) -> bool:
    """
    Envía el correo de invitación/activación al paciente con el enlace para crear su contraseña.
    Si SMTP no está configurado, retorna False sin levantar excepciones.
    """
    if not all([settings.SMTP_HOST, settings.SMTP_USER, settings.SMTP_PASSWORD, settings.SMTP_FROM]):
        logger.warning("SMTP not configured: activation email not sent")
        return False

    subject = "Active su cuenta - Receta Fácil"
    body = f"""Estimado/a {patient_name},

Su médico le ha invitado a acceder al portal de Receta Fácil para ver sus datos clínicos.

Para activar su cuenta y crear su contraseña, utilice el siguiente enlace (válido 48 horas):

{activation_link}

Si no ha solicitado esta invitación, puede ignorar este correo.

Receta Fácil
"""

    try:
        import asyncio
        await asyncio.to_thread(_send_smtp_text_sync, to_email, subject, body)
        return True
    except Exception as e:
        logger.exception("Failed to send activation email: %s", e)
        return False
