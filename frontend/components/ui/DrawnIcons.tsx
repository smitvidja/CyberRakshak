import type {SVGProps} from "react";

/**
 * Hand-drawn replacements for the Lucide icons on the home page.
 *
 * These are drop-in: same call shape as Lucide (`size`, `strokeWidth`), so the
 * page swaps an import and nothing else.
 *
 * Drawing character at 17-24px is a different problem from drawing character at
 * 300px. A wobbly bezier that reads as "drawn by hand" in a hero illustration
 * just reads as "badly aligned" on a 22px icon - the wobble is smaller than the
 * stroke. What actually survives at this size is:
 *
 *   - OPEN JOINTS: corners that do not meet, the way a pen lifts early;
 *   - OVERSHOOT: a line that carries a pixel or two past the corner;
 *   - UNEQUAL PAIRS: two sides of a "symmetrical" shape that disagree slightly;
 *   - a single detail stroke at a lighter weight, standing in for pen pressure.
 *
 * So every icon below is built from those, not from noise added to a circle.
 */

type IconProps = Omit<SVGProps<SVGSVGElement>, "children" | "viewBox"> & {
  size?: number;
  strokeWidth?: number;
};

function Drawn({size = 22, strokeWidth = 1.7, children, ...rest}: IconProps & {children: React.ReactNode}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      {...rest}
    >
      {children}
    </svg>
  );
}

/** Be a Cyber Warrior: a person, with a small shield held at their side. */
export function DrawnWarrior(props: IconProps) {
  return (
    <Drawn {...props}>
      <path d="M9.6 4.6c2 .1 3.3 1.5 3.2 3.3-.1 1.7-1.5 2.9-3.3 2.8C7.8 10.6 6.6 9.3 6.7 7.5 6.8 5.9 8 4.6 9.6 4.6Z" />
      <path d="M3.9 19.4c.3-3.2 2.5-5.3 5.6-5.4 1.6 0 3 .5 4 1.5" />
      <path d="M16.9 12.2c1.5.4 2.9.9 4.3 1.5-.1 1.6-.1 3-.3 4.3-.2 1.4-1.3 2.4-3.8 3.2-2.3-1-3.4-2.1-3.6-3.4-.2-1.3-.2-2.7-.1-4.2 1.1-.6 2.3-1 3.5-1.4Z" strokeWidth={1.5} />
    </Drawn>
  );
}

/** Stay Alert: a bell, with the clapper and two ring-ticks. */
export function DrawnBell(props: IconProps) {
  return (
    <Drawn {...props}>
      <path d="M6.2 17c1.3-1.7 1.8-3.8 1.7-6.3C7.8 8.1 9.4 6.3 12 6.3c2.6 0 4.2 1.8 4.1 4.4-.1 2.5.4 4.6 1.7 6.3-3.9.8-7.6.8-11.6 0Z" />
      <path d="M10.1 19.1c.4 1.3 3 1.4 3.6 0" strokeWidth={1.5} />
      <path d="M12 6.3V4" strokeWidth={1.5} />
      <path d="M3.5 9.6c.2-1.4.8-2.6 1.8-3.5M20.5 9.4c-.3-1.4-.9-2.5-1.9-3.4" strokeWidth={1.4} />
    </Drawn>
  );
}

/** Secure India: a shield the pen closed a little past its own start, with a tick. */
export function DrawnShield(props: IconProps) {
  return (
    <Drawn {...props}>
      <path d="M12 3.2c2.7.8 5.2 1.7 7.6 2.8-.1 2.8-.2 5.3-.5 7.5-.4 2.5-2.3 4.3-6.9 6.3-4.4-2-6.4-3.8-6.9-6.2-.4-2.2-.5-4.7-.5-7.5C7.1 4.9 9.5 4 12 3.2Z" />
      <path d="M8.9 11.9c.9 1 1.7 1.8 2.5 2.5 1.6-1.9 3.1-3.5 4.6-5" strokeWidth={1.6} />
    </Drawn>
  );
}

