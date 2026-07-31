import { ProgramDetail } from "./program-detail";

export default async function Page({ params }: { params: Promise<{ programId: string }> }) {
  const { programId } = await params;
  return <ProgramDetail programId={programId} />;
}
