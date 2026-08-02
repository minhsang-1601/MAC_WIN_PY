#!/usr/bin/env python3
"""Suy ra IMAP host theo domain email. Chỉ hỗ trợ Gmail và Yahoo (kể cả Yahoo Japan)."""

IMAP_PORT = 993

GMAIL_DOMAINS = {"gmail.com", "googlemail.com"}

YAHOO_HOSTS = {
    "yahoo.co.jp": "imap.mail.yahoo.co.jp",
    "yahoo.com": "imap.mail.yahoo.com",
    "yahoo.co.uk": "imap.mail.yahoo.com",
    "ymail.com": "imap.mail.yahoo.com",
    "rocketmail.com": "imap.mail.yahoo.com",
}


def _domain(email_addr):
    return email_addr.strip().lower().rsplit("@", 1)[-1]


def get_provider(email_addr):
    """Trả về 'gmail' / 'yahoo' theo domain email, None nếu không hỗ trợ."""
    domain = _domain(email_addr)
    if domain in GMAIL_DOMAINS:
        return "gmail"
    if domain in YAHOO_HOSTS:
        return "yahoo"
    return None


def resolve_imap_host(email_addr):
    """Trả về (host, port) IMAP theo domain email.

    Raise ValueError nếu domain không thuộc Gmail/Yahoo.
    """
    domain = _domain(email_addr)
    if domain in GMAIL_DOMAINS:
        return "imap.gmail.com", IMAP_PORT
    if domain in YAHOO_HOSTS:
        return YAHOO_HOSTS[domain], IMAP_PORT
    raise ValueError(
        f"Domain '{domain}' chưa được hỗ trợ (chỉ Gmail và Yahoo) — email: {email_addr}"
    )
