import { PermissionGate } from "@/components/permission-gate";
import { RecipeDirectory } from "./recipe-directory";

export default function Page() {
  return (
    <PermissionGate permission="inventory.recipes.view">
      <RecipeDirectory />
    </PermissionGate>
  );
}
