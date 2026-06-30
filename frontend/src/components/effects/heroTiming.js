const LETTER_MS = 52;
const LETTER_REVEAL_DURATION = 0.42;
const SUBTITLE_DELAY_AFTER_HEADING = 0.14;
const SUBTITLE_REVEAL_DURATION = 0.38;
const HEADING_LETTER_COUNT = "Financial document intelligence".length;

function headingEndDelay(reduceMotion = false) {
  if (reduceMotion) return 0;
  const lastLetterStart = (HEADING_LETTER_COUNT - 1) * (LETTER_MS / 1000);
  return lastLetterStart + LETTER_REVEAL_DURATION + SUBTITLE_DELAY_AFTER_HEADING;
}

/** When the hero CTA should appear (after subheading finishes). */
export function heroCtaDelay(reduceMotion = false) {
  if (reduceMotion) return 0.15;
  return headingEndDelay(false) + SUBTITLE_REVEAL_DURATION + 0.08;
}

export function subtitleDelay(reduceMotion = false) {
  return headingEndDelay(reduceMotion);
}
