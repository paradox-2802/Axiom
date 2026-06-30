import { createElement } from "react";

/** Shared typography primitives — use type-* classes from index.css where possible. */

export function HeroTitle({ as = "h1", className = "", children }) {
  return createElement(as, { className: `type-hero ${className}` }, children);
}

export function Title({ as = "h2", className = "", children }) {
  return createElement(as, { className: `type-title ${className}` }, children);
}

export function SectionTitle({ as = "h3", className = "", children }) {
  return createElement(as, { className: `type-section ${className}` }, children);
}

export function Lead({ className = "", children }) {
  return <p className={`type-lead ${className}`}>{children}</p>;
}

export function Body({ className = "", children }) {
  return <p className={`type-body ${className}`}>{children}</p>;
}

export function Caption({ className = "", children }) {
  return <p className={`type-caption ${className}`}>{children}</p>;
}

export function Label({ className = "", children, htmlFor }) {
  return (
    <label htmlFor={htmlFor} className={`type-label ${className}`}>
      {children}
    </label>
  );
}

export function Overline({ className = "", children }) {
  return <p className={`type-overline ${className}`}>{children}</p>;
}
