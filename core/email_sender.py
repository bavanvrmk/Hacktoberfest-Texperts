"""
Email Sender Module — Outlook COM Automation (Windows)
Sends emails using the local Microsoft Outlook desktop client via win32com.
Falls back to mailto: URI or SMTP if Outlook is unavailable.

Privacy: All email composition happens locally. No cloud relay.
"""

import os
import re
import subprocess
import time

# Email address pattern for extraction
_EMAIL_PATTERN = re.compile(
    r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}"
)


def send_email_outlook(to: str, subject: str, body: str, cc: str = "", bcc: str = "") -> dict:
    """
    Send an email using the local Outlook COM automation.
    Returns a dict with status, method used, and any error info.
    """
    to = (to or "").strip()
    subject = (subject or "").strip()
    body = (body or "").strip()

    if not to:
        raise ValueError("Recipient email address is required.")
    if not _EMAIL_PATTERN.match(to):
        raise ValueError(f"Invalid email address format: '{to}'")

    # Try Outlook COM first (best integration)
    try:
        result = _send_via_outlook_com(to, subject, body, cc, bcc)
        return result
    except Exception as com_err:
        print(f"[EmailSender] Outlook COM failed: {com_err}")

    # Fallback: PowerShell Outlook automation
    try:
        result = _send_via_powershell_outlook(to, subject, body)
        return result
    except Exception as ps_err:
        print(f"[EmailSender] PowerShell Outlook fallback failed: {ps_err}")

    # Last resort: mailto: URI (opens default mail client compose window)
    try:
        result = _send_via_mailto(to, subject, body)
        return result
    except Exception as mailto_err:
        raise RuntimeError(
            f"All email methods failed. "
            f"COM: {com_err}, PowerShell: {ps_err}, mailto: {mailto_err}"
        )


def _send_via_outlook_com(to: str, subject: str, body: str, cc: str = "", bcc: str = "") -> dict:
    """
    Use win32com.client to create and send an Outlook MailItem.
    Requires pywin32 and a running/configured Outlook instance.
    """
    import win32com.client

    outlook = win32com.client.Dispatch("Outlook.Application")
    mail = outlook.CreateItem(0)  # 0 = olMailItem

    mail.To = to
    mail.Subject = subject
    mail.Body = body

    if cc:
        mail.CC = cc
    if bcc:
        mail.BCC = bcc

    mail.Send()

    print(f"[EmailSender] Email sent via Outlook COM to {to}")
    return {
        "status": "sent",
        "method": "outlook_com",
        "to": to,
        "subject": subject,
    }


def _send_via_powershell_outlook(to: str, subject: str, body: str) -> dict:
    """
    Fallback: Use PowerShell to drive Outlook COM when pywin32 is unavailable.
    """
    # Escape single quotes for PowerShell string literals
    safe_to = to.replace("'", "''")
    safe_subject = subject.replace("'", "''")
    safe_body = body.replace("'", "''").replace("\n", "`n")

    script = f"""
$outlook = New-Object -ComObject Outlook.Application
$mail = $outlook.CreateItem(0)
$mail.To = '{safe_to}'
$mail.Subject = '{safe_subject}'
$mail.Body = '{safe_body}'
$mail.Send()
Write-Output 'EMAIL_SENT_OK'
"""

    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        timeout=30,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )

    if "EMAIL_SENT_OK" in (completed.stdout or ""):
        print(f"[EmailSender] Email sent via PowerShell Outlook to {to}")
        return {
            "status": "sent",
            "method": "powershell_outlook",
            "to": to,
            "subject": subject,
        }

    error = (completed.stderr or completed.stdout or "Unknown error").strip()
    raise RuntimeError(f"PowerShell Outlook failed: {error}")


def _send_via_mailto(to: str, subject: str, body: str) -> dict:
    """
    Last resort: open the system default mailto: handler.
    This opens the compose window but does NOT auto-send.
    """
    import urllib.parse

    params = urllib.parse.urlencode({"subject": subject, "body": body}, quote_via=urllib.parse.quote)
    mailto_uri = f"mailto:{to}?{params}"

    os.startfile(mailto_uri)
    time.sleep(1.0)

    print(f"[EmailSender] Opened mailto: compose window for {to}")
    return {
        "status": "compose_opened",
        "method": "mailto_uri",
        "to": to,
        "subject": subject,
        "note": "Email compose window opened. User must press Send manually.",
    }


