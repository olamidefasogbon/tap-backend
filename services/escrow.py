# services/escrow.py
from decimal import Decimal, ROUND_DOWN
from core.config import settings

def calculate_escrow_split(buyer_amount_kobo: int) -> dict:
    """
    Given the amount the buyer pays (in Kobo), return a breakdown of:
    - tap_fee:            Platform fee (4% of buyer amount)
    - vendor_net:         What the vendor ultimately receives
    - first_disbursement: 50% of vendor_net — released on payment
    - second_disbursement: 50% of vendor_net — released after 12hr

    All arithmetic is done with integers (Kobo) to avoid float imprecision.
    """
    fee_rate      = settings.PLATFORM_FEE_PERCENT / Decimal('100')
    tap_fee       = int(Decimal(buyer_amount_kobo) * fee_rate.quantize(Decimal('0.01'), rounding=ROUND_DOWN))
    vendor_net    = buyer_amount_kobo - tap_fee
    first_half    = vendor_net // 2
    second_half   = vendor_net - first_half  # Handles odd-kobo rounding

    return {
        'tap_fee':             tap_fee,
        'vendor_net':          vendor_net,
        'first_disbursement':  first_half,
        'second_disbursement': second_half,
    }