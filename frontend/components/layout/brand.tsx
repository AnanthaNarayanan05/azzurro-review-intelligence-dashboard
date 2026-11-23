import { APP_ICON, APP_NAME, APP_SUBTITLE } from "@/lib/navigation";

export function Brand() {
  const Icon = APP_ICON;
  return (
    <div className="flex items-center gap-3">
      <div className="flex size-8 items-center justify-center rounded-md bg-primary text-primary-foreground">
        <Icon className="size-4" aria-hidden />
      </div>
      <div className="leading-tight">
        <p className="text-sm font-semibold">{APP_NAME}</p>
        <p className="text-xs text-muted-foreground">{APP_SUBTITLE}</p>
      </div>
    </div>
  );
}
