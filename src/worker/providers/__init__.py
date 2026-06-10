from .base import NotificationProvider
from .email_provider import SMTPEmailProvider, MockEmailProvider
from .sms_provider import MockSMSProvider
from src.shared.models.notification import NotificationChannel
from src.shared.settings import settings

def get_provider(channel: NotificationChannel) -> NotificationProvider:
    if channel == NotificationChannel.EMAIL:
        if settings.email.provider == "mock":
            return MockEmailProvider()
        
        if settings.email.provider == "smtp":
            return SMTPEmailProvider()
        
        raise ValueError(f"Unknown provider: {settings.sms.provider}. Available: mock, smtp")
    
    elif channel == NotificationChannel.SMS:
        if settings.sms.provider == "mock":
            return MockSMSProvider()
        
        raise ValueError(f"Unknown provider: {settings.sms.provider}. Available: mock")
    
    raise ValueError(f"Unknown channel: {channel}")