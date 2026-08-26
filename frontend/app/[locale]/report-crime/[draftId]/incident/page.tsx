import {ComplaintIncidentStep} from "@/features/complaints/ComplaintDraftFlow";

export default async function ComplaintIncidentPage({params}: {params: Promise<{draftId: string}>}) {
  const {draftId} = await params;
  return <ComplaintIncidentStep draftId={draftId} />;
}