import {redirect} from "next/navigation";

export default async function CyberWarriorApplicationPage({params}: {params: Promise<{locale: string}>}) {
  const {locale} = await params;
  redirect("/" + locale + "/cyber-warrior/apply/resume");
}
