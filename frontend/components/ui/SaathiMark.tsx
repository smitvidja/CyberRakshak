import type {SVGProps} from "react";

/**
 * Cyber Saathi's mark.
 *
 * Three things have to be true at once: it is a companion ("saathi"), it is
 * there to help you REPORT something, and it is an assistant rather than a
 * person. The first attempt nested a speech bubble inside a shield, which read
 * as two clip-art pieces stacked rather than as one idea.
 *
 * So this is a single silhouette doing both jobs: a speech bubble whose sides
 * sweep down to a point, which is also the outline of a shield. Talking to it IS
 * the protection - that is the whole proposition of the product, in one shape.
 *
 * Inside are two message lines of unequal length: something said, something
 * answered. The four-point spark outside the top-right corner is the only
 * "assistant" signal, kept small and off the main shape so it decorates rather
 * than competes.
 *
 * Drawn in the same hand as the rest of the page: open joints, sides that do not
 * quite agree, a lighter weight for interior detail.
 */
export function SaathiMark({size = 30, strokeWidth = 2, ...rest}: Omit<SVGProps<SVGSVGElement>, "children" | "viewBox"> & {size?: number; strokeWidth?: number}) {
  const detail = Number(strokeWidth) * 0.8;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      aria-hidden="true"
      focusable="false"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      {...rest}
    >
      {/* bubble and shield, one outline */}
      <path d="M9.6 11.4c9.5-1.4 19.2-1.4 28.8-.2.7 5.9.8 11.3.2 16.3-.6 5.2-3.3 9.3-8.2 12.7-2 1.4-4.1 2.6-6.3 3.6-2.3-1-4.5-2.3-6.6-3.8-4.7-3.5-7.3-7.6-7.8-12.6-.5-5-.4-10.3.9-16Z" />
      {/* what you said, and what came back */}
      <path d="M16.8 20.9c4.9-.6 9.9-.6 14.8.1" strokeWidth={detail} />
      <path d="M17 26.7c3.4-.4 6.8-.4 10.1.1" strokeWidth={detail} />
      {/* the assistant, kept to a spark in the corner */}
      <path d="M40.6 7.6c.5 2.1 1.2 3.5 2.2 4.3-1.1.7-1.8 2-2.2 4-.4-2-1.1-3.3-2.2-4 1.1-.8 1.8-2.2 2.2-4.3Z" strokeWidth={detail} />
    </svg>
  );
}
