import {ComplaintSubmitted} from "@/features/complaints/ComplaintCompletionFlow";

export default async function ComplaintSubmittedPage({params}: {params: Promise<{complaintNumber: string}>}) {
  const {complaintNumber} = await params;
  return <ComplaintSubmitted complaintNumber={complaintNumber} />;
}
