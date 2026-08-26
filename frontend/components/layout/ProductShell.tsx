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

  return <div className="app-shell">
    <div className="utility-bar"><div className="shell-container utility-content"><span>{t("utilityNotice")}</span><div className="utility-actions"><span>{t("textSize")}</span><span aria-hidden="true">|</span>{routing.locales.map((nextLocale) => <Link className={nextLocale === locale ? "language-current" : ""} href={localeHref(nextLocale)} key={nextLocale}>{t("languages." + nextLocale)}</Link>)}</div></div></div>
    <header className="brand-header"><div className="shell-container brand-content"><Link className="brand-lockup" href={"/" + locale}><span className="brand-mark" aria-hidden="true">CR</span><span><strong>{t("brandHindi")}</strong><small>{t("brandEnglish")}</small></span></Link><div className="brand-support"><strong>{t("supportLabel")}</strong><span>{t("supportNumber")}</span></div></div></header>
    <nav className="primary-nav" aria-label={t("primaryNavigation")}><div className="shell-container nav-list">{navItems.map(([key, href]) => <Link href={href} key={key}>{t("nav." + key)}</Link>)}</div></nav>
    <div className="breadcrumbs"><div className="shell-container"><Link href={"/" + locale}>{t("nav.home")}</Link><span>/</span><span>{t("breadcrumbCurrent")}</span></div></div>
    {children}
    <section className="support-band"><div className="shell-container"><strong>{t("supportTitle")}</strong><span>{t("supportCopy")}</span><a href={"tel:" + t("supportNumber")}>{t("callSupport")}</a></div></section>
    <footer className="public-footer"><div className="shell-container footer-content"><span>{t("footerCopyright")}</span><nav aria-label={t("footerNavigation")}><a href="#privacy">{t("privacy")}</a><a href="#accessibility">{t("accessibility")}</a><a href="#terms">{t("terms")}</a></nav></div></footer>
  </div>;
}
