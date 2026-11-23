"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, X } from "lucide-react";
import { useState, type FormEvent } from "react";
import { toast } from "sonner";

import { EmptyState } from "@/components/states/empty-state";
import { ErrorState } from "@/components/states/error-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { useHydrated } from "@/hooks/use-hydrated";
import { propertiesQueryKey, useProperties } from "@/hooks/use-properties";
import { addAlias, createProperty, deleteAlias, updateProperty } from "@/services/properties";
import type { Property } from "@/types/api";
import { Building2 } from "lucide-react";

function AliasEditor({ property }: { property: Property }) {
  const queryClient = useQueryClient();
  const [alias, setAlias] = useState("");
  const refresh = () => queryClient.invalidateQueries({ queryKey: propertiesQueryKey });

  const add = useMutation({
    mutationFn: (value: string) => addAlias(property.id, value),
    onSuccess: () => {
      setAlias("");
      void refresh();
    },
    onError: (error: Error) => toast.error(error.message),
  });
  const remove = useMutation({
    mutationFn: (aliasId: number) => deleteAlias(property.id, aliasId),
    onSuccess: () => void refresh(),
    onError: (error: Error) => toast.error(error.message),
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (alias.trim()) add.mutate(alias.trim());
  }

  return (
    <div className="space-y-2">
      <Label htmlFor={`alias-${property.id}`} className="text-xs text-muted-foreground">
        Other spellings used in files (aliases)
      </Label>
      {property.aliases.length > 0 && (
        <ul className="flex flex-wrap gap-2">
          {property.aliases.map((item) => (
            <li key={item.id}>
              <Badge variant="secondary" className="gap-1 pr-1">
                {item.alias_normalised}
                <button
                  type="button"
                  className="rounded-full p-0.5 hover:bg-background/60"
                  aria-label={`Remove alias ${item.alias_normalised}`}
                  disabled={remove.isPending}
                  onClick={() => remove.mutate(item.id)}
                >
                  <X className="size-3" aria-hidden />
                </button>
              </Badge>
            </li>
          ))}
        </ul>
      )}
      <form onSubmit={submit} className="flex max-w-md gap-2">
        <Input
          id={`alias-${property.id}`}
          value={alias}
          maxLength={200}
          placeholder="Add a spelling, e.g. a name used in exports"
          onChange={(event) => setAlias(event.target.value)}
        />
        <Button type="submit" variant="outline" size="sm" disabled={!alias.trim() || add.isPending}>
          Add
        </Button>
      </form>
    </div>
  );
}

function PropertyCard({ property }: { property: Property }) {
  const queryClient = useQueryClient();
  const toggle = useMutation({
    mutationFn: (isActive: boolean) => updateProperty(property.id, { is_active: isActive }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: propertiesQueryKey }),
    onError: (error: Error) => toast.error(error.message),
  });

  return (
    <Card size="sm">
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center gap-2">
          {property.name}
          {!property.is_active && <Badge variant="outline">Inactive</Badge>}
        </CardTitle>
        <CardDescription>
          {property.review_count.toLocaleString()} imported reviews
          {property.synthetic_review_count > 0 &&
            ` · ${property.synthetic_review_count.toLocaleString()} synthetic demo reviews (counted separately)`}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center gap-2">
          <Checkbox
            id={`active-${property.id}`}
            checked={property.is_active}
            disabled={toggle.isPending}
            onCheckedChange={(checked) => toggle.mutate(checked === true)}
          />
          <Label htmlFor={`active-${property.id}`}>Active (included in analytics)</Label>
        </div>
        <AliasEditor property={property} />
      </CardContent>
    </Card>
  );
}

export function PropertyManager() {
  const hydrated = useHydrated();
  const properties = useProperties();
  const queryClient = useQueryClient();
  const [name, setName] = useState("");

  const create = useMutation({
    mutationFn: (value: string) => createProperty({ name: value }),
    onSuccess: (created) => {
      setName("");
      toast.success(`Property "${created.name}" added.`);
      void queryClient.invalidateQueries({ queryKey: propertiesQueryKey });
    },
    onError: (error: Error) => toast.error(error.message),
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (name.trim()) create.mutate(name.trim());
  }

  return (
    <section className="space-y-4" aria-labelledby="properties-heading">
      <div>
        <h2 id="properties-heading" className="text-lg font-semibold">
          Properties
        </h2>
        <p className="text-sm text-muted-foreground">
          The hotels reviews are imported for. Names come from your data; nothing is built in.
        </p>
      </div>

      <form onSubmit={submit} className="flex max-w-md gap-2">
        <div className="flex-1">
          <Label htmlFor="new-property" className="sr-only">
            New property name
          </Label>
          <Input
            id="new-property"
            value={name}
            maxLength={200}
            placeholder="New property name"
            onChange={(event) => setName(event.target.value)}
          />
        </div>
        <Button type="submit" disabled={!name.trim() || create.isPending}>
          <Plus aria-hidden /> Add property
        </Button>
      </form>

      {!hydrated || properties.isPending ? (
        <Skeleton className="h-40 w-full" />
      ) : properties.isError ? (
        <ErrorState title="Could not load properties" message={properties.error.message} onRetry={() => properties.refetch()} />
      ) : properties.data.length === 0 ? (
        <EmptyState
          icon={Building2}
          title="No properties yet"
          description="Add a property above, or load the demo data or import a file that has a property column."
        />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          {properties.data.map((property) => (
            <PropertyCard key={property.id} property={property} />
          ))}
        </div>
      )}
    </section>
  );
}
