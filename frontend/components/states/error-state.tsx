import { AlertCircle, RotateCw } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

interface ErrorStateProps {
  title?: string;
  message: string;
  onRetry?: () => void;
  retrying?: boolean;
}

export function ErrorState({ title = "Something went wrong", message, onRetry, retrying }: ErrorStateProps) {
  return (
    <Alert variant="destructive">
      <AlertCircle aria-hidden />
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription>
        <p>{message}</p>
        {onRetry && (
          <Button variant="outline" size="sm" className="mt-3" onClick={onRetry} disabled={retrying}>
            <RotateCw className={retrying ? "animate-spin" : undefined} aria-hidden />
            {retrying ? "Retrying…" : "Try again"}
          </Button>
        )}
      </AlertDescription>
    </Alert>
  );
}
