import { PermissionGate } from "@/components/permission-gate";
import { StaffDetail } from "./staff-detail";

export default async function Page({ params }: { params: Promise<{ staffId: string }> }) {
  const { staffId } = await params;
  return (
    <PermissionGate permission="staff.view">
      <StaffDetail staffId={staffId} />
    </PermissionGate>
  );
}
