"use client";

import Image from "next/image";
import Link from "next/link";
import {useLocale, useTranslations} from "next-intl";
import {usePathname} from "next/navigation";
import {PhoneCall} from "lucide-react";
import {useEffect, useLayoutEffect, useState, type ReactNode} from "react";

import {getReportCategoryHint} from "@/lib/auth/citizen-session";
import {routing} from "@/lib/i18n/routing";

// A plain useEffect runs *after* the browser paints, so the "generic" fallback text
// is visibly rendered for one frame before the real category swaps in - exactly the
// wrong-text flash reported against this callout. useLayoutEffect runs synchronously
// before paint, which eliminates that. It cannot run during SSR (no DOM), so it must
// be swapped for a plain effect there - Next.js only executes effects in the browser
// anyway, but calling the real useLayoutEffect during the server-render pass still
// logs a warning, hence the guard.
const useIsomorphicLayoutEffect = typeof window !== "undefined" ? useLayoutEffect : useEffect;

// "A- A+" was rendered as a single plain <span> of static text - not a button, no
// click handler, nothing happened when someone tapped it. This makes it a real,
// working text-size control: two buttons that scale the whole page's root font
// size, clamped and persisted so the choice survives a reload.
const FONT_SCALE_KEY = "cyberrakshak.font-scale";
const FONT_SCALE_MIN = 90;
const FONT_SCALE_MAX = 130;
const FONT_SCALE_STEP = 10;
const FONT_SCALE_DEFAULT = 100;

// The 6 category keys used by the landing page's report cards (app/[locale]/page.tsx)
// and carried through the flow via ?category= then a sessionStorage hint. Any other
// value (or none - warrior reports, suspect reports, identity verification) falls
// back to "generic".
const HELPLINE_CATEGORIES = ["women", "financial", "identity", "harassment", "commerce", "other"] as const;
type HelplineCategory = (typeof HELPLINE_CATEGORIES)[number] | "generic";

type ProductShellProps = {children: ReactNode};

