import { Suspense } from "react";
import { LoginForm } from "./login-form";

export default function LoginPage() {
  return (
    <div className="flex min-h-screen flex-1 items-center justify-center p-6">
      <div className="w-full max-w-sm rounded-lg border border-black/10 p-6 dark:border-white/15">
        <h1 className="mb-1 text-lg font-semibold">RKPR Restaurant CRM</h1>
        <p className="mb-6 text-sm text-muted-foreground">Sign in with your staff account.</p>
        <Suspense>
          <LoginForm />
        </Suspense>
      </div>
    </div>
  );
}
