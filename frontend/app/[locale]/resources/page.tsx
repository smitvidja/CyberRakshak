import {hasLocale} from "next-intl";
import {setRequestLocale} from "next-intl/server";
import {notFound} from "next/navigation";

import {AwarenessResourcesContent} from "@/features/resources/AwarenessResourcesContent";
import {routing} from "@/lib/i18n/routing";

type Props = {params: Promise<{locale: string}>};

// The public "Learning Corner" destination - reachable by anyone from the home
// page or the top nav, with no warrior dashboard chrome around it. Renders the
// same content as the Cyber Warrior dashboard's Resources page
// (features/resources/AwarenessResourcesContent.tsx is the single shared
// source), just without the warrior sidebar/login-flavoured wrapper, which is
// wrong context for a citizen who only wants to read safety awareness content.
export default async function PublicResourcesPage({params}: Props) {
  const {locale} = await params;
  if (!hasLocale(routing.locales, locale)) notFound();
  setRequestLocale(locale);

  return (
    <main className="shell-container resources-public-page">
      <AwarenessResourcesContent />
    </main>
  );
}
