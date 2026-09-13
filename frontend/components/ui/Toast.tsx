"use client";

import {createContext, useCallback, useContext, useEffect, useMemo, useRef, useState} from "react";
import {CheckCircle2, Info, TriangleAlert} from "lucide-react";

/**
 * Small confirmations: "Saved", "Complaint submitted", "Copy downloaded".
 *
 * Deliberately NOT on every button. A toast after every click - a tab switch, a
 * filter, a chevron - trains people to stop reading them, and on a portal built
 * for accessibility it is worse than useless: this region is aria-live, so every
 * spurious toast is read aloud over whatever a screen-reader user was doing.
 * Confirmations belong on actions that COMPLETE something, where the citizen
 * otherwise cannot tell whether it worked.
 *
 * Two ways to raise one:
 *   - `useToast()` after an async action succeeds - the accurate way, because it
 *     fires when the server confirmed rather than when the click happened;
 *   - `data-toast="Saved"` on a button, for an instant local action where there
 *     is nothing to await.
 */

type ToastTone = "success" | "info" | "warning";
type ToastItem = {id: number; message: string; tone: ToastTone};

type ToastApi = {toast: (message: string, tone?: ToastTone) => void};

const ToastContext = createContext<ToastApi | null>(null);

const VISIBLE_MS = 3200;
const ICONS = {success: CheckCircle2, info: Info, warning: TriangleAlert} as const;

export function useToast(): ToastApi {
  const context = useContext(ToastContext);
  // A component outside the provider must not crash the page for a confirmation.
  return context ?? {toast: () => undefined};
}

export function ToastProvider({children}: {children: React.ReactNode}) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const nextId = useRef(1);

  const toast = useCallback((message: string, tone: ToastTone = "success") => {
    const trimmed = message.trim();
    if (!trimmed) return;
    const id = nextId.current++;
    setItems((current) => [...current.slice(-2), {id, message: trimmed, tone}]);
    setTimeout(() => setItems((current) => current.filter((item) => item.id !== id)), VISIBLE_MS);
  }, []);

  // The declarative path: any button can ask for a confirmation without its
  // component knowing this module exists.
  useEffect(() => {
    const onClick = (event: MouseEvent) => {
      const target = (event.target as HTMLElement | null)?.closest?.("[data-toast]");
      if (!(target instanceof HTMLElement)) return;
      if (target.matches(":disabled, [aria-disabled='true']")) return;
      toast(target.dataset.toast ?? "", (target.dataset.toastTone as ToastTone) || "success");
    };
    document.addEventListener("click", onClick);
    return () => document.removeEventListener("click", onClick);
  }, [toast]);

  const value = useMemo(() => ({toast}), [toast]);

  return (
    <ToastContext.Provider value={value}>
      {children}
      {/* polite, not assertive: a confirmation must never interrupt a citizen
          mid-sentence in a screen reader. */}
      <div aria-live="polite" className="toast-region" role="status">
        {items.map((item) => {
          const Icon = ICONS[item.tone];
          return (
            <p className={"toast toast-" + item.tone} key={item.id}>
              <Icon aria-hidden="true" size={17} strokeWidth={2} />
              {item.message}
            </p>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}
