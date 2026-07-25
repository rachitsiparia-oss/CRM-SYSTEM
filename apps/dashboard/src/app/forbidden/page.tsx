import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/error-state";

export default function ForbiddenPage() {
  return (
    <div className="flex min-h-screen flex-1 flex-col items-center justify-center gap-4 p-6">
      <ErrorState
        variant="403"
        description="Your account doesn't have the permission required for this page. Contact your manager if you believe this is a mistake."
      />
      <Button asChild>
        <Link href="/">Back to dashboard</Link>
      </Button>
    </div>
  );
}
