"use client";

import {AwarenessResourcesContent} from "@/features/resources/AwarenessResourcesContent";
import {WarriorShellPage} from "./WarriorAppShell";

export function WarriorResources() {
  return (
    <WarriorShellPage active="resources">
      <div className="warrior-dashboard-content warrior-full-width">
        <AwarenessResourcesContent />
      </div>
    </WarriorShellPage>
  );
}
