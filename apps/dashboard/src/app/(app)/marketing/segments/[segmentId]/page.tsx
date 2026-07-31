import { SegmentDetail } from "./segment-detail";

export default async function Page({ params }: { params: Promise<{ segmentId: string }> }) {
  const { segmentId } = await params;
  return <SegmentDetail segmentId={segmentId} />;
}
