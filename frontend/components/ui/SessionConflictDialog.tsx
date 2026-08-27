"use client";

import {createPortal} from "react-dom";
import {LogOut, ShieldAlert, X} from "lucide-react";
import {useTranslations} from "next-intl";

export type SessionConflictDialogProps = {
  activeName: string;
  activeRole: "citizen" | "warrior";
  onCancel: () => void;
  onLogoutAndContinue: () => void;
};

// A real, functioning block - not a cosmetic notice. Rendered on top of the identity-verification
// form (see WarriorIdentityVerification / MockIdentityForm), it must make the form underneath
// completely unreachable until the visitor either logs out of the active session or cancels out.
//
// Rendered via a portal into document.body, NOT in-place as a normal child. Rendering in-place
// made this a direct child of <main className="citizen-page ..."> / "warrior-page ...", and both
// pages already have a `.citizen-page > div { position: relative; ... }` / equivalent rule with
// higher CSS specificity than `.session-conflict-backdrop { position: fixed }` - that rule silently
// won, so the "backdrop" laid out as an ordinary in-flow box instead of covering the viewport, and
// the form behind it stayed fully clickable (confirmed live: could still fill in an Aadhaar number
// and reach the OTP step with the dialog open). Portaling to document.body means this is never a
// descendant of page-specific layout rules, so that class of collision cannot happen again here.
export function SessionConflictDialog({activeName, activeRole, onCancel, onLogoutAndContinue}: SessionConflictDialogProps) {
  const t = useTranslations("sessionGuard");
  const roleLabel = t(activeRole === "warrior" ? "roleWarrior" : "roleCitizen");

  if (typeof document === "undefined") return null;

  return createPortal(
    <div className="session-conflict-backdrop" onClick={onCancel} role="presentation">
      <div aria-modal="true" className="session-conflict-modal" onClick={(event) => event.stopPropagation()} role="dialog">
        <button aria-label={t("close")} className="session-conflict-close" onClick={onCancel} type="button">
          <X aria-hidden="true" size={18} />
        </button>
        <span className="session-conflict-icon" aria-hidden="true"><ShieldAlert size={26} /></span>
        <h2>{t("title")}</h2>
        <p>{t("body", {name: activeName, role: roleLabel})}</p>
        <div className="session-conflict-actions">
          <button className="portal-primary-link" onClick={onLogoutAndContinue} type="button">
            <LogOut aria-hidden="true" size={17} />
            {t("logoutAndContinue", {role: roleLabel})}
          </button>
          <button className="warrior-text-link" onClick={onCancel} type="button">{t("cancel")}</button>
        </div>
      </div>
    </div>,
    document.body
  );
}
