const SIZES = {
  xs: 28,
  sm: 32,
  md: 40,
  lg: 48,
  xl: 56,
};

/** Claude-style 8-ray starburst, rendered in brand indigo. */
const BURST_ANGLES = [0, 45, 90, 135, 180, 225, 270, 315];

export function LogoMark({ size = "sm", className = "" }) {
  const px = typeof size === "number" ? size : SIZES[size] || SIZES.sm;

  return (
    <svg
      width={px}
      height={px}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={`text-brand-600 dark:text-brand-400 flex-shrink-0 ${className}`}
      aria-hidden="true"
    >
      <g fill="currentColor">
        {BURST_ANGLES.map((angle) => (
          <ellipse
            key={angle}
            cx="12"
            cy="6.15"
            rx="2.05"
            ry="4.85"
            transform={`rotate(${angle} 12 12)`}
          />
        ))}
      </g>
    </svg>
  );
}

export default function Logo({ size = "sm", showWordmark = true, subtitle, className = "" }) {
  return (
    <div className={`flex items-center gap-2.5 min-w-0 ${className}`}>
      <LogoMark size={size} />
      {showWordmark && (
        <div className="min-w-0">
          <p className="font-display font-bold text-brand-600 dark:text-brand-400 text-lg leading-tight tracking-tight">
            Axiom
          </p>
          {subtitle && (
            <p className="type-overline leading-none mt-0.5">
              {subtitle}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
