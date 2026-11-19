/**
 * Original illustration for the dashboard "Report Cybercrime" banner (Step 5 reference):
 * a hooded Cyber Warrior at a laptop carrying a shield, in front of a faint city skyline,
 * with circuit traces and floating security icons. Drawn for CyberRakshak - no copied
 * artwork. The figure wears a glowing visor rather than a mask: the banner is about
 * defenders reporting cybercrime, not attackers.
 *
 * Inline SVG: scales with its container, follows the site palette, nothing to cache.
 * Decorative only (aria-hidden) - the banner's heading and button carry the meaning.
 */
export function WarriorCtaIllustration({className}: {className?: string}) {
  return (
    <svg aria-hidden="true" className={className} focusable="false" preserveAspectRatio="xMidYMid meet" viewBox="0 0 320 200" xmlns="http://www.w3.org/2000/svg">
      {/* city skyline */}
      <g fill="#d7e7f7">
        <rect height="62" rx="2" width="20" x="10" y="122" />
        <rect height="88" rx="2" width="16" x="34" y="96" />
        <rect height="52" rx="2" width="22" x="54" y="132" />
        <rect height="104" rx="2" width="14" x="80" y="80" />
        <rect height="70" rx="2" width="18" x="232" y="114" />
        <rect height="96" rx="2" width="14" x="254" y="88" />
        <rect height="58" rx="2" width="20" x="272" y="126" />
        <rect height="80" rx="2" width="16" x="296" y="104" />
      </g>
      <g fill="#ffffff" opacity="0.9">
        <rect height="4" width="4" x="38" y="104" /><rect height="4" width="4" x="44" y="112" />
        <rect height="4" width="4" x="84" y="90" /><rect height="4" width="4" x="84" y="102" />
        <rect height="4" width="4" x="258" y="98" /><rect height="4" width="4" x="258" y="110" />
        <rect height="4" width="4" x="300" y="114" />
      </g>

      {/* circuit traces */}
      <g fill="none" stroke="#a9c8ea" strokeDasharray="3 4" strokeLinecap="round" strokeWidth="1.5">
        <path d="M60 46 H96 V70 H122" />
        <path d="M262 40 H228 V64 H200" />
        <path d="M44 150 H82 V130 H112" />
        <path d="M280 156 H244 V136 H210" />
      </g>
      <g fill="#7fb0e6">
        <circle cx="122" cy="70" r="2.5" /><circle cx="200" cy="64" r="2.5" />
        <circle cx="112" cy="130" r="2.5" /><circle cx="210" cy="136" r="2.5" />
      </g>

      {/* the Cyber Warrior: hood and shoulders */}
      <path d="M160 34c-26 0-42 21-42 46 0 9 2 17 6 24-20 7-32 20-36 40h144c-4-20-16-33-36-40 4-7 6-15 6-24 0-25-16-46-42-46z" fill="#0b2a5b" />
      <path d="M160 46c-18 0-30 15-30 34 0 17 13 32 30 32s30-15 30-32c0-19-12-34-30-34z" fill="#122f57" />
      {/* face in the hood's shadow, with a glowing visor */}
      <ellipse cx="160" cy="84" fill="#0a1a33" rx="22" ry="26" />
      <rect fill="#5fb0ff" height="9" rx="4.5" width="34" x="143" y="76" />
      <rect fill="#d6ecff" height="3" opacity="0.85" rx="1.5" width="14" x="147" y="78" />
      {/* hoodie drawstrings */}
      <path d="M152 108v14M168 108v14" stroke="#3a5d8f" strokeLinecap="round" strokeWidth="2" />

      {/* laptop */}
      <path d="M108 172h104l10 12H98z" fill="#1d3354" />
      <rect fill="#2a4672" height="50" rx="5" width="96" x="112" y="122" />
      <rect fill="#33568a" height="42" rx="3" width="88" x="116" y="126" />
      {/* shield emblem on the lid */}
      <path d="M160 133l14 5v9c0 9-6 15-14 18-8-3-14-9-14-18v-9z" fill="#ffffff" />
      <path d="M153 148l5 5 9-10" fill="none" stroke="#075fb9" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.6" />

      {/* floating security icons */}
      <g>
        <circle cx="96" cy="28" fill="#fff" r="15" stroke="#f4b4b4" strokeWidth="1.5" />
        <circle cx="96" cy="28" fill="none" r="8" stroke="#e04a4a" strokeWidth="2" />
        <path d="M96 24v5" stroke="#e04a4a" strokeLinecap="round" strokeWidth="2.2" /><circle cx="96" cy="32" fill="#e04a4a" r="1.3" />
      </g>
      <g>
        <circle cx="228" cy="26" fill="#fff" r="15" stroke="#bcd5ef" strokeWidth="1.5" />
        <rect fill="none" height="10" rx="2" stroke="#075fb9" strokeWidth="2" width="13" x="221.5" y="26" />
        <path d="M224.5 26v-3a3.5 3.5 0 0 1 7 0v3" fill="none" stroke="#075fb9" strokeWidth="2" />
      </g>
      <g>
        <circle cx="66" cy="92" fill="#fff" r="14" stroke="#bcd5ef" strokeWidth="1.5" />
        <rect fill="none" height="10" rx="1.5" stroke="#075fb9" strokeWidth="2" width="14" x="59" y="87" />
        <path d="M59.5 88l6.5 5 6.5-5" fill="none" stroke="#075fb9" strokeWidth="2" />
      </g>
      <g>
        <circle cx="258" cy="92" fill="#fff" r="14" stroke="#bcd5ef" strokeWidth="1.5" />
        <circle cx="258" cy="92" fill="none" r="7" stroke="#075fb9" strokeWidth="2" />
        <path d="M251 92h14M258 85c-3 4-3 10 0 14M258 85c3 4 3 10 0 14" fill="none" stroke="#075fb9" strokeWidth="1.6" />
      </g>
      <g>
        <circle cx="80" cy="158" fill="#fff" r="13" stroke="#bcd5ef" strokeWidth="1.5" />
        <circle cx="80" cy="154" fill="none" r="3.5" stroke="#075fb9" strokeWidth="2" />
        <path d="M73.5 165a6.5 6.5 0 0 1 13 0" fill="none" stroke="#075fb9" strokeWidth="2" />
      </g>
    </svg>
  );
}
