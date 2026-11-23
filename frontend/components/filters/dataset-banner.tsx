import { FlaskConical, Info } from "lucide-react";

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { formatCount, formatDate } from "@/lib/format";
import type { Dataset } from "@/types/analytics";

/**
 * Says which data the numbers on the page are made of. Synthetic demo data is never shown without
 * a visible label, and is never mixed in silently.
 */
export function DatasetBanner({ dataset }: { dataset: Dataset }) {
  if (dataset.scope === "synthetic") {
    return (
      <Alert>
        <FlaskConical aria-hidden />
        <AlertTitle>Synthetic demo data</AlertTitle>
        <AlertDescription>
          These figures come from generated demo reviews. They are not real guest feedback and say
          nothing about the hotels.
        </AlertDescription>
      </Alert>
    );
  }
  if (dataset.scope === "all") {
    return (
      <Alert>
        <FlaskConical aria-hidden />
        <AlertTitle>Genuine and synthetic reviews are mixed</AlertTitle>
        <AlertDescription>
          {formatCount(dataset.genuine_reviews)} genuine and {formatCount(dataset.synthetic_reviews)}{" "}
          synthetic demo reviews are counted together. Switch “Data” to “Genuine reviews only” for
          real results.
        </AlertDescription>
      </Alert>
    );
  }
  if (dataset.genuine_reviews === 0 && dataset.synthetic_reviews > 0) {
    return (
      <Alert>
        <Info aria-hidden />
        <AlertTitle>No genuine reviews imported yet</AlertTitle>
        <AlertDescription>
          Only synthetic demo data exists ({formatCount(dataset.synthetic_reviews)} reviews). Import a
          review file, or set “Data” to “Synthetic demo data only” to explore the dashboard.
        </AlertDescription>
      </Alert>
    );
  }
  return null;
}

export function DatasetPeriod({ dataset }: { dataset: Dataset }) {
  if (!dataset.first_review_date || !dataset.last_review_date) return null;
  return (
    <p className="text-sm text-muted-foreground">
      Reviews dated {formatDate(dataset.first_review_date)} to {formatDate(dataset.last_review_date)}.
    </p>
  );
}
