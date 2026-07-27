import { PermissionGate } from "@/components/permission-gate";
import { RecipeDetail } from "./recipe-detail";

export default async function Page({ params }: { params: Promise<{ recipeId: string }> }) {
  const { recipeId } = await params;
  return (
    <PermissionGate permission="inventory.recipes.view">
      <RecipeDetail recipeId={recipeId} />
    </PermissionGate>
  );
}
