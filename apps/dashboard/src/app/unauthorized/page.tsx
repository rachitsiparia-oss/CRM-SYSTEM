import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function UnauthorizedPage() {
  return (
    <div className="flex min-h-screen flex-1 items-center justify-center p-6">
      <div className="w-full max-w-md text-center">
        <h1 className="mb-2 text-lg font-semibold">Not signed in</h1>
        <p className="mb-6 text-sm text-zinc-500">
          You need to sign in to access the RKPR Restaurant CRM.
        </p>
        <Button asChild>
          <Link href="/login">Go to sign in</Link>
        </Button>
      </div>
    </div>
  );
}
