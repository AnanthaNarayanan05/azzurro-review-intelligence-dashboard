import { formatCount } from "@/lib/format";

interface SplitBarProps {
  positive: number;
  neutral: number;
  negative: number;
  label: string;
}

/** A thin positive/neutral/negative bar for table rows. The exact counts are in the title and label. */
export function SplitBar({ positive, neutral, negative, label }: SplitBarProps) {
  const parts = [
    { name: "positive", n: positive, color: "var(--viz-positive)" },
    { name: "neutral", n: neutral, color: "var(--viz-neutral)" },
    { name: "negative", n: negative, color: "var(--viz-negative)" },
  ];
  return (
    <div
      className="flex h-2.5 w-full min-w-24 gap-0.5 overflow-hidden rounded-full bg-muted"
      role="img"
      aria-label={`${label}: ${positive} positive, ${neutral} neutral, ${negative} negative`}
    >
      {parts.map((part) =>
        part.n > 0 ? (
          <div
            key={part.name}
            title={`${formatCount(part.n)} ${part.name}`}
            style={{ flexGrow: part.n, backgroundColor: part.color }}
          />
        ) : null,
      )}
    </div>
  );
}
