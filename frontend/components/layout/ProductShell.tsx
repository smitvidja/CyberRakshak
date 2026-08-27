"use client";

import Link from "next/link";
import {useLocale, useTranslations} from "next-intl";
import {usePathname} from "next/navigation";
import type {ReactNode} from "react";

import {routing} from "@/lib/i18n/routing";

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
  const navItems = [["home", "/" + locale], ["report", "/" + locale + "/report-crime"], ["track", "/" + locale + "/complaints/track"], ["suspects", "/" + locale + "/suspects/report"], ["warriors", "/" + locale + "/cyber-warrior"], ["learn", "/" + locale + "/resources"], ["contact", "/" + locale + "/contact"]] as const;
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

  return <div className="app-shell">
    <div className="utility-bar"><div className="shell-container utility-content"><span>{t("utilityNotice")}</span><div className="utility-actions"><span>{t("textSize")}</span><span aria-hidden="true">|</span>{routing.locales.map((nextLocale) => <Link className={nextLocale === locale ? "language-current" : ""} href={localeHref(nextLocale)} key={nextLocale}>{t("languages." + nextLocale)}</Link>)}</div></div></div>
    <header className="brand-header"><div className="shell-container brand-content"><Link className="brand-lockup" href={"/" + locale}><span className="brand-mark" aria-hidden="true">CR</span><span><strong>{t("brandHindi")}</strong><small>{t("brandEnglish")}</small></span></Link><div className="brand-support"><strong>{t("supportLabel")}</strong><span>{t("supportNumber")}</span></div></div></header>
    <nav className="primary-nav" aria-label={t("primaryNavigation")}><div className="shell-container nav-list">{navItems.map(([key, href]) => <Link href={href} key={key}>{t("nav." + key)}</Link>)}</div></nav>
    <nav aria-label={t("breadcrumbs.label")} className="breadcrumbs"><ol className="shell-container">{breadcrumbItems.map((item, index) => <li className="flex items-center gap-2" key={item.label + index}>{index > 0 ? <span aria-hidden="true">/</span> : null}{item.href && index < breadcrumbItems.length - 1 ? <Link href={item.href}>{item.label}</Link> : <span aria-current={index === breadcrumbItems.length - 1 ? "page" : undefined}>{item.label}</span>}</li>)}</ol></nav>
    {children}
    <section className="support-band"><div className="shell-container"><strong>{t("supportTitle")}</strong><span>{t("supportCopy")}</span><a href={"tel:" + t("supportNumber")}>{t("callSupport")}</a></div></section>
    <footer className="public-footer"><div className="shell-container footer-content"><span>{t("footerCopyright")}</span><nav aria-label={t("footerNavigation")}><a href="#privacy">{t("privacy")}</a><a href="#accessibility">{t("accessibility")}</a><a href="#terms">{t("terms")}</a></nav></div></footer>
  </div>;
}
