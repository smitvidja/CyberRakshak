import {ComplaintPeopleStep} from "@/features/complaints/ComplaintDraftFlow";

export default async function ComplaintPeoplePage({params}: {params: Promise<{draftId: string}>}) {
  const {draftId} = await params;
  return <ComplaintPeopleStep draftId={draftId} />;
}