/** Track Your Complaint: a clipboard, its clip drawn as a separate stroke. */
export function DrawnClipboard(props: IconProps) {
  return (
    <Drawn {...props}>
      <path d="M6.3 4.6c3.9-.4 7.7-.4 11.5 0 .4 4.9.4 9.9 0 14.8-3.9.4-7.7.4-11.6 0-.4-4.9-.4-9.8.1-14.8Z" />
      <path d="M9.6 4.7c-.1-1 0-1.7.4-2 .6-.4 3.4-.4 4 0 .4.3.5 1 .4 2-1.6.2-3.2.2-4.8 0Z" strokeWidth={1.5} />
      <path d="M9.1 12.3c.9.9 1.6 1.6 2.2 2.2 1.3-1.6 2.5-2.9 3.7-4.1" strokeWidth={1.5} />
    </Drawn>
  );
}

/** Beware of fake calls: a handset, tilted, with two ring arcs. */
export function DrawnPhone(props: IconProps) {
  return (
    <Drawn {...props}>
      <path d="M5.2 5.1c.8-.9 1.8-1.3 2.4-.8.9.7 1.6 1.7 2.1 2.8.2.6-.1 1.1-.9 1.7-.5.4-.6.9-.2 1.7.9 1.9 2.3 3.3 4.2 4.2.8.4 1.3.3 1.7-.2.6-.8 1.1-1.1 1.7-.9 1.1.5 2.1 1.2 2.8 2.1.5.6.1 1.6-.8 2.4-1 .9-2.2 1.1-3.8.5-3-1.1-5.4-2.8-7.2-5.1C5 11.5 4.2 9.6 4.3 7.8c0-1 .3-1.9.9-2.7Z" />
      <path d="M14.9 4.4c1.2.2 2.2 1 2.6 2.1M14.4 1.9c2.4.4 4.3 2.2 5 4.6" strokeWidth={1.4} />
    </Drawn>
  );
}

/** New safety advisory: a megaphone, cone and body drawn as separate strokes. */
export function DrawnMegaphone(props: IconProps) {
  return (
    <Drawn {...props}>
      <path d="M19.4 5.1c.4 4.5.4 8.9 0 13.3-4.3-2.4-8.3-4-12.1-4.7-.3-1.3-.3-2.6 0-3.9 3.9-.8 7.9-2.3 12.1-4.7Z" />
      <path d="M7.3 9.8c-1.2.1-2 .3-2.4.8-.6.7-.6 2.3 0 3 .4.5 1.2.8 2.4.9" strokeWidth={1.5} />
      <path d="M9.4 14.3c.2 2.2.7 4 1.4 5.4.9.4 1.9.4 2.8 0-.5-1.6-.9-3.5-1.1-5.7" strokeWidth={1.5} />
    </Drawn>
  );
}

/** Cyber security tips: a bulb, with two base lines and three rays. */
export function DrawnBulb(props: IconProps) {
  return (
    <Drawn {...props}>
      <path d="M12 3.4c3.4 0 5.9 2.4 5.9 5.5 0 2-.9 3.3-2.1 4.6-.7.8-1 1.6-1 2.6-1.9.3-3.7.3-5.6 0 0-1-.3-1.8-1-2.6C6.9 12.2 6 10.9 6.1 8.9c0-3.1 2.5-5.5 5.9-5.5Z" />
      <path d="M9.5 18.4c1.7.3 3.4.3 5.1 0M10.3 20.7c1.1.2 2.3.2 3.4 0" strokeWidth={1.4} />
      <path d="M12 1.4V.6M3.7 4.2 3 3.6M20.3 4.1l.7-.6" strokeWidth={1.3} />
    </Drawn>
  );
}

/** Learning Corner: a mortarboard, with the tassel hanging off the right corner. */
export function DrawnCap(props: IconProps) {
  return (
    <Drawn {...props}>
      <path d="M12 4.2c3.6 1.2 7 2.5 10.3 4-3.3 1.6-6.7 2.9-10.2 4-3.6-1-7-2.3-10.4-4 3.4-1.6 6.8-2.9 10.3-4Z" />
      <path d="M5.9 10.2c-.2 2-.2 3.6 0 4.9 3.9 1.8 8 1.8 12.1.1.3-1.4.3-3.1.1-5" strokeWidth={1.5} />
      <path d="M21.6 8.6c.4 2.2.5 4.2.3 6" strokeWidth={1.4} />
    </Drawn>
  );
}
