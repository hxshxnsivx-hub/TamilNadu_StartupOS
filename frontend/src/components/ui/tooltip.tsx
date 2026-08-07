import * as React from "react";
import * as TooltipPrimitive from "@radix-ui/react-tooltip";
import { cn } from "../../lib/cn";

/*
 * Tooltip. Note the 12px floor applies here too — tooltips are exactly
 * where small type creeps back in, and this product's users are the ones
 * least able to absorb it.
 */

const TooltipProvider = TooltipPrimitive.Provider;
const Tooltip = TooltipPrimitive.Root;
const TooltipTrigger = TooltipPrimitive.Trigger;

const TooltipContent = React.forwardRef<
  React.ElementRef<typeof TooltipPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TooltipPrimitive.Content>
>(({ className, sideOffset = 6, ...props }, ref) => (
  <TooltipPrimitive.Content
    ref={ref}
    sideOffset={sideOffset}
    className={cn(
      "hairline bg-deep shadow-float z-50 max-w-xs rounded-md px-3 py-2 text-xs leading-relaxed text-foreground",
      "data-[state=delayed-open]:animate-in data-[state=closed]:animate-out",
      "data-[state=delayed-open]:fade-in-0 data-[state=closed]:fade-out-0",
      "data-[state=delayed-open]:zoom-in-95 data-[state=closed]:zoom-out-95",
      className,
    )}
    {...props}
  />
));
TooltipContent.displayName = TooltipPrimitive.Content.displayName;

export { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider };
