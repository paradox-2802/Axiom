import { motion, useReducedMotion } from "framer-motion";
import { subtitleDelay } from "./heroTiming";

const EASE = [0.22, 0.61, 0.36, 1];

/** Heading: slow letter-by-letter */
const LETTER_MS = 52;
const LETTER_REVEAL_DURATION = 0.42;

/** Subheading: quick block fade */
const SUBTITLE_REVEAL_DURATION = 0.38;

const HEADING_PARTS = [
  { text: "Financial document ", className: "text-slate-900 dark:text-slate-100" },
  { text: "intelligence", className: "text-brand-600 dark:text-brand-400" },
];

const HEADING_ARIA_LABEL = "Financial document intelligence";

const letterHidden = { opacity: 0, filter: "blur(8px)", y: 8 };
const letterVisible = { opacity: 1, filter: "blur(0px)", y: 0 };

function buildHeadingLetters() {
  const letters = [];
  for (const part of HEADING_PARTS) {
    for (const char of part.text) {
      letters.push({ char, className: part.className });
    }
  }
  return letters;
}

const HEADING_LETTERS = buildHeadingLetters();

function RevealLetter({ char, delay, className }) {
  const reduceMotion = useReducedMotion();
  const display = char === " " ? "\u00A0" : char;

  if (reduceMotion) {
    return <span className={className}>{display}</span>;
  }

  return (
    <motion.span
      initial={letterHidden}
      animate={letterVisible}
      transition={{ duration: LETTER_REVEAL_DURATION, delay, ease: EASE }}
      className={`inline will-change-[transform,opacity,filter] ${className || ""}`}
    >
      {display}
    </motion.span>
  );
}

function RevealHeadingLetters({ className = "" }) {
  const reduceMotion = useReducedMotion();

  if (reduceMotion) {
    return (
      <span className={className} aria-label={HEADING_ARIA_LABEL}>
        {HEADING_PARTS.map((part) => (
          <span key={part.text} className={part.className}>
            {part.text}
          </span>
        ))}
      </span>
    );
  }

  return (
    <span className={className} aria-label={HEADING_ARIA_LABEL}>
      {HEADING_LETTERS.map((item, i) => (
        <RevealLetter
          key={`${item.char}-${i}`}
          char={item.char}
          delay={i * (LETTER_MS / 1000)}
          className={item.className}
        />
      ))}
    </span>
  );
}

function RevealSubtitle({ text, delay, className = "" }) {
  const reduceMotion = useReducedMotion();

  if (reduceMotion) {
    return <p className={className}>{text}</p>;
  }

  return (
    <motion.p
      initial={{ opacity: 0, filter: "blur(6px)", y: 6 }}
      animate={{ opacity: 1, filter: "blur(0px)", y: 0 }}
      transition={{ duration: SUBTITLE_REVEAL_DURATION, delay, ease: EASE }}
      className={`will-change-[transform,opacity,filter] ${className}`}
    >
      {text}
    </motion.p>
  );
}

/** Hero heading (slow letter reveal) + subheading (fast block reveal). */
export function HeroReveal({ className = "" }) {
  const reduceMotion = useReducedMotion();
  const subtitle =
    "Upload a report, ask questions, and extract executive summaries and risk analysis — grounded in your document.";

  return (
    <div className={`flex flex-col items-center gap-3 sm:gap-3.5 ${className}`}>
      <h1 className="type-hero text-center">
        <RevealHeadingLetters />
      </h1>
      <RevealSubtitle
        text={subtitle}
        delay={subtitleDelay(reduceMotion)}
        className="type-lead text-slate-500 dark:text-slate-400 max-w-md mx-auto text-center"
      />
    </div>
  );
}
