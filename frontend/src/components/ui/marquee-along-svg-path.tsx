import React, { RefObject, useCallback, useEffect, useRef } from "react";
import {
  motion,
  MotionValue,
  SpringOptions,
  useAnimationFrame,
  useMotionValue,
  useScroll,
  useSpring,
  useTransform,
  useVelocity,
} from "motion/react";

import { cn } from "@/lib/utils";

// Custom wrap function
const wrap = (min: number, max: number, value: number): number => {
  const range = max - min;
  return ((((value - min) % range) + range) % range) + min;
};

type PreserveAspectRatioAlign =
  | "none"
  | "xMinYMin"
  | "xMidYMin"
  | "xMaxYMin"
  | "xMinYMid"
  | "xMidYMid"
  | "xMaxYMid"
  | "xMinYMax"
  | "xMidYMax"
  | "xMaxYMax";

interface CSSVariableInterpolation {
  property: string;
  from: number | string;
  to: number | string;
}

type PreserveAspectRatioMeetOrSlice = "meet" | "slice";

type PreserveAspectRatio =
  | PreserveAspectRatioAlign
  | `${Exclude<PreserveAspectRatioAlign, "none">} ${PreserveAspectRatioMeetOrSlice}`;

interface MarqueeAlongSvgPathProps {
  children: React.ReactNode;
  className?: string;

  // Path properties
  path: string;
  pathId?: string;
  preserveAspectRatio?: PreserveAspectRatio;
  showPath?: boolean;

  // SVG properties
  width?: string | number;
  height?: string | number;
  viewBox?: string;

  // Marquee properties
  baseVelocity?: number;
  direction?: "normal" | "reverse";
  easing?: (value: number) => number;
  slowdownOnHover?: boolean;
  slowDownFactor?: number;
  slowDownSpringConfig?: SpringOptions;

  // Scroll properties
  useScrollVelocity?: boolean;
  scrollAwareDirection?: boolean;
  scrollSpringConfig?: SpringOptions;
  scrollContainer?: RefObject<HTMLElement | null> | HTMLElement | null;

  // Item repetition
  repeat?: number;

  // Drag properties
  draggable?: boolean;
  dragSensitivity?: number;
  dragVelocityDecay?: number;
  dragAwareDirection?: boolean;
  grabCursor?: boolean;

  // Z-index properties
  enableRollingZIndex?: boolean;
  zIndexBase?: number;
  zIndexRange?: number;

  cssVariableInterpolation?: CSSVariableInterpolation[];

  // Responsive properties
  responsive?: boolean;
}

/**
 * One item riding the path.
 *
 * Extracted into its own component on purpose: the upstream snippet calls
 * useTransform/useMotionValue/useEffect inside `items.map()`, which breaks the
 * Rules of Hooks — the hook order shifts the moment `repeat` or the child count
 * changes, and React throws. A component per item makes each hook call sit at
 * the top level of its own render, so the list can resize freely.
 */
function MarqueeItem({
  child,
  itemIndex,
  itemCount,
  baseOffset,
  path,
  easing,
  calculateZIndex,
  enableRollingZIndex,
  cssVariableInterpolation,
  draggable,
  grabCursor,
  ariaHidden,
  onHoverChange,
}: {
  child: React.ReactNode;
  itemIndex: number;
  itemCount: number;
  baseOffset: MotionValue<number>;
  path: string;
  easing?: (value: number) => number;
  calculateZIndex: (offsetDistance: number) => number | undefined;
  enableRollingZIndex: boolean;
  cssVariableInterpolation: CSSVariableInterpolation[];
  draggable: boolean;
  grabCursor: boolean;
  ariaHidden: boolean;
  onHoverChange: (hovered: boolean) => void;
}) {
  const itemOffset = useTransform(baseOffset, (v: number) => {
    const position = (itemIndex * 100) / itemCount;
    const wrappedValue = wrap(0, 100, v + position);
    return `${easing ? easing(wrappedValue / 100) * 100 : wrappedValue}%`;
  });

  const currentOffsetDistance = useMotionValue(0);

  const zIndex = useTransform(currentOffsetDistance, (value: number) =>
    calculateZIndex(value),
  );

  useEffect(() => {
    const unsubscribe = itemOffset.on("change", (value: string) => {
      const match = value.match(/^([\d.]+)%$/);
      if (match && match[1]) {
        currentOffsetDistance.set(parseFloat(match[1]));
      }
    });
    return unsubscribe;
  }, [itemOffset, currentOffsetDistance]);

  // Hooks may not run in a loop, so the interpolation list is capped and each
  // slot gets its own unconditional hook call.
  const v0 = useTransform(
    currentOffsetDistance,
    [0, 100],
    [cssVariableInterpolation[0]?.from ?? 0, cssVariableInterpolation[0]?.to ?? 0],
  );
  const v1 = useTransform(
    currentOffsetDistance,
    [0, 100],
    [cssVariableInterpolation[1]?.from ?? 0, cssVariableInterpolation[1]?.to ?? 0],
  );
  const v2 = useTransform(
    currentOffsetDistance,
    [0, 100],
    [cssVariableInterpolation[2]?.from ?? 0, cssVariableInterpolation[2]?.to ?? 0],
  );

  const cssVariables: Record<string, MotionValue<string | number>> = {};
  [v0, v1, v2].forEach((mv, i) => {
    const spec = cssVariableInterpolation[i];
    if (spec) cssVariables[spec.property] = mv;
  });

  return (
    <motion.div
      className={cn("mq-item", draggable && grabCursor && "mq-grab")}
      style={{
        offsetPath: `path('${path}')`,
        offsetDistance: itemOffset,
        zIndex: enableRollingZIndex ? zIndex : undefined,
        willChange: "offset-distance",
        backfaceVisibility: "hidden",
        ...cssVariables,
      }}
      aria-hidden={ariaHidden}
      onMouseEnter={() => onHoverChange(true)}
      onMouseLeave={() => onHoverChange(false)}
    >
      {child}
    </motion.div>
  );
}

