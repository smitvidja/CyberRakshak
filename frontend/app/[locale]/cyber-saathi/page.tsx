import {hasLocale} from "next-intl";
import {setRequestLocale} from "next-intl/server";
import {notFound} from "next/navigation";

import {CyberSaathiConversation} from "@/features/cyber-saathi/CyberSaathiConversation";
import {routing} from "@/lib/i18n/routing";

type Props = {params: Promise<{locale: string}>};

export default async function CyberSaathiPage({params}: Props) {
  const {locale} = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  setRequestLocale(locale);
  return <CyberSaathiConversation />;
}
