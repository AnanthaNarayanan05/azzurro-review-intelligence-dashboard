"use client";

import { useMutation, useQueryClient, type UseQueryResult } from "@tanstack/react-query";
import { Loader2, Plus } from "lucide-react";
import { toast } from "sonner";

import { ErrorState } from "@/components/states/error-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { useHydrated } from "@/hooks/use-hydrated";
import { propertiesQueryKey, useProperties } from "@/hooks/use-properties";
import {
  DATE_FORMAT_LABELS,
  effectiveChoice,
  propertyProblems,
  SKIP,
  type PropertyChoice,
  type PropertyMode,
} from "@/lib/import-wizard";
import { createProperty } from "@/services/properties";
import type { DateFormat, ImportPreview, Property, PropertyValue, PropertyValues } from "@/types/api";

export interface OptionsState {
  mode: PropertyMode;
  fixedPropertyId: number | null;
  choices: Record<string, PropertyChoice>;
  scalePreset: "10" | "5" | "100" | "custom";
  customScale: string;
  dateFormat: DateFormat;
  sourceName: string;
  isSynthetic: boolean;
}

export const DEFAULT_OPTIONS: OptionsState = {
  mode: "column",
  fixedPropertyId: null,
  choices: {},
  scalePreset: "10",
  customScale: "",
  dateFormat: "auto",
  sourceName: "booking.com",
  isSynthetic: false,
};

export function ratingScaleOf(options: OptionsState): number {
  return options.scalePreset === "custom" ? Number(options.customScale) : Number(options.scalePreset);
}

interface OptionsStepProps {
  preview: ImportPreview;
  mapping: Record<string, string>;
  options: OptionsState;
  onChange: (patch: Partial<OptionsState>) => void;
  /** Distinct values of the property column; owned by the wizard because it needs them to build the request. */
  valuesQuery: UseQueryResult<PropertyValues>;
  onBack: () => void;
  onSubmit: () => void;
  submitting: boolean;
  submitError: string | null;
}

