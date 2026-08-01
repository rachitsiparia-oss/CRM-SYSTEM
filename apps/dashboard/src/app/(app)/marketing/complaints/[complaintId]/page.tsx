import { ComplaintDetail } from "./complaint-detail";

export default async function Page({
  params,
}: {
  params: Promise<{ complaintId: string }>;
}) {
  const { complaintId } = await params;
  return <ComplaintDetail complaintId={complaintId} />;
}
