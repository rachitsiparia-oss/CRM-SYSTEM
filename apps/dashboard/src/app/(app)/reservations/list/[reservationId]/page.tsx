import { PermissionGate } from "@/components/permission-gate";
import { ReservationDetail } from "../reservation-detail";

export default async function Page({
  params,
}: {
  params: Promise<{ reservationId: string }>;
}) {
  const { reservationId } = await params;
  return (
    <PermissionGate permission="reservations.view">
      <ReservationDetail reservationId={reservationId} />
    </PermissionGate>
  );
}