export function ProductShell({children}: ProductShellProps) {
  const t = useTranslations("shell");
  const locale = useLocale();
  const pathname = usePathname();
  const localeHref = (nextLocale: string) => {
    const parts = pathname.split("/");
    parts[1] = nextLocale;
    return parts.join("/") || "/" + nextLocale;
  };
  // "learn" pointed at /{locale}/resources, a route that has never existed (404) -
  // the only real resources page is under /cyber-warrior/resources.
  const navItems = [["home", "/" + locale], ["report", "/" + locale + "/report-crime"], ["track", "/" + locale + "/complaints/track"], ["suspects", "/" + locale + "/suspects/report"], ["warriors", "/" + locale + "/cyber-warrior"], ["learn", "/" + locale + "/cyber-warrior/resources"], ["contact", "/" + locale + "/contact"]] as const;
  const homeHref = "/" + locale;
  const dashboardHref = homeHref + "/report-crime/dashboard";
  const reportHref = homeHref + "/report-crime";
  const warriorHref = homeHref + "/cyber-warrior";
  const warriorDashboardHref = warriorHref + "/dashboard";
  const breadcrumbItems: Array<{href?: string; label: string}> = [{href: homeHref, label: t("nav.home")}];

  if (pathname !== homeHref) {
    if (pathname === dashboardHref) {
      breadcrumbItems.push({label: t("breadcrumbs.dashboard")});
    } else if (pathname === reportHref) {
      breadcrumbItems.push({label: t("nav.report")});
    } else if (pathname === reportHref + "/verify") {
      breadcrumbItems.push({href: reportHref, label: t("nav.report")}, {label: t("breadcrumbs.verifyIdentity")});
    } else if (pathname === reportHref + "/profile") {
      breadcrumbItems.push({href: dashboardHref, label: t("breadcrumbs.dashboard")}, {label: t("breadcrumbs.myProfile")});
    } else if (pathname.includes("/report-crime/") && pathname.endsWith("/people")) {
      const incidentHref = pathname.replace(/\/people$/, "/incident");
      breadcrumbItems.push({href: dashboardHref, label: t("breadcrumbs.dashboard")}, {href: incidentHref, label: t("breadcrumbs.reportIncident")}, {label: t("breadcrumbs.peopleInvolved")});
    } else if (pathname.includes("/report-crime/") && pathname.endsWith("/review")) {
      const incidentHref = pathname.replace(/\/review$/, "/incident");
      breadcrumbItems.push({href: dashboardHref, label: t("breadcrumbs.dashboard")}, {href: incidentHref, label: t("breadcrumbs.reportIncident")}, {label: t("breadcrumbs.reviewSubmit")});
    } else if (pathname.includes("/report-crime/") && pathname.endsWith("/incident")) {
      breadcrumbItems.push({href: dashboardHref, label: t("breadcrumbs.dashboard")}, {label: t("breadcrumbs.reportIncident")});
    } else if (pathname.startsWith(homeHref + "/complaints/submitted/")) {
      breadcrumbItems.push({href: dashboardHref, label: t("breadcrumbs.dashboard")}, {href: homeHref + "/complaints", label: t("breadcrumbs.myReports")}, {label: t("breadcrumbs.submitted")});
    } else if (pathname.startsWith(homeHref + "/complaints/track/")) {
      breadcrumbItems.push({href: dashboardHref, label: t("breadcrumbs.dashboard")}, {href: homeHref + "/complaints/track", label: t("breadcrumbs.trackReport")}, {label: t("breadcrumbs.reportDetails")});
    } else if (pathname === homeHref + "/complaints/track") {
      breadcrumbItems.push({href: dashboardHref, label: t("breadcrumbs.dashboard")}, {label: t("breadcrumbs.trackReport")});
    } else if (pathname === homeHref + "/complaints") {
      breadcrumbItems.push({href: dashboardHref, label: t("breadcrumbs.dashboard")}, {label: t("breadcrumbs.myReports")});
    } else if (pathname.startsWith(homeHref + "/suspects")) {
      breadcrumbItems.push({label: t("nav.suspects")});
    } else if (pathname === warriorHref) {
      breadcrumbItems.push({label: t("nav.warriors")});
    } else if (pathname === warriorHref + "/verify") {
      breadcrumbItems.push({href: warriorHref, label: t("nav.warriors")}, {label: t("breadcrumbs.warriorRegistration")});
    } else if (pathname === warriorHref + "/verify/profile") {
      breadcrumbItems.push({href: warriorHref, label: t("nav.warriors")}, {label: t("breadcrumbs.warriorProfileSetup")});
    } else if (pathname === warriorDashboardHref) {
      breadcrumbItems.push({label: t("breadcrumbs.warriorDashboard")});
    } else if (pathname === warriorHref + "/profile") {
      breadcrumbItems.push({href: warriorDashboardHref, label: t("breadcrumbs.warriorDashboard")}, {label: t("breadcrumbs.warriorProfile")});
    } else if (pathname.startsWith(warriorHref + "/apply")) {
      breadcrumbItems.push({href: warriorHref, label: t("nav.warriors")}, {href: warriorHref + "/apply/resume", label: t("breadcrumbs.warriorApplication")});
      if (pathname.endsWith("/resume")) breadcrumbItems.push({label: t("breadcrumbs.warriorResume")});
      else if (pathname.endsWith("/review")) breadcrumbItems.push({label: t("breadcrumbs.warriorReview")});
      else if (pathname.endsWith("/submitted")) breadcrumbItems.push({label: t("breadcrumbs.warriorSubmitted")});
    } else if (pathname === warriorHref + "/reports") {
      breadcrumbItems.push({href: warriorDashboardHref, label: t("breadcrumbs.warriorDashboard")}, {label: t("breadcrumbs.warriorMyReports")});
    } else if (pathname === warriorHref + "/reports/track") {
      breadcrumbItems.push({href: warriorDashboardHref, label: t("breadcrumbs.warriorDashboard")}, {label: t("breadcrumbs.warriorTrackReport")});
    } else if (pathname === warriorHref + "/reports/new") {
      breadcrumbItems.push({href: warriorDashboardHref, label: t("breadcrumbs.warriorDashboard")}, {label: t("breadcrumbs.warriorReportCybercrime")});
    } else if (pathname.endsWith("/submitted") && pathname.startsWith(warriorHref + "/reports/")) {
      breadcrumbItems.push({href: warriorDashboardHref, label: t("breadcrumbs.warriorDashboard")}, {href: warriorHref + "/reports/new", label: t("breadcrumbs.warriorReportCybercrime")}, {label: t("breadcrumbs.warriorReportSubmitted")});
    } else if (pathname.startsWith(warriorHref + "/reports/")) {
      breadcrumbItems.push({href: warriorDashboardHref, label: t("breadcrumbs.warriorDashboard")}, {href: warriorHref + "/reports", label: t("breadcrumbs.warriorMyReports")}, {label: t("breadcrumbs.warriorReportDetails")});
    } else if (pathname === warriorHref + "/leaderboard") {
      breadcrumbItems.push({href: warriorDashboardHref, label: t("breadcrumbs.warriorDashboard")}, {label: t("breadcrumbs.warriorLeaderboard")});
    } else if (pathname === warriorHref + "/badges") {
      breadcrumbItems.push({href: warriorDashboardHref, label: t("breadcrumbs.warriorDashboard")}, {label: t("breadcrumbs.warriorBadges")});
    } else if (pathname === warriorHref + "/resources") {
      breadcrumbItems.push({href: warriorDashboardHref, label: t("breadcrumbs.warriorDashboard")}, {label: t("breadcrumbs.warriorResources")});
    } else if (pathname.startsWith(warriorHref)) {
      breadcrumbItems.push({href: warriorHref, label: t("nav.warriors")}, {label: t("breadcrumbCurrent")});
    } else {
      breadcrumbItems.push({label: t("breadcrumbCurrent")});
    }
  }

  // Reporting and registration are exactly the moments someone may be mid-fraud and
  // needs the helpline immediately, so those routes get a prominent tappable callout
  // rather than only the small number in the header.
  const isReportingRoute = ["/report-crime", "/suspects/report", "/cyber-warrior/reports", "/verify"].some(
    (segment) => pathname.includes(segment)
  );

  // The category is only ever in the URL on the very first /report-crime?category=
  // pick screen - every step after that carries it via a sessionStorage hint (see
  // CitizenEntry.tsx), so both are checked, URL first since it's the freshest signal.
  const [fontScale, setFontScale] = useState(FONT_SCALE_DEFAULT);
  useIsomorphicLayoutEffect(() => {
    if (typeof window === "undefined") return;
    const stored = Number(window.localStorage.getItem(FONT_SCALE_KEY));
    const initial = stored >= FONT_SCALE_MIN && stored <= FONT_SCALE_MAX ? stored : FONT_SCALE_DEFAULT;
    setFontScale(initial);
    document.documentElement.style.fontSize = initial + "%";
  }, []);
  function adjustFontScale(direction: 1 | -1) {
    setFontScale((current) => {
      const next = Math.min(FONT_SCALE_MAX, Math.max(FONT_SCALE_MIN, current + direction * FONT_SCALE_STEP));
      document.documentElement.style.fontSize = next + "%";
      window.localStorage.setItem(FONT_SCALE_KEY, String(next));
      return next;
    });
  }

  const [helplineCategory, setHelplineCategory] = useState<HelplineCategory>("generic");
  useIsomorphicLayoutEffect(() => {
    if (typeof window === "undefined") return;
    const fromUrl = new URLSearchParams(window.location.search).get("category");
    const fromSession = getReportCategoryHint();
    const candidate = fromUrl ?? fromSession;
    setHelplineCategory(
      (HELPLINE_CATEGORIES as readonly string[]).includes(candidate ?? "") ? (candidate as HelplineCategory) : "generic"
    );
  }, [pathname]);

  return <div className="app-shell">
    <div className="utility-bar"><div className="shell-container utility-content"><span>{t("utilityNotice")}</span><div className="utility-actions">
      <span className="text-size-control">
        <button aria-label={t("decreaseTextSize")} disabled={fontScale <= FONT_SCALE_MIN} onClick={() => adjustFontScale(-1)} type="button">A-</button>
        <button aria-label={t("increaseTextSize")} disabled={fontScale >= FONT_SCALE_MAX} onClick={() => adjustFontScale(1)} type="button">A+</button>
      </span>
      <span aria-hidden="true">|</span>{routing.locales.map((nextLocale) => <Link className={nextLocale === locale ? "language-current" : ""} href={localeHref(nextLocale)} key={nextLocale}>{t("languages." + nextLocale)}</Link>)}</div></div></div>
    <header className="brand-header"><div className="shell-container brand-content"><Link className="brand-lockup" href={"/" + locale}><Image alt="" aria-hidden="true" className="brand-mark" height={44} priority src="/images/awareness/logo.webp" width={44} /><span><strong>{t("brandHindi")}</strong><small>{t("brandEnglish")}</small></span></Link><a className="brand-support" href={"tel:" + t("supportNumber")}><strong>{t("supportLabel")}</strong><span><PhoneCall aria-hidden="true" size={17} />{t("supportNumber")}</span></a></div></header>
    <nav className="primary-nav" aria-label={t("primaryNavigation")}><div className="shell-container nav-list">{navItems.map(([key, href]) => <Link href={href} key={key}>{t("nav." + key)}</Link>)}</div></nav>
    <nav aria-label={t("breadcrumbs.label")} className="breadcrumbs"><ol className="shell-container">{breadcrumbItems.map((item, index) => <li className="flex items-center gap-2" key={item.label + index}>{index > 0 ? <span aria-hidden="true">/</span> : null}{item.href && index < breadcrumbItems.length - 1 ? <Link href={item.href}>{item.label}</Link> : <span aria-current={index === breadcrumbItems.length - 1 ? "page" : undefined}>{item.label}</span>}</li>)}</ol></nav>
    {isReportingRoute ? (
      <aside className="helpline-callout" aria-label={t("helplineCalloutLabel")}>
        <div className="shell-container">
          <span className="helpline-callout-icon" aria-hidden="true"><PhoneCall size={20} /></span>
          <p><strong>{t("helplineCallout." + helplineCategory + "Title")}</strong><span>{t("helplineCallout." + helplineCategory + "Copy")}</span></p>
          <a href={"tel:" + t("supportNumber")}>{t("callSupport")}</a>
        </div>
      </aside>
    ) : null}
    {children}
    <section className="support-band"><div className="shell-container"><strong>{t("supportTitle")}</strong><span>{t("supportCopy")}</span><a href={"tel:" + t("supportNumber")}>{t("callSupport")}</a></div></section>
    <footer className="public-footer"><div className="shell-container footer-content"><span>{t("footerCopyright")}</span><nav aria-label={t("footerNavigation")}><a href="#privacy">{t("privacy")}</a><a href="#accessibility">{t("accessibility")}</a><a href="#terms">{t("terms")}</a></nav></div></footer>
  </div>;
}
