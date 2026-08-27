import {WarriorReportDetails} from "@/features/cyber-warriors/WarriorReportDetails";

export default async function CyberWarriorReportDetailsPage({params}: {params: Promise<{reportId: string}>}) {
  const {reportId} = await params;
  return <WarriorReportDetails reportId={reportId} />;
}
