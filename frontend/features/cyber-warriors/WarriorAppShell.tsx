"use client";

import Link from "next/link";
import {useLocale, useTranslations} from "next-intl";
import {usePathname, useRouter} from "next/navigation";
import {useEffect, useRef, useState, type ReactNode} from "react";
import {
  Award,
  Bell,
  CheckCheck,
  ChevronDown,
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

import type {NotificationRecord} from "@/lib/api/notifications";
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

function useOutsideClick(onOutside: () => void) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    function handlePointerDown(event: MouseEvent) {
      if (ref.current && !ref.current.contains(event.target as Node)) onOutside();
    }
    document.addEventListener("mousedown", handlePointerDown);
    return () => document.removeEventListener("mousedown", handlePointerDown);
  }, [onOutside]);
  return ref;
}

export function WarriorTopBar({
  name,
  notifications,
  onMarkRead,
  profileHref,
  roleLabel
}: {
  name: string;
  notifications: NotificationRecord[];
  onMarkRead: (id: string) => void;
  profileHref: string;
  roleLabel: string;
}) {
  const t = useTranslations("warriorDashboard");
  const locale = useLocale();
  const router = useRouter();
  const [bellOpen, setBellOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const bellRef = useOutsideClick(() => setBellOpen(false));
  const menuRef = useOutsideClick(() => setMenuOpen(false));
  const unreadCount = notifications.filter((item) => !item.is_read).length;
  const dateFormatter = new Intl.DateTimeFormat(locale, {dateStyle: "medium", timeStyle: "short"});

  function logout() {
    clearWarriorSession();
    router.push("/" + locale + "/cyber-warrior");
  }

  return (
    <div className="warrior-topbar">
      <div className="warrior-topbar-menu" ref={bellRef}>
        <button aria-expanded={bellOpen} aria-label={t("notificationsLabel", {count: unreadCount})} className="warrior-topbar-bell" onClick={() => setBellOpen((open) => !open)} type="button">
          <Bell aria-hidden="true" size={19} />
          {unreadCount > 0 ? <span className="warrior-topbar-badge">{unreadCount}</span> : null}
        </button>
        {bellOpen ? (
          <div className="warrior-dropdown-panel warrior-notification-panel">
            <h3>{t("notificationsTitle")}</h3>
            {notifications.length === 0 ? (
              <p className="warrior-dropdown-empty">{t("notificationsEmpty")}</p>
            ) : (
              <ul>
                {notifications.slice(0, 6).map((item) => (
                  <li className={item.is_read ? "" : "is-unread"} key={item.id}>
                    <div><strong>{item.title}</strong><span>{item.message}</span><small>{dateFormatter.format(new Date(item.created_at))}</small></div>
                    {item.is_read ? null : <button aria-label={t("markReadLabel")} onClick={() => onMarkRead(item.id)} type="button"><CheckCheck aria-hidden="true" size={15} /></button>}
                  </li>
                ))}
              </ul>
            )}
          </div>
        ) : null}
      </div>
      <div className="warrior-topbar-menu" ref={menuRef}>
        <button aria-expanded={menuOpen} className="warrior-topbar-identity" onClick={() => setMenuOpen((open) => !open)} type="button">
          <span className="warrior-topbar-avatar" aria-hidden="true"><ShieldCheck size={18} /></span>
          <span><strong>{name}</strong><small>{roleLabel}</small></span>
          <ChevronDown aria-hidden="true" size={15} />
        </button>
        {menuOpen ? (
          <div className="warrior-dropdown-panel warrior-account-panel">
            <Link href={profileHref} onClick={() => setMenuOpen(false)}><User aria-hidden="true" size={16} />{t("navProfile")}</Link>
            <button onClick={logout} type="button"><LogOut aria-hidden="true" size={16} />{t("navLogout")}</button>
          </div>
        ) : null}
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
