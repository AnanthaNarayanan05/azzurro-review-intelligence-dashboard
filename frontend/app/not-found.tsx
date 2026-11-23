import Link from "next/link";
import { SearchX } from "lucide-react";

import { EmptyState } from "@/components/states/empty-state";
import { Button } from "@/components/ui/button";

export default function NotFound() {
  return (
    <EmptyState
      icon={SearchX}
      title="Page not found"
      description="The page you requested does not exist."
      action={
        <Button asChild variant="outline">
          <Link href="/overview">Go to overview</Link>
        </Button>
      }
    />
  );
}
