# Local application imports
import uuid
from datetime import datetime, timezone
from models.user_model import (
    DelivererDetails,
    DelivererWithdrawal,
    WithdrawalMethod,
    WithdrawalStatus
)

from core.exceptions import APIException


class WithdrawalService:
    async def request_withdrawal(self, deliverer_id: str, amount: float, method: WithdrawalMethod):
        deliverer = await DelivererDetails.get(id=deliverer_id)
        
        if amount <= 0:
            raise APIException(detail="Le montant doit être positif.")
        
        if amount > deliverer.available_balance:
            raise APIException(detail="Solde insuffisant pour ce retrait.")

        reference = str(uuid.uuid4())

        # Crée une demande de retrait
        withdrawal = await DelivererWithdrawal.create(
            deliverer=deliverer,
            amount=amount,
            reference=reference,
            method=method,
            status=WithdrawalStatus.PENDING
        )

        # Bloque temporairement ce montant
        deliverer.pending_withdrawal_amount += amount
        await deliverer.save()

        return {
            "withdrawal_id": str(withdrawal.id),
            "reference": withdrawal.reference,
            "amount": float(withdrawal.amount),
            "status": withdrawal.status,
            "available_balance": deliverer.available_balance
        }

    async def confirm_withdrawal(self, withdrawal_id: str):
        withdrawal = await DelivererWithdrawal.get(id=withdrawal_id).prefetch_related("deliverer")
        deliverer = withdrawal.deliverer

        if withdrawal.status != WithdrawalStatus.PENDING:
            raise APIException(detail="Le retrait n'est pas en attente.")

        withdrawal.status = WithdrawalStatus.COMPLETED
        withdrawal.processed_at = datetime.now(timezone.utc)
        await withdrawal.save()

        # Mise à jour des totaux
        deliverer.total_withdrawn += float(withdrawal.amount)
        deliverer.pending_withdrawal_amount -= float(withdrawal.amount)
        await deliverer.save()

        return {"status": "COMPLETED", "balance": deliverer.available_balance}
