"""Pure mapping from ORM Booking to API manifest rows (DRY for driver manifest + summary)."""

from __future__ import annotations

from urllib.parse import quote

from app.domain.bookings.model import Booking
from app.domain.bookings.schema import BookingManifestItem


def booking_to_manifest_item(booking: Booking) -> BookingManifestItem | None:
    """One manifest row: phone normalization + WhatsApp link (shared by manifest endpoint and driver summary)."""
    user = booking.passenger_request.user if booking.passenger_request else None
    if not user:
        return None
    clean_phone = "".join(filter(str.isdigit, user.phone_number or ""))
    if clean_phone.startswith("0"):
        clean_phone = "972" + clean_phone[1:]
    whatsapp_link = f"https://wa.me/{clean_phone}?text={quote('היי, אני הנהג שלך מהאפליקציה')}"
    return BookingManifestItem(
        booking_id=booking.booking_id,
        passenger_id=user.user_id,
        passenger_name=user.full_name or "נוסע",
        phone=user.phone_number or "",
        whatsapp_link=whatsapp_link,
        num_seats=booking.num_seats,
        status=booking.status,
        pickup_name=booking.pickup_name,
        pickup_time=booking.pickup_time,
        destination_name=(booking.passenger_request.destination_name if booking.passenger_request else None),
    )
