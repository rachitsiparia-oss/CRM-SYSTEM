import { GiftCardDetail } from "./gift-card-detail";

export default async function Page({ params }: { params: Promise<{ giftCardId: string }> }) {
  const { giftCardId } = await params;
  return <GiftCardDetail giftCardId={giftCardId} />;
}
