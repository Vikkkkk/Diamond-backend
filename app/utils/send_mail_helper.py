import smtplib
import os
import re
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.image import MIMEImage
from typing import List, Optional, Dict
import html as _html
from functools import lru_cache
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()




def build_missing_damaged_items_table_html(
    notify_items: List[tuple],
    *,
    intro_text: str = "The following PO items were updated:",
) -> str:
    """
    Builds the HTML table body used by order missing/damaged notifications.

    `notify_items` should be a list of tuples like: (status_label, order_item)
    where order_item has attributes like opening_number, location_1, from_to.
    """
    rows_html = ""
    for status_label, order_item in notify_items:
        opening_number = _html.escape(str(getattr(order_item, "opening_number", "") or ""))
        status_cell = _html.escape(str(status_label or ""))
        project_name = _html.escape(str(getattr(order_item, "project_name", "") or ""))
        project_id = _html.escape(str(getattr(order_item, "project_id", "") or ""))
        frontendUrl = _html.escape(f'{os.getenv("FRONTEND_URL", "http://localhost:3000")}/app/project_management/{project_id}/order_management')

        rows_html += (
            "<tr>"
            f"<td style='padding:8px; border-bottom:1px solid #e5e7eb;'>{status_cell}</td>"
            f"<td style='padding:8px; border-bottom:1px solid #e5e7eb;'>{opening_number}</td>"
            f"<td style='padding:8px; border-bottom:1px solid #e5e7eb;'>{project_name}</td>"
            f"<td style='padding:8px; border-bottom:1px solid #e5e7eb;'><a href='{frontendUrl}'>Please find in the attachment</a></td>"
            "</tr>"
        )

    intro = _html.escape(intro_text)
    return (
        f"<p>{intro}</p>"
        "<table style='width:100%; border-collapse:collapse;'>"
        "<thead>"
        "<tr>"
        "<th style='text-align:left; padding:8px; border-bottom:2px solid #e5e7eb;'>Status</th>"
        "<th style='text-align:left; padding:8px; border-bottom:2px solid #e5e7eb;'>Opening #</th>"
        "<th style='text-align:left; padding:8px; border-bottom:2px solid #e5e7eb;'>Project Name</th>"
        "<th style='text-align:left; padding:8px; border-bottom:2px solid #e5e7eb;'>Images</th>"
        "</tr>"
        "</thead>"
        "<tbody>"
        f"{rows_html}"
        "</tbody>"
        "</table>"
    )

