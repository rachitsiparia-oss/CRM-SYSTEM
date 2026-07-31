import { AchievementDetail } from "./achievement-detail";

export default async function Page({ params }: { params: Promise<{ achievementId: string }> }) {
  const { achievementId } = await params;
  return <AchievementDetail achievementId={achievementId} />;
}
