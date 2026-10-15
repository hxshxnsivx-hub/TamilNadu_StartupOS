import * as React from "react";
import { Slot } from "@radix-ui/react-slot";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "../../lib/cn";

/*
 * Button — shadcn structure, nocturne palette.
 *
 * `gold` is the primary action and is deliberately the only variant that
 * carries colour. Everything else is light-on-dark with a hairline. One
 * accent, used sparingly, is most of why the reference reads as expensive;
 * a second competing colour is what makes a UI look like a dashboard.
 */
const buttonVariants = cva(
  // Base: pill geometry matching nocturne's existing .btn, gold focus ring.
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-full font-semibold tracking-wide transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gold focus-visible:ring-offset-2 focus-visible:ring-offset-background disabled:pointer-events-none disabled:opacity-45",
  {
    variants: {
      variant: {
        gold: "btn-gold hover:-translate-y-px active:translate-y-0",
        solid:
          "bg-foreground text-background hover:bg-foreground/90 shadow-elevated",
        ghost:
          "hairline bg-white/[0.03] text-foreground hover:bg-white/[0.07] hover:hairline-gold",
        quiet: "text-muted-foreground hover:text-foreground",
        destructive:
          "bg-destructive text-destructive-foreground hover:bg-destructive/90 shadow-elevated",
      },
      size: {
        // 12px is the floor everywhere — `sm` sits ON it, never under.
        sm: "h-9 px-4 text-xs",
        md: "h-11 px-6 text-sm",
        lg: "h-13 px-9 text-[15px]",
      },
    },
    defaultVariants: { variant: "ghost", size: "md" },
  },
);

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  /** Render as the child element (e.g. a react-router <Link>) instead of <button>. */
  asChild?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : "button";
    return (
      <Comp
        className={cn(buttonVariants({ variant, size }), className)}
        ref={ref}
        {...props}
      />
    );
  },
);
Button.displayName = "Button";

export { Button, buttonVariants };
