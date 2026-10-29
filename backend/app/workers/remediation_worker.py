"""
Dristik AI Remediation Worker
Generates validated code patches, schema injections, robots.txt rules, and 7/30/90-day roadmaps.
"""
from typing import Dict, Any, Optional, List
from app.workers.base_worker import BaseCognitiveWorker
from app.cognition.blackboard import CognitiveBlackboard
from app.remediation.patch_generator import RemediationPatcher
from app.reports.roadmap import RoadmapBuilder

class CognitiveRemediationWorker(BaseCognitiveWorker):
    def __init__(self, worker_id: str, model_router):
        super().__init__(
            worker_id=worker_id,
            role_name="Autonomous Remediation & Code Patch Engineer",
            model_router=model_router
        )
        self.patcher = RemediationPatcher()
        self.roadmap_builder = RoadmapBuilder()

    async def execute_task(
        self,
        capability_id: str,
        blackboard: CognitiveBlackboard,
        task_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        findings = blackboard.findings
        bp = blackboard.business_profile
        website_url = blackboard.website_url

        # 1. Generate Structured Code Patches
        patches = self.patcher.generate_patches(findings, bp, website_url)
        blackboard.code_patches = patches

        # 2. Build 7/30/90-Day Prioritized Roadmaps
        r7, r30, r90 = self.roadmap_builder.build_roadmap(findings, blackboard.executive_narrative)
        blackboard.roadmap_7_days = r7
        blackboard.roadmap_30_days = r30
        blackboard.roadmap_90_days = r90

        return {
            "patches_count": len(patches),
            "roadmap_7_days_count": len(r7),
            "roadmap_30_days_count": len(r30),
            "roadmap_90_days_count": len(r90)
        }
