import type { Metadata } from "next";

import { ImportWorkspace } from "@/components/import/import-workspace";
import { PageHeader } from "@/components/layout/page-header";

export const metadata: Metadata = { title: "Data Import" };

export default function ImportPage() {
  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Data Import"
        description="Bring review exports in from CSV or Excel. Every row is checked, and nothing is dropped without being reported."
      />
      <ImportWorkspace />
    </div>
  );
}
