import * as React from "react";
import { cn } from "../../lib/cn";

/*
 * Card — a translucent panel on the near-black ground.
 *
 * Not a filled box: the surface is a few percent of white over the page,
 * bounded by a hairline and lifted by an inset top highlight. That is what
 * keeps panels reading as *planes catching light* rather than as grey
 * rectangles pasted on black.
 */

const Card = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement> & { interactive?: boolean }
>(({ className, interactive = false, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "hairline relative rounded-lg bg-white/[0.025] shadow-elevated",
      interactive &&
        "transition-all duration-300 hover:bg-white/[0.05] hover:shadow-float",
      className,
    )}
    {...props}
  />
));
Card.displayName = "Card";

const CardHeader = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("flex flex-col gap-1.5 p-6", className)} {...props} />
  ),
);
CardHeader.displayName = "CardHeader";

/** Small tracked uppercase label. Sits above a title, never below. */
const CardEyebrow = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("eyebrow text-gold-deep", className)} {...props} />
  ),
);
CardEyebrow.displayName = "CardEyebrow";

const CardTitle = React.forwardRef<
  HTMLHeadingElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn("font-display text-lg leading-tight text-foreground", className)}
    {...props}
  />
));
CardTitle.displayName = "CardTitle";

const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p
    ref={ref}
    className={cn("text-[13px] leading-relaxed text-muted-foreground", className)}
    {...props}
  />
));
CardDescription.displayName = "CardDescription";

const CardContent = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("p-6 pt-0", className)} {...props} />
  ),
);
CardContent.displayName = "CardContent";

const CardFooter = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn("mt-auto flex items-center gap-3 p-6 pt-0", className)} {...props} />
  ),
);
CardFooter.displayName = "CardFooter";

export {
  Card,
  CardHeader,
  CardEyebrow,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
};
