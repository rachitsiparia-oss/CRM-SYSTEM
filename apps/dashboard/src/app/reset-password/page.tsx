import { ResetPasswordForm } from "./reset-password-form";

export default function ResetPasswordPage() {
  return (
    <div className="flex min-h-screen flex-1 items-center justify-center p-6">
      <div className="w-full max-w-sm rounded-lg border border-black/10 p-6 dark:border-white/15">
        <h1 className="mb-1 text-lg font-semibold">Reset your password</h1>
        <p className="mb-6 text-sm text-muted-foreground">
          Enter your email to receive a reset link, or set a new password if you followed one.
        </p>
        <ResetPasswordForm />
      </div>
    </div>
  );
}
