"use client";

import { ImportHistory } from "@/components/import/import-history";
import { ImportWizard } from "@/components/import/import-wizard";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

export function ImportWorkspace() {
  return (
    <Tabs defaultValue="new">
      <TabsList>
        <TabsTrigger value="new">New import</TabsTrigger>
        <TabsTrigger value="history">Import history</TabsTrigger>
      </TabsList>
      <TabsContent value="new">
        <ImportWizard />
      </TabsContent>
      <TabsContent value="history">
        <ImportHistory />
      </TabsContent>
    </Tabs>
  );
}
