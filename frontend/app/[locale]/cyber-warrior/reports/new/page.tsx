import {Suspense} from "react";

import {WarriorReportWizard} from "@/features/cyber-warriors/WarriorReportWizard";

export default function CyberWarriorNewReportPage() {
  return (
    <Suspense fallback={null}>
      <WarriorReportWizard />
    </Suspense>
  );
}
