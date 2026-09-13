import type {Metadata} from "next";
import {Barlow_Condensed, Fraunces, Inter, Noto_Sans_Devanagari, Space_Grotesk} from "next/font/google";
import {hasLocale, NextIntlClientProvider} from "next-intl";
import {getTranslations, setRequestLocale} from "next-intl/server";
import {notFound} from "next/navigation";

import {ProductShell} from "@/components/layout/ProductShell";
import {routing} from "@/lib/i18n/routing";

// Inter carries the reading. It has a tall x-height and open apertures, which is
// what keeps small text legible for an older reader on a phone - the single
// constraint this portal cannot trade away.
//
// Space Grotesk is used only at heading sizes. It has enough character to stop the
// page looking like a bootstrap template - slightly squared bowls, a distinctive
// "y" and "g" - without the legibility cost of a display face. A pixel face was
// tried here and abandoned: it looks the part on a designer's screen and fails the
// person this service exists for.
//
// Devanagari has no equivalent worth setting a portal in, so Hindi runs in Noto
// Sans Devanagari throughout.
const sans = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-sans",
  weight: ["400", "500", "600", "700", "800"]
});

const display = Space_Grotesk({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-display",
  weight: ["500", "600", "700"]
});

const devanagari = Noto_Sans_Devanagari({
  subsets: ["devanagari"],
  display: "swap",
  variable: "--font-devanagari",
  weight: ["400", "500", "600", "700"]
});

// The warm retro display serif - the "East Kind" reference. Fraunces is the one
// free family with axes built for this exact look: SOFT rounds the serifs and
// terminals off, WONK swaps in the slightly irregular italic-ish forms. Pushed
// to the top of both axes it stops reading as a workhorse serif and starts
// reading as a 1970s display face.
const poster = Fraunces({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-poster",
  axes: ["SOFT", "WONK", "opsz"]
});

// The condensed face, standing in for Calama: tall, narrow, and at home in caps.
// It carries labels, tags, eyebrows and buttons - the short strings where
// condensed type saves width and looks deliberate rather than cramped.
const condensed = Barlow_Condensed({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-condensed",
  weight: ["500", "600", "700"]
});

type LocaleLayoutProps = Readonly<{children: React.ReactNode; params: Promise<{locale: string}>;}>;
export function generateStaticParams() { return routing.locales.map((locale) => ({locale})); }
export async function generateMetadata({params}: Pick<LocaleLayoutProps, "params">): Promise<Metadata> {
  const {locale} = await params;
  if (!hasLocale(routing.locales, locale)) return {};
  const t = await getTranslations({locale, namespace: "common"});
  return {title: t("projectName"), description: t("foundationMessage")};
}
export default async function LocaleLayout({children, params}: LocaleLayoutProps) {
  const {locale} = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  setRequestLocale(locale);
  return (
    <html className={`${sans.variable} ${display.variable} ${devanagari.variable} ${poster.variable} ${condensed.variable}`} lang={locale}>
      <body><NextIntlClientProvider><ProductShell>{children}</ProductShell></NextIntlClientProvider></body>
    </html>
  );
}