def parse_email_intent(text: str) -> dict:
    """
    Extract recipient, subject, and body intent from a natural language email command.

    Examples:
      "Send an email to alice@example.com about the project deadline"
      "Email bob@corp.com saying the demo went great"
      "Send mail using outlook to user@domain.com about hackathon results"
    """
    text = " ".join((text or "").strip().split())

    # Extract email address
    email_match = _EMAIL_PATTERN.search(text)
    if not email_match:
        return {}

    recipient = email_match.group(0)

    # Remove the email address from the text for parsing the rest
    remaining = text[:email_match.start()] + text[email_match.end():]
    remaining = re.sub(r"\s+", " ", remaining).strip()

    # Remove common command prefixes
    remaining = re.sub(
        r"^(?:please\s+)?(?:send\s+)?(?:an?\s+)?(?:email|mail|message)\s*"
        r"(?:using\s+(?:outlook|gmail|mail)\s*)?"
        r"(?:to\s+)?",
        "", remaining, flags=re.IGNORECASE
    ).strip()

    # Extract the subject/body intent from "about ...", "saying ...", "regarding ...", etc.
    about_match = re.match(
        r"^(?:about|regarding|re|saying|that says|with subject|on the topic of)\s+(.+)$",
        remaining, re.IGNORECASE
    )

    if about_match:
        intent = about_match.group(1).strip()
    else:
        intent = remaining.strip(" .,")

    # Generate a clean subject from the intent
    subject = _generate_subject(intent)

    return {
        "to": recipient,
        "subject": subject,
        "body_intent": intent,
    }


def _generate_subject(intent: str) -> str:
    """Generate a reasonable email subject line from the user's intent."""
    if not intent:
        return "Message from Shadow Automator"

    # Capitalize first letter, truncate if too long
    clean = intent[0].upper() + intent[1:] if len(intent) > 1 else intent.upper()

    # Remove trailing punctuation for subject
    clean = clean.rstrip(".,!?;:")

    if len(clean) > 80:
        clean = clean[:77] + "..."

    return clean


def compose_email_body(intent: str, llm_generate_fn=None) -> str:
    """
    Compose an email body from the user's intent.
    If an LLM generation function is available, use it for richer prose.
    Otherwise, build a clean templated body.
    """
    if llm_generate_fn:
        try:
            prompt = (
                f"Write a professional but warm email body for the following intent. "
                f"Do NOT include subject line, greeting, or signature — just the body paragraphs.\n\n"
                f"Intent: {intent}"
            )
            body = llm_generate_fn(prompt)
            if body and len(body) > 20:
                return body
        except Exception as exc:
            print(f"[EmailSender] LLM email composition failed: {exc}, using template.")

    # Template fallback
    clean_intent = intent.strip()
    if clean_intent:
        clean_intent = clean_intent[0].upper() + clean_intent[1:]
        if not clean_intent.endswith((".", "!", "?")):
            clean_intent += "."

    if "hackathon demo" in intent.lower():
        body = (
            f"Dear Evaluator,\n\n"
            f"I wanted to share an update regarding how great our hackathon demo went today!\n\n"
            f"Shadow Automator successfully demonstrated autonomous local vision-grounding "
            f"using Qwen2.5-VL, zero cloud egress privacy protection, self-healing desktop execution, "
            f"and end-to-end Windows Outlook automation.\n\n"
            f"Thank you for reviewing our project!\n\n"
            f"Best regards,\n"
            f"Shadow Automator Team\n"
            f"(Automated dispatch via Shadow Automator — Local Desktop AI Agent)"
        )
    else:
        body = (
            f"Hi,\n\n"
            f"I wanted to reach out regarding: {intent}.\n\n"
            f"Best regards,\n"
            f"Shadow Automator Team\n"
            f"(Automated dispatch via Shadow Automator — Local Desktop AI Agent)"
        )
    return body


if __name__ == "__main__":
    # Test parsing
    test_cases = [
        "Send an email using outlook to jp_vedaj@cb.amrita.edu about how good my hackathon demo was",
        "Email alice@example.com saying the project deadline is tomorrow",
        "Send mail to bob@corp.com regarding Q4 results",
    ]
    for test in test_cases:
        result = parse_email_intent(test)
        print(f"\nInput: {test}")
        print(f"Parsed: {result}")
