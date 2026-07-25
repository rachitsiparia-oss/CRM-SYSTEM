import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function SessionExpiredPage() {
  return (
    <div className="flex min-h-screen flex-1 items-center justify-center p-6">
      <div className="w-full max-w-md text-center">
        <h1 className="mb-2 text-lg font-semibold">Your session has expired</h1>
        <p className="mb-6 text-sm text-zinc-500">
          For your security, please sign in again to continue.
        </p>
        <Button asChild>
          <Link href="/login">Sign in again</Link>
        </Button>
      </div>
    </div>
  );
}
