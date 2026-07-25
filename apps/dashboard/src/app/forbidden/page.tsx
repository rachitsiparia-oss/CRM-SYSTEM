import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function ForbiddenPage() {
  return (
    <div className="flex min-h-screen flex-1 items-center justify-center p-6">
      <div className="w-full max-w-md text-center">
        <h1 className="mb-2 text-lg font-semibold">You don&apos;t have access to this</h1>
        <p className="mb-6 text-sm text-zinc-500">
          Your account doesn&apos;t have the permission required for this page. Contact your
          manager if you believe this is a mistake.
        </p>
        <Button asChild>
          <Link href="/">Back to dashboard</Link>
        </Button>
      </div>
    </div>
  );
}
