import {WarriorReportSubmitted} from "@/features/cyber-warriors/WarriorReportSubmitted";

export default async function CyberWarriorReportSubmittedPage({params}: {params: Promise<{reportId: string}>}) {
  const {reportId} = await params;
  return <WarriorReportSubmitted reportId={reportId} />;
}
