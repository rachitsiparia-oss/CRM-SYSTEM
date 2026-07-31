import { OfferDetail } from "./offer-detail";

export default async function Page({ params }: { params: Promise<{ offerId: string }> }) {
  const { offerId } = await params;
  return <OfferDetail offerId={offerId} />;
}
