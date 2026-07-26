import { PermissionGate } from "@/components/permission-gate";
import { ProductDetail } from "./product-detail";

export default async function Page({ params }: { params: Promise<{ productId: string }> }) {
  const { productId } = await params;
  return (
    <PermissionGate permission="menu.view">
      <ProductDetail productId={productId} />
    </PermissionGate>
  );
}
