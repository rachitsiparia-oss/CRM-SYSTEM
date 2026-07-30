import { ArticleDetail } from "./article-detail";

export default async function Page({ params }: { params: Promise<{ articleId: string }> }) {
  const { articleId } = await params;
  return <ArticleDetail articleId={articleId} />;
}
