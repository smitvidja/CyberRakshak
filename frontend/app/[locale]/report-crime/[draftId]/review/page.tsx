import {ComplaintReviewStep} from "@/features/complaints/ComplaintCompletionFlow";

export default async function ComplaintReviewPage({params}: {params: Promise<{draftId: string}>}) {
  const {draftId} = await params;
  return <ComplaintReviewStep draftId={draftId} />;
}
