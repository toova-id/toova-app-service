import * as React from "react";
import { cn } from "@/lib/utils";

export const Switch = React.forwardRef<HTMLInputElement, Omit<React.InputHTMLAttributes<HTMLInputElement>, "type">>(({ className, ...props }, ref) => <label className={cn("relative inline-flex h-8 w-8 cursor-pointer items-center align-middle", className)}><input ref={ref} type="checkbox" className="peer sr-only" {...props}/><span className="relative h-[18px] w-8 rounded-full bg-muted transition-colors after:absolute after:left-0.5 after:top-0.5 after:h-3.5 after:w-3.5 after:rounded-full after:bg-background after:shadow-[var(--shadow-control)] after:transition-transform peer-checked:bg-primary peer-checked:after:translate-x-3.5 peer-focus-visible:ring-1 peer-focus-visible:ring-ring peer-focus-visible:ring-offset-1 peer-disabled:cursor-not-allowed peer-disabled:opacity-50"/></label>);
Switch.displayName = "Switch";
