import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { formatCount } from "@/lib/format";

interface KpiTileProps {
  label: string;
  /** Already formatted, or "–" when there is nothing to show. */
  value: string;
  /** Sample size behind the number. */
  n: number;
  /** Rows not counted (for example reviews without a rating). */
  missing?: number;
  lowSample?: boolean;
  /** Plain-language definition shown under the number. */
  note?: string;
}

/** A headline number that always shows how many observations it rests on. */
export function KpiTile({ label, value, n, missing = 0, lowSample = false, note }: KpiTileProps) {
  return (
    <Card size="sm">
      <CardContent className="flex flex-col gap-1">
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className="text-3xl font-semibold tabular-nums tracking-tight">{value}</p>
        <p className="text-xs text-muted-foreground">
          Based on {formatCount(n)} {n === 1 ? "review" : "reviews"}
          {missing > 0 && `; ${formatCount(missing)} without a value`}
        </p>
        {note && <p className="text-xs text-muted-foreground">{note}</p>}
        {lowSample && (
          <Badge variant="outline" className="mt-1 w-fit">
            Low sample
          </Badge>
        )}
      </CardContent>
    </Card>
  );
}
