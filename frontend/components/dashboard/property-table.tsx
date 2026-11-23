import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { filtersHref } from "@/hooks/use-filters";
import type { FilterState } from "@/lib/filters";
import { formatCount, formatRating } from "@/lib/format";
import type { PropertyRating } from "@/types/analytics";

/** One row per property with its sample size beside the rating. Links keep the date and data filters. */
export function PropertyTable({ rows, filters }: { rows: PropertyRating[]; filters: FilterState }) {
  const carry: FilterState = { ...filters, propertyIds: [] };
  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Property</TableHead>
            <TableHead className="text-right">Reviews</TableHead>
            <TableHead className="text-right">Average rating (0–10)</TableHead>
            <TableHead className="text-right">Rated reviews</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((row) => (
            <TableRow key={row.property_id}>
              <TableCell className="font-medium">
                <Link
                  href={filtersHref(`/properties/${row.property_id}`, carry)}
                  className="underline-offset-4 hover:underline"
                >
                  {row.name}
                </Link>
              </TableCell>
              <TableCell className="text-right tabular-nums">{formatCount(row.reviews)}</TableCell>
              <TableCell className="text-right tabular-nums">
                {formatRating(row.rating.value)}
                {row.rating.low_sample && (
                  <Badge variant="outline" className="ml-2">
                    Low sample
                  </Badge>
                )}
              </TableCell>
              <TableCell className="text-right tabular-nums">{formatCount(row.rating.n)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
