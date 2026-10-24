import * as RadioGroupPrimitive from "@radix-ui/react-radio-group";
import * as React from "react";
import { cn } from "@/lib/utils";

export const RadioGroup = React.forwardRef<React.ElementRef<typeof RadioGroupPrimitive.Root>, React.ComponentPropsWithoutRef<typeof RadioGroupPrimitive.Root>>(({ className, ...props }, ref) => <RadioGroupPrimitive.Root ref={ref} className={cn("flex flex-wrap gap-2", className)} {...props}/>);
RadioGroup.displayName = RadioGroupPrimitive.Root.displayName;

export const RadioGroupItem = React.forwardRef<React.ElementRef<typeof RadioGroupPrimitive.Item>, React.ComponentPropsWithoutRef<typeof RadioGroupPrimitive.Item>>(({ className, ...props }, ref) => <RadioGroupPrimitive.Item ref={ref} className={cn("grid h-3.5 w-3.5 shrink-0 place-items-center rounded-full border border-input bg-background shadow-[var(--shadow-control)] outline-none transition-colors hover:border-[var(--focus-border)] focus-visible:ring-1 focus-visible:ring-ring/30 disabled:cursor-not-allowed disabled:opacity-50 data-[state=checked]:border-primary", className)} {...props}><RadioGroupPrimitive.Indicator className="h-1.5 w-1.5 rounded-full bg-primary"/></RadioGroupPrimitive.Item>);
RadioGroupItem.displayName = RadioGroupPrimitive.Item.displayName;
