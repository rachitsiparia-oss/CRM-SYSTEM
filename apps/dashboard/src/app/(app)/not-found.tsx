import Link from "next/link";

import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/error-state";

export default function NotFound() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 p-8">
      <ErrorState variant="404" />
      <Button asChild>
        <Link href="/">Back to dashboard</Link>
      </Button>
    </div>
  );
}
