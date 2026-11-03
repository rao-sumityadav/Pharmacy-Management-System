from datetime import date, timedelta
from models import Medicine

class ExpiryService:
    @staticmethod
    def get_expired_medicines():
        today = date.today()
        return Medicine.query.filter(
            Medicine.expiry_date < today,
            Medicine.is_discontinued == False
        ).order_by(Medicine.expiry_date.asc()).all()

    @staticmethod
    def get_expiring_soon_medicines(days=30):
        today = date.today()
        cutoff = today + timedelta(days=days)
        return Medicine.query.filter(
            Medicine.expiry_date >= today,
            Medicine.expiry_date <= cutoff,
            Medicine.is_discontinued == False
        ).order_by(Medicine.expiry_date.asc()).all()

    @staticmethod
    def get_expiry_metrics(days=30):
        expired = ExpiryService.get_expired_medicines()
        expiring_soon = ExpiryService.get_expiring_soon_medicines(days)
        
        expired_value = sum(m.quantity * m.cost_price for m in expired)
        expiring_value = sum(m.quantity * m.cost_price for m in expiring_soon)

        return {
            "expired_count": len(expired),
            "expiring_soon_count": len(expiring_soon),
            "expired_loss_value": round(expired_value, 2),
            "at_risk_value": round(expiring_value, 2)
        }
