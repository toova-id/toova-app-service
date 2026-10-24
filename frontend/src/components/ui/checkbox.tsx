import * as CheckboxPrimitive from "@radix-ui/react-checkbox";
import { Check, Minus } from "lucide-react";
import * as React from "react";
import { cn } from "@/lib/utils";

export const Checkbox = React.forwardRef<React.ElementRef<typeof CheckboxPrimitive.Root>, React.ComponentPropsWithoutRef<typeof CheckboxPrimitive.Root>>(({ className, ...props }, ref) => <CheckboxPrimitive.Root ref={ref} className={cn("peer grid h-3.5 w-3.5 shrink-0 place-items-center rounded-[3px] border border-input bg-background shadow-[var(--shadow-control)] outline-none transition-colors hover:border-[var(--focus-border)] focus-visible:ring-1 focus-visible:ring-ring/30 disabled:cursor-not-allowed disabled:opacity-50 data-[state=checked]:border-primary data-[state=checked]:bg-primary data-[state=checked]:text-primary-foreground data-[state=indeterminate]:border-primary data-[state=indeterminate]:bg-primary data-[state=indeterminate]:text-primary-foreground", className)} {...props}><CheckboxPrimitive.Indicator>{props.checked === "indeterminate" ? <Minus className="h-2.5 w-2.5"/> : <Check className="h-2.5 w-2.5"/>}</CheckboxPrimitive.Indicator></CheckboxPrimitive.Root>);
Checkbox.displayName = CheckboxPrimitive.Root.displayName;