class SMTPMailService:
    @staticmethod
    @lru_cache(maxsize=8)
    def _load_template_text(template_path: str) -> str:
        return Path(template_path).read_text(encoding="utf-8")

    @staticmethod
    def _render_template_string(template_text: str, data: Dict[str, str]) -> str:
        """
        Manually renders a template by replacing placeholders like {{ key }}.

        Notes:
        - `data` values are inserted as-is. Escape/sanitize before passing if needed.
        - Supports whitespace inside braces: {{key}} / {{ key }} / {{   key   }}.
        """
        rendered = template_text
        for key, value in (data or {}).items():
            pattern = r"\{\{\s*" + re.escape(str(key)) + r"\s*\}\}"
            rendered = re.sub(pattern, str(value), rendered)
        return rendered

    def _get_template_path(self) -> Path:
        templates_dir = Path(__file__).resolve().parents[1] / "templates"
        return templates_dir / self.template_name

    def __init__(
        self,
        *,
        smtp_server: Optional[str] = None,
        smtp_port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        secure: Optional[str] = None,
        default_from: Optional[str] = None,
        template_name: str = "email_html.html",
    ):
        self.smtp_server = smtp_server or os.getenv("SMTP_HOST")
        self.smtp_port = smtp_port or (int(os.getenv("SMTP_PORT")) if os.getenv("SMTP_PORT") else 587)
        self.username = username or os.getenv("SMTP_USERNAME") or os.getenv("SMTP_MAIL_ADDRESS")
        self.password = password or os.getenv("SMTP_PASSWORD")
        self.secure = (secure or os.getenv("SMTP_SECURE") or "starttls").lower()
        self.default_from = default_from or os.getenv("SMTP_MAIL_ADDRESS")
        self.template_name = template_name

    def render_html(self, *, subject: str, data: Dict[str, str]) -> str:
        base_data = dict(data or {})
        base_data.setdefault("title", _html.escape(subject or ""))
        template_path = str(self._get_template_path())
        template_text = self._load_template_text(template_path)
        return self._render_template_string(template_text, base_data)

    def send_email(
        self,
        *,
        email_addresses: List[str],
        subject: str,
        mail_from: Optional[str] = None,
        html_body: Optional[str] = None,
        text_body: Optional[str] = None,
        template_data: Optional[Dict[str, str]] = None,
        attachment_file_paths: Optional[List[str]] = None,
        inline_images: Optional[Dict[str, str]] = None,
        image_src_to_cid: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Sends an email using SMTP with multipart/alternative (text + html),
        optional attachments, and optional inline images via CID.
        """
        try:
            if not self.smtp_server or not self.smtp_port or not self.username or not self.password:
                raise ValueError("SMTP server is not configured (SMTP_HOST).")
            if not email_addresses:
                raise ValueError("No recipient email addresses provided.")

            message = MIMEMultipart("mixed")
            message["Subject"] = subject
            message["From"] = mail_from or self.default_from or self.username
            message["To"] = ", ".join(email_addresses)

            alt = MIMEMultipart("alternative")
            message.attach(alt)

            if html_body is None:
                template_data = template_data or {}
                html_body = self.render_html(subject=subject, data=template_data)

            if image_src_to_cid:
                for filename, cid in image_src_to_cid.items():
                    html_body = html_body.replace(f'src="{filename}"', f'src="cid:{cid}"')

            if text_body is None and html_body is not None:
                # Basic fallback so recipients who can't render HTML still see something.
                text_body = re.sub(r"<[^>]+>", "", html_body)

            if text_body:
                alt.attach(MIMEText(text_body, "plain", "utf-8"))
            alt.attach(MIMEText(html_body, "html", "utf-8"))

            if inline_images:
                for cid, path in inline_images.items():
                    if not os.path.exists(path):
                        continue
                    with open(path, "rb") as f:
                        img_data = f.read()
                    img = MIMEImage(img_data)
                    img.add_header("Content-ID", f"<{cid}>")
                    img.add_header("Content-Disposition", "inline", filename=os.path.basename(path))
                    message.attach(img)

            if attachment_file_paths:
                for file_path in attachment_file_paths:
                    with open(file_path, "rb") as f:
                        file_data = f.read()
                    part = MIMEApplication(file_data)
                    filename = os.path.basename(file_path)
                    part.add_header("Content-Disposition", "attachment", filename=filename)
                    message.attach(part)

            if self.secure in ("ssl", "smtps"):
                server = smtplib.SMTP_SSL(
                    self.smtp_server,
                    self.smtp_port,
                    context=ssl.create_default_context(),
                )
            else:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                if self.secure in ("starttls", "tls", "true", "1", "yes"):
                    server.starttls(context=ssl.create_default_context())

            with server:
                if self.username and self.password:
                    server.login(self.username, self.password)
                server.sendmail(message["From"], email_addresses, message.as_string())
            print(f"Email sent successfully to {email_addresses}: {subject}")
            return True
        except Exception as e:
            print(f"[SMTPMailService.send_email error]: {e}")
            print(f"Email sending failed to {email_addresses}: {subject}: {e}")
            return False


if __name__ == "__main__":
    subject = "SMTP Test Email"

    to_emails = ["saikatgoswami004@gmail.com"]

    if not to_emails:
        # Default: send to the configured sender address (useful for quick testing)
        smtp_mail_address = os.getenv("SMTP_MAIL_ADDRESS")
        if smtp_mail_address:
            to_emails = [smtp_mail_address]
        else:
            raise SystemExit("No recipients. Set SMTP_TEST_TO / TEST_EMAIL_TO or SMTP_MAIL_ADDRESS.")

    dummy_items = [
        (
            "missing",
            type(
                "Obj",
                (),
                {"opening_number": "OP-101", "location_1": "Level 1", "from_to": "A - B"},
            )(),
        ),
        (
            "damaged",
            type(
                "Obj",
                (),
                {"opening_number": "OP-205", "location_1": "Level 2", "from_to": "C - D"},
            )(),
        ),
    ]
    body_html = build_missing_damaged_items_table_html(dummy_items)

    service = SMTPMailService()
    ok = service.send_email(
        email_addresses=to_emails,
        subject=subject,
        template_data={
            "heading": subject,
            "preview_text": "SMTP test email",
            "body_html": body_html,
            "footer_text": "This is a test email from Diamond backend.",
        },
        attachment_file_paths=[
            str(Path(__file__).resolve().parents[1] / "quotation" / "template" / "logo.png")
        ],
    )

    if not ok:
        raise SystemExit(1)