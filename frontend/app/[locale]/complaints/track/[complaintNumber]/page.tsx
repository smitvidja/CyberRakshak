import {ComplaintTrackingDetail} from "@/features/complaints/ComplaintCompletionFlow";

export default async function ComplaintTrackingDetailPage({params}: {params: Promise<{complaintNumber: string}>}) {
  const {complaintNumber} = await params;
  return <ComplaintTrackingDetail complaintNumber={complaintNumber} />;
}
