"use client";

import Link from "next/link";
import { useState } from "react";
import { ChevronDown, ChevronUp, ExternalLink, FlaskConical } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatCount, formatDate } from "@/lib/format";
import { STRENGTH_LABELS, TYPE_LABELS, exampleReviewHref, supportingReviewsHref } from "@/lib/insights";
import type { EvidenceStrength, Insight, InsightType } from "@/types/analytics";

const CONCERN_TYPES: InsightType[] = [
  "emerging_negative_trend",
  "cross_property_issue",
  "property_issue",
  "recurring_complaint",
];

function typeVariant(type: InsightType) {
  if (CONCERN_TYPES.includes(type)) return "destructive" as const;
  return type === "strength" ? ("default" as const) : ("secondary" as const);
}

function strengthVariant(strength: EvidenceStrength) {
  return strength === "limited" ? ("outline" as const) : ("secondary" as const);
}

interface InsightCardProps {
  insight: Insight;
  /** The Overview teaser shows the headline only. */
  compact?: boolean;
}

/**
 * One insight: what was found, why, what to do, and the actual guest sentences behind it. Every
 * number in the text comes from the stored metrics; the examples are verbatim review sentences.
 */
export function InsightCard({ insight, compact = false }: InsightCardProps) {
  const [open, setOpen] = useState(false);
  const examplesId = `insight-${insight.id}-examples`;
  const shown = insight.evidence.length;

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={typeVariant(insight.insight_type)}>{TYPE_LABELS[insight.insight_type]}</Badge>
          <Badge variant={strengthVariant(insight.evidence_strength)}>
            {STRENGTH_LABELS[insight.evidence_strength]}
          </Badge>
          {insight.data_scope !== "genuine" && (
            <Badge variant="outline">
              <FlaskConical aria-hidden />
              {insight.data_scope === "synthetic" ? "Synthetic demo data" : "Genuine + synthetic mixed"}
            </Badge>
          )}
        </div>
        <CardTitle className="text-base">{insight.title}</CardTitle>
        <p className="text-xs text-muted-foreground">
          {insight.properties.map((p) => p.name).join(", ")} · {formatDate(insight.period_start)} to{" "}
          {formatDate(insight.period_end)} · {formatCount(insight.supporting_review_count)} supporting{" "}
          {insight.supporting_review_count === 1 ? "review" : "reviews"}
        </p>
      </CardHeader>
      {!compact && (
        <CardContent className="flex flex-col gap-4">
          <p className="text-sm">{insight.explanation}</p>
          <div className="rounded-md bg-muted/50 p-3 text-sm">
            <p className="font-medium">Suggested action</p>
            <p className="mt-1 text-muted-foreground">{insight.recommended_action}</p>
          </div>

          <div className="flex flex-wrap gap-2">
            <Button asChild variant="outline" size="sm">
              <Link href={supportingReviewsHref(insight)}>
                See all {formatCount(insight.supporting_review_count)} reviews{" "}
                <ExternalLink aria-hidden />
              </Link>
            </Button>
            {shown > 0 && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                aria-expanded={open}
                aria-controls={examplesId}
                onClick={() => setOpen((v) => !v)}
              >
                {open ? "Hide" : "Show"} {shown} example {shown === 1 ? "sentence" : "sentences"}
                {open ? <ChevronUp aria-hidden /> : <ChevronDown aria-hidden />}
              </Button>
            )}
          </div>

          {open && (
            <ul id={examplesId} className="flex flex-col gap-3 border-l-2 pl-4">
              {insight.evidence.map((item) => (
                <li key={item.review_id} className="text-sm">
                  <blockquote className="italic">“{item.excerpt}”</blockquote>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {item.property_name} · {formatDate(item.review_date)}
                    {item.rating !== null && ` · rated ${item.rating}`}
                    {item.is_synthetic && " · synthetic"} ·{" "}
                    <Link
                      href={exampleReviewHref(insight, item.review_id)}
                      className="underline underline-offset-2 hover:text-foreground"
                    >
                      Open full review
                    </Link>
                  </p>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      )}
    </Card>
  );
}