const MarqueeAlongSvgPath = ({
  children,
  className,

  // Path defaults
  path,
  pathId,
  preserveAspectRatio = "xMidYMid meet",
  showPath = false,

  // SVG defaults
  width = "100%",
  height = "100%",
  viewBox = "0 0 100 100",

  // Marquee defaults
  baseVelocity = 5,
  direction = "normal",
  easing,
  slowdownOnHover = false,
  slowDownFactor = 0.3,
  slowDownSpringConfig = { damping: 50, stiffness: 400 },

  // Scroll defaults
  useScrollVelocity = false,
  scrollAwareDirection = false,
  scrollSpringConfig = { damping: 50, stiffness: 400 },
  scrollContainer,

  // Items repetition
  repeat = 3,

  // Drag defaults
  draggable = false,
  dragSensitivity = 0.2,
  dragVelocityDecay = 0.96,
  dragAwareDirection = false,
  grabCursor = false,

  // Z-index defaults
  enableRollingZIndex = true,
  zIndexBase = 1,
  zIndexRange = 10,

  cssVariableInterpolation = [],

  // Responsive defaults
  responsive = false,
}: MarqueeAlongSvgPathProps) => {
  const container = useRef<HTMLDivElement>(null);
  const marqueeContainerRef = useRef<HTMLDivElement>(null);
  const baseOffset = useMotionValue(0);
  const pathRef = useRef<SVGPathElement>(null);

  // Responsive scaling using direct DOM manipulation (no re-renders)
  useEffect(() => {
    if (!responsive) return;

    const [, , vbWidth, vbHeight] = viewBox.split(" ").map(Number);
    const originalWidth = vbWidth || 100;
    const originalHeight = vbHeight || 100;

    const updateScale = () => {
      const wrapper = container.current;
      const marqueeContainer = marqueeContainerRef.current;
      if (!wrapper || !marqueeContainer) return;

      const wrapperWidth = wrapper.clientWidth;
      const wrapperHeight = wrapper.clientHeight;

      const scale = Math.min(wrapperWidth / originalWidth, wrapperHeight / originalHeight);

      const offsetX = (wrapperWidth - originalWidth * scale) / 2;
      const offsetY = (wrapperHeight - originalHeight * scale) / 2;

      marqueeContainer.style.width = `${originalWidth}px`;
      marqueeContainer.style.height = `${originalHeight}px`;
      marqueeContainer.style.transform = `translate(${offsetX}px, ${offsetY}px) scale(${scale})`;
      marqueeContainer.style.transformOrigin = "top left";
    };

    updateScale();
    window.addEventListener("resize", updateScale);
    return () => window.removeEventListener("resize", updateScale);
  }, [responsive, viewBox]);

  const items = React.useMemo(() => {
    const childrenArray = React.Children.toArray(children);
    return childrenArray.flatMap((child, childIndex) =>
      Array.from({ length: repeat }, (_, repeatIndex) => ({
        child,
        childIndex,
        repeatIndex,
        itemIndex: repeatIndex * childrenArray.length + childIndex,
        key: `${childIndex}-${repeatIndex}`,
      })),
    );
  }, [children, repeat]);

  const calculateZIndex = useCallback(
    (offsetDistance: number) => {
      if (!enableRollingZIndex) return undefined;
      return Math.floor(zIndexBase + (offsetDistance / 100) * zIndexRange);
    },
    [enableRollingZIndex, zIndexBase, zIndexRange],
  );

  const id = pathId || `marquee-path-${React.useId().replace(/:/g, "")}`;

  const { scrollY } = useScroll({
    container: (scrollContainer as RefObject<HTMLDivElement | null>) || container,
  });

  const scrollVelocity = useVelocity(scrollY);
  const smoothVelocity = useSpring(scrollVelocity, scrollSpringConfig);

  const isHovered = useRef(false);
  const isDragging = useRef(false);
  const dragVelocity = useRef(0);

  const directionFactor = useRef(direction === "normal" ? 1 : -1);

  const hoverFactorValue = useMotionValue(1);
  const defaultVelocity = useMotionValue(1);
  const smoothHoverFactor = useSpring(hoverFactorValue, slowDownSpringConfig);

  const velocityFactor = useTransform(
    useScrollVelocity ? smoothVelocity : defaultVelocity,
    [0, 1000],
    [0, 5],
    { clamp: false },
  );

  useAnimationFrame((_, delta) => {
    if (isDragging.current && draggable) {
      baseOffset.set(baseOffset.get() + dragVelocity.current);
      dragVelocity.current *= 0.9;
      if (Math.abs(dragVelocity.current) < 0.01) dragVelocity.current = 0;
      return;
    }

    hoverFactorValue.set(isHovered.current && slowdownOnHover ? slowDownFactor : 1);

    let moveBy =
      directionFactor.current * baseVelocity * (delta / 1000) * smoothHoverFactor.get();

    if (scrollAwareDirection && !isDragging.current) {
      if (velocityFactor.get() < 0) directionFactor.current = -1;
      else if (velocityFactor.get() > 0) directionFactor.current = 1;
    }

    moveBy += directionFactor.current * moveBy * velocityFactor.get();

    if (draggable) {
      moveBy += dragVelocity.current;

      if (dragAwareDirection && Math.abs(dragVelocity.current) > 0.1) {
        directionFactor.current = Math.sign(dragVelocity.current);
      }

      if (!isDragging.current && Math.abs(dragVelocity.current) > 0.01) {
        dragVelocity.current *= dragVelocityDecay;
      } else if (!isDragging.current) {
        dragVelocity.current = 0;
      }
    }

    baseOffset.set(baseOffset.get() + moveBy);
  });

  const lastPointerPosition = useRef({ x: 0, y: 0 });

  const handlePointerDown = (e: React.PointerEvent) => {
    if (!draggable) return;
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    if (grabCursor) (e.currentTarget as HTMLElement).style.cursor = "grabbing";
    isDragging.current = true;
    lastPointerPosition.current = { x: e.clientX, y: e.clientY };
    dragVelocity.current = 0;
  };

  const handlePointerMove = (e: React.PointerEvent) => {
    if (!draggable || !isDragging.current) return;
    const deltaX = e.clientX - lastPointerPosition.current.x;
    const deltaY = e.clientY - lastPointerPosition.current.y;
    const delta = Math.sqrt(deltaX * deltaX + deltaY * deltaY);
    dragVelocity.current = (deltaX > 0 ? delta : -delta) * dragSensitivity;
    lastPointerPosition.current = { x: e.clientX, y: e.clientY };
  };

  const handlePointerUp = (e: React.PointerEvent) => {
    if (!draggable) return;
    (e.currentTarget as HTMLElement).releasePointerCapture(e.pointerId);
    isDragging.current = false;
    if (grabCursor) (e.currentTarget as HTMLElement).style.cursor = "grab";
  };

  const setHovered = useCallback((v: boolean) => {
    isHovered.current = v;
  }, []);

  return (
    <div
      ref={container}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerCancel={handlePointerUp}
      className={cn("mq-root", className)}
    >
      <div ref={marqueeContainerRef} className="mq-stage" style={{ contain: "layout style" }}>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width={width}
          height={height}
          viewBox={viewBox}
          preserveAspectRatio={preserveAspectRatio}
          className="mq-svg"
        >
          <path
            id={id}
            d={path}
            stroke={showPath ? "currentColor" : "none"}
            fill="none"
            ref={pathRef}
          />
        </svg>

        {items.map(({ child, repeatIndex, itemIndex, key }) => (
          <MarqueeItem
            key={key}
            child={child}
            itemIndex={itemIndex}
            itemCount={items.length}
            baseOffset={baseOffset}
            path={path}
            easing={easing}
            calculateZIndex={calculateZIndex}
            enableRollingZIndex={enableRollingZIndex}
            cssVariableInterpolation={cssVariableInterpolation}
            draggable={draggable}
            grabCursor={grabCursor}
            ariaHidden={repeatIndex > 0}
            onHoverChange={setHovered}
          />
        ))}
      </div>
    </div>
  );
};

export default MarqueeAlongSvgPath;