export function OptionsStep(props: OptionsStepProps) {
  const { preview, mapping, options, onChange, valuesQuery, onBack, onSubmit, submitting, submitError } = props;
  const values = valuesQuery.data?.values ?? [];
  const hydrated = useHydrated();
  const properties = useProperties();
  const queryClient = useQueryClient();
  const propertyColumn = mapping.property;

  const createMutation = useMutation({
    mutationFn: (name: string) => createProperty({ name }),
    onSuccess: (created, name) => {
      onChange({ choices: { ...options.choices, [name]: created.id } });
      void queryClient.invalidateQueries({ queryKey: propertiesQueryKey });
      toast.success(`Property "${created.name}" created.`);
    },
    onError: (error: Error) => toast.error(error.message),
  });

  const scale = ratingScaleOf(options);
  const scaleValid = Number.isFinite(scale) && scale > 0 && scale <= 100;
  const problems = [
    ...propertyProblems({
      mode: options.mode,
      fixedPropertyId: options.fixedPropertyId,
      mapping,
      values,
      choices: options.choices,
    }),
    ...(scaleValid ? [] : ["Enter a rating scale between 1 and 100."]),
    ...(options.isSynthetic || options.sourceName.trim() ? [] : ["Enter the platform this export came from."]),
  ];
  const propertyList: Property[] = properties.data ?? [];
  const skippedRows = values
    .filter((value) => effectiveChoice(value, options.choices) === SKIP)
    .reduce((sum, value) => sum + value.count, 0);

  return (
    <div className="space-y-8">
      <section className="space-y-4" aria-labelledby="property-heading">
        <h3 id="property-heading" className="text-sm font-semibold">
          Which hotel is each review for?
        </h3>
        <div className="flex flex-wrap gap-2" role="group" aria-label="How the file identifies the property">
          <Button
            variant={options.mode === "column" ? "default" : "outline"}
            size="sm"
            aria-pressed={options.mode === "column"}
            onClick={() => onChange({ mode: "column" })}
            disabled={!propertyColumn}
          >
            The file has a property column{propertyColumn ? ` (${propertyColumn})` : ""}
          </Button>
          <Button
            variant={options.mode === "fixed" ? "default" : "outline"}
            size="sm"
            aria-pressed={options.mode === "fixed"}
            onClick={() => onChange({ mode: "fixed" })}
          >
            All rows belong to one property
          </Button>
        </div>

        {!hydrated || properties.isPending ? (
          <Skeleton className="h-24 w-full" />
        ) : properties.isError ? (
          <ErrorState title="Could not load properties" message={properties.error.message} onRetry={() => properties.refetch()} />
        ) : options.mode === "fixed" ? (
          <div className="max-w-sm space-y-2">
            <Label htmlFor="fixed-property">Property</Label>
            <Select
              value={options.fixedPropertyId === null ? undefined : String(options.fixedPropertyId)}
              onValueChange={(value) => onChange({ fixedPropertyId: Number(value) })}
            >
              <SelectTrigger id="fixed-property" className="w-full">
                <SelectValue placeholder="Choose a property" />
              </SelectTrigger>
              <SelectContent>
                {propertyList.map((property) => (
                  <SelectItem key={property.id} value={String(property.id)}>
                    {property.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {propertyList.length === 0 && (
              <p className="text-sm text-muted-foreground">
                No properties exist yet. Add them under Settings, or use a property column and create them here.
              </p>
            )}
          </div>
        ) : valuesQuery.isError ? (
          <ErrorState title="Could not read the property column" message={valuesQuery.error.message} onRetry={() => valuesQuery.refetch()} />
        ) : valuesQuery.isPending ? (
          <Skeleton className="h-32 w-full" />
        ) : (
          <PropertyValueTable
            values={values}
            properties={propertyList}
            choices={options.choices}
            onChoose={(raw, choice) => onChange({ choices: { ...options.choices, [raw]: choice } })}
            onCreate={(name) => createMutation.mutate(name)}
            creating={createMutation.isPending ? createMutation.variables : null}
            truncated={valuesQuery.data.truncated}
          />
        )}
        {skippedRows > 0 && (
          <p className="text-sm text-muted-foreground">
            {skippedRows.toLocaleString()} rows are set to be skipped. They will be rejected and listed in the report.
          </p>
        )}
      </section>

      <section className="grid gap-x-6 gap-y-5 md:grid-cols-2" aria-labelledby="format-heading">
        <h3 id="format-heading" className="text-sm font-semibold md:col-span-2">
          How should the values be read?
        </h3>

        <div className="space-y-2">
          <Label htmlFor="rating-scale">Rating scale in this file</Label>
          <Select
            value={options.scalePreset}
            onValueChange={(value) => onChange({ scalePreset: value as OptionsState["scalePreset"] })}
          >
            <SelectTrigger id="rating-scale" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="10">Out of 10 (Booking.com style)</SelectItem>
              <SelectItem value="5">Out of 5</SelectItem>
              <SelectItem value="100">Out of 100</SelectItem>
              <SelectItem value="custom">Other maximum…</SelectItem>
            </SelectContent>
          </Select>
          {options.scalePreset === "custom" && (
            <Input
              inputMode="decimal"
              aria-label="Highest possible rating"
              placeholder="Highest possible rating, e.g. 7"
              value={options.customScale}
              onChange={(event) => onChange({ customScale: event.target.value })}
            />
          )}
          <p className="text-xs text-muted-foreground">
            Ratings are converted to a 0–10 scale so properties can be compared. The original value is kept.
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="date-format">Date format</Label>
          <Select value={options.dateFormat} onValueChange={(value) => onChange({ dateFormat: value as DateFormat })}>
            <SelectTrigger id="date-format" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {(Object.keys(DATE_FORMAT_LABELS) as DateFormat[]).map((format) => (
                <SelectItem key={format} value={format}>
                  {DATE_FORMAT_LABELS[format]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">
            A date like 03/04/2026 could mean 3 April or 4 March. If your file uses that style, pick the right order.
          </p>
        </div>

        <div className="space-y-2">
          <Label htmlFor="source-name">Where did this file come from?</Label>
          <Input
            id="source-name"
            value={options.isSynthetic ? "synthetic-demo" : options.sourceName}
            disabled={options.isSynthetic}
            maxLength={64}
            onChange={(event) => onChange({ sourceName: event.target.value })}
          />
          <p className="text-xs text-muted-foreground">
            Recorded with every review as its source. It describes the file you are supplying; it is not verified.
          </p>
        </div>

        <div className="flex items-start gap-3 rounded-md border p-3">
          <Checkbox
            id="is-synthetic"
            checked={options.isSynthetic}
            onCheckedChange={(checked) => onChange({ isSynthetic: checked === true })}
            className="mt-0.5"
          />
          <div className="space-y-1">
            <Label htmlFor="is-synthetic">This file contains synthetic (demo) data</Label>
            <p className="text-xs text-muted-foreground">
              Marks every review as invented. Synthetic reviews are stored and counted separately and are never
              shown as genuine guest feedback.
            </p>
          </div>
        </div>
      </section>

      {(problems.length > 0 || submitError) && (
        <div role="alert" className="space-y-1 text-sm text-destructive">
          {problems.map((problem) => (
            <p key={problem}>{problem}</p>
          ))}
          {submitError && <p>{submitError}</p>}
        </div>
      )}

      <div className="flex justify-between">
        <Button variant="outline" onClick={onBack} disabled={submitting}>
          Back
        </Button>
        <Button onClick={onSubmit} disabled={problems.length > 0 || submitting}>
          {submitting && <Loader2 className="animate-spin" aria-hidden />}
          {submitting ? "Importing…" : `Import ${preview.total_rows.toLocaleString()} rows`}
        </Button>
      </div>
    </div>
  );
}

interface PropertyValueTableProps {
  values: PropertyValue[];
  properties: Property[];
  choices: Record<string, PropertyChoice>;
  onChoose: (raw: string, choice: PropertyChoice) => void;
  onCreate: (name: string) => void;
  creating: string | null;
  truncated: boolean;
}

function PropertyValueTable({ values, properties, choices, onChoose, onCreate, creating, truncated }: PropertyValueTableProps) {
  return (
    <div className="space-y-2">
      <div className="overflow-x-auto rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Value in your file</TableHead>
              <TableHead className="w-24">Reviews</TableHead>
              <TableHead className="w-72">Property</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {values.map((value) => {
              const choice = effectiveChoice(value, choices);
              const automatic = choices[value.value] === undefined && value.suggested_property_id !== null;
              return (
                <TableRow key={value.value}>
                  <TableCell className="max-w-64 truncate font-medium">{value.value}</TableCell>
                  <TableCell className="tabular-nums">{value.count.toLocaleString()}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Select
                        value={choice === undefined ? undefined : String(choice)}
                        onValueChange={(selected) => onChoose(value.value, selected === SKIP ? SKIP : Number(selected))}
                      >
                        <SelectTrigger className="w-full" aria-label={`Property for "${value.value}"`}>
                          <SelectValue placeholder="Choose…" />
                        </SelectTrigger>
                        <SelectContent>
                          {properties.map((property) => (
                            <SelectItem key={property.id} value={String(property.id)}>
                              {property.name}
                            </SelectItem>
                          ))}
                          <SelectItem value={SKIP}>Skip these rows</SelectItem>
                        </SelectContent>
                      </Select>
                      {automatic && (
                        <Badge variant="secondary" title="Matched automatically">
                          {value.match_type === "similar" ? "Similar name" : "Matched"}
                        </Badge>
                      )}
                      {choice === undefined && (
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={creating === value.value}
                          onClick={() => onCreate(value.value)}
                          aria-label={`Create property "${value.value}"`}
                        >
                          <Plus aria-hidden /> New
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
      {truncated && (
        <p className="text-xs text-muted-foreground">Showing the 200 most common values. Rows with other values are rejected.</p>
      )}
    </div>
  );
}
