"use client";

import Link from "next/link";
import {useLocale, useTranslations} from "next-intl";
import {usePathname, useRouter} from "next/navigation";
import type {ReactNode} from "react";
import {
  Award,
  Bell,
  ClipboardList,
  FileText,
  HelpCircle,
  LayoutDashboard,
  LogOut,
  Search,
  ShieldCheck,
  Trophy,
  User,
  type LucideIcon
} from "lucide-react";

import {clearWarriorSession} from "@/lib/auth/warrior-session";

export type WarriorNavKey = "dashboard" | "myReports" | "trackReports" | "profile" | "myApplication" | "leaderboard" | "badges" | "resources";

type NavItem = {icon: LucideIcon; key: WarriorNavKey; labelKey: string};

const primaryNavItems: NavItem[] = [
  {icon: LayoutDashboard, key: "dashboard", labelKey: "navDashboard"},
  {icon: FileText, key: "myReports", labelKey: "navMyReports"},
  {icon: Search, key: "trackReports", labelKey: "navTrackReports"}
];

const secondaryNavItems: NavItem[] = [
  {icon: User, key: "profile", labelKey: "navProfile"},
  {icon: ClipboardList, key: "myApplication", labelKey: "navMyApplication"},
  {icon: Trophy, key: "leaderboard", labelKey: "navLeaderboard"},
  {icon: Award, key: "badges", labelKey: "navBadges"},
  {icon: HelpCircle, key: "resources", labelKey: "navResources"}
];

function navHref(locale: string, key: WarriorNavKey) {
  const base = "/" + locale + "/cyber-warrior";
  switch (key) {
    case "dashboard": return base + "/dashboard";
    case "myReports": return base + "/reports";
    case "trackReports": return base + "/reports/track";
    case "profile": return base + "/profile";
    case "myApplication": return base + "/apply/submitted";
    case "leaderboard": return base + "/leaderboard";
    case "badges": return base + "/badges";
    case "resources": return base + "/resources";
  }
}

export type WarriorSidebarIdentity = {label: string; verified: boolean; warriorId: string};

export function WarriorSidebar({active, identity}: {active: WarriorNavKey; identity?: WarriorSidebarIdentity}) {
  const t = useTranslations("warriorDashboard");
  const locale = useLocale();
  const router = useRouter();

  function logout() {
    clearWarriorSession();
    router.push("/" + locale + "/cyber-warrior");
  }

  return (
    <nav aria-label={t("sidebarLabel")} className="warrior-sidebar">
      {identity ? (
        <div className="warrior-sidebar-identity">
          <span aria-hidden="true"><ShieldCheck size={22} /></span>
          <div>
            <strong>{identity.warriorId}</strong>
            {identity.verified ? <span className="warrior-verified-pill"><ShieldCheck aria-hidden="true" size={13} />{t("verifiedLabel")}</span> : null}
            <small>{identity.label}</small>
          </div>
        </div>
      ) : null}
      <ol>
        {primaryNavItems.map((item) => (
          <li className={active === item.key ? "is-active" : ""} key={item.key}>
            <Link href={navHref(locale, item.key)}><item.icon aria-hidden="true" size={18} /><span>{t(item.labelKey)}</span></Link>
          </li>
        ))}
      </ol>
      <ol>
        {secondaryNavItems.map((item) => (
          <li className={active === item.key ? "is-active" : ""} key={item.key}>
            <Link href={navHref(locale, item.key)}><item.icon aria-hidden="true" size={18} /><span>{t(item.labelKey)}</span></Link>
          </li>
        ))}
      </ol>
      <ol>
        <li><a href="tel:1930"><HelpCircle aria-hidden="true" size={18} /><span>{t("navHelp")}</span></a></li>
        <li className="warrior-nav-logout"><button onClick={logout} type="button"><LogOut aria-hidden="true" size={18} /><span>{t("navLogout")}</span></button></li>
      </ol>
    </nav>
  );
}

export function WarriorTopBar({name, notificationCount, roleLabel}: {name: string; notificationCount: number; roleLabel: string}) {
  const t = useTranslations("warriorDashboard");
  return (
    <div className="warrior-topbar">
      <button aria-label={t("notificationsLabel", {count: notificationCount})} className="warrior-topbar-bell" type="button">
        <Bell aria-hidden="true" size={19} />
        {notificationCount > 0 ? <span className="warrior-topbar-badge">{notificationCount}</span> : null}
      </button>
      <div className="warrior-topbar-identity">
        <span className="warrior-topbar-avatar" aria-hidden="true"><ShieldCheck size={18} /></span>
        <span><strong>{name}</strong><small>{roleLabel}</small></span>
      </div>
    </div>
  );
}

export function WarriorComingSoon({description, title}: {description: string; title: string}) {
  const t = useTranslations("warriorDashboard");
  return (
    <div className="warrior-coming-soon">
      <span aria-hidden="true"><ClipboardList size={30} /></span>
      <h2>{title}</h2>
      <p>{description}</p>
      <p className="warrior-coming-soon-note">{t("comingSoonNote")}</p>
    </div>
  );
}

export function WarriorShellPage({active, children, identity}: {active: WarriorNavKey; children: ReactNode; identity?: WarriorSidebarIdentity}) {
  const pathname = usePathname();
  return (
    <main className="warrior-page warrior-dashboard-page" key={pathname}>
      <div className="shell-container warrior-dashboard-layout">
        <WarriorSidebar active={active} identity={identity} />
        <div className="warrior-dashboard-main">{children}</div>
      </div>
    </main>
  );
}
