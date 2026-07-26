import { PermissionGate } from "@/components/permission-gate";
import { CategoryDirectory } from "./category-directory";

export default function Page() {
  return (
    <PermissionGate permission="menu.view">
      <CategoryDirectory />
    </PermissionGate>
  );
}
