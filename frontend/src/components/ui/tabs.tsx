import * as React from "react";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import { cn } from "../../lib/cn";

/*
 * Tabs — the active tab is marked by a gold underline rather than a filled
 * pill. On a dark ground a filled active state reads as a button and
 * competes with the real CTAs; a rule reads as position.
 */

const Tabs = TabsPrimitive.Root;

const TabsList = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.List>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.List>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.List
    ref={ref}
    className={cn("hairline-b flex items-center gap-1", className)}
    {...props}
  />
));
TabsList.displayName = TabsPrimitive.List.displayName;

const TabsTrigger = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Trigger>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Trigger
    ref={ref}
    className={cn(
      "relative -mb-px px-4 py-2.5 text-xs font-semibold tracking-wide transition-colors",
      "text-muted-foreground hover:text-foreground",
      "focus-visible:ring-gold focus-visible:outline-none focus-visible:ring-2",
      "data-[state=active]:text-foreground",
      "data-[state=active]:after:bg-gold data-[state=active]:after:absolute data-[state=active]:after:inset-x-0 data-[state=active]:after:-bottom-px data-[state=active]:after:h-px",
      className,
    )}
    {...props}
  />
));
TabsTrigger.displayName = TabsPrimitive.Trigger.displayName;

const TabsContent = React.forwardRef<
  React.ElementRef<typeof TabsPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TabsPrimitive.Content>
>(({ className, ...props }, ref) => (
  <TabsPrimitive.Content
    ref={ref}
    className={cn("focus-visible:ring-gold mt-6 focus-visible:outline-none focus-visible:ring-2", className)}
    {...props}
  />
));
TabsContent.displayName = TabsPrimitive.Content.displayName;

export { Tabs, TabsList, TabsTrigger, TabsContent };